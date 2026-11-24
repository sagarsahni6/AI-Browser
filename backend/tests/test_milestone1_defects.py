import os
import json
import tempfile
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from backend.app.main import app, handle_tasks_approve, handle_tasks_reject
from backend.app.config import settings
from backend.app.database.engine import AsyncSessionLocal, init_db
from backend.app.database.repository import Repository
from backend.app.agents.models import TaskStep, StepStatus, TaskPlan
from backend.app.agents.supervisor import SupervisorAgent
from backend.app.agents.browser_use_agent import BrowserUseEngine
from backend.app.agents.data_agent import DataAgent
from backend.app.agents.verifier import VerifierAgent
from backend.app.research.service import ResearchService
from backend.app.workflows.engine import WorkflowEngine
from backend.app.tools.executor import ToolExecutor
from backend.app.browser.bridge import bridge

@pytest.fixture(autouse=True)
async def setup_test_db():
    await init_db()
    yield

# ============================================================================
# GROUP 1: DEFECT 1 — Approval System Lifecycle
# ============================================================================

@pytest.mark.asyncio
async def test_approval_lifecycle_pause_and_checkpoint_serialization():
    """Verify task pauses on approval_required, serializes checkpoint, and saves step info."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Sensitive Task", "Fill user credentials")
        task_id = task.id

    step1 = TaskStep(
        id=1,
        agent="browser",
        action="fill_input",
        description="Fill sensitive token",
        parameters={"x": 100, "y": 200, "text": "secret_password"}
    )
    step2 = TaskStep(
        id=2,
        agent="browser",
        action="click_element",
        description="Click login",
        parameters={"x": 100, "y": 250}
    )

    remaining_steps = [step1, step2]
    total_steps = 2

    # Run step loop which hits approval_required on fill_input password
    res = await SupervisorAgent._execute_steps_loop(task_id, remaining_steps, step_results=[], total_steps=total_steps)

    assert res["status"] == "approval_required"
    assert res["step_number"] == 1
    assert "approval_id" in res

    # Verify database state
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        t = await repo.get_task(task_id)
        assert t.status == "approval_required"

        appr = await repo.get_approval_request(res["approval_id"])
        assert appr is not None
        assert appr.status == "pending"
        assert appr.step_number == 1
        assert appr.session_checkpoint_json is not None

        checkpoint = json.loads(appr.session_checkpoint_json)
        assert checkpoint["task_id"] == task_id
        assert checkpoint["step_number"] == 1
        assert len(checkpoint["remaining_steps"]) == 1
        assert checkpoint["remaining_steps"][0]["id"] == 2
        assert checkpoint["total_steps"] == 2

@pytest.mark.asyncio
async def test_approval_rejection_cancels_task():
    """Verify user rejection marks approval rejected and task cancelled without executing action."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Rejection Task", "Execute sensitive command")
        appr = await repo.create_approval_request(
            task_id=task.id,
            tool_name="desktop_launch_app",
            action_type="sensitive_operation",
            description="Launch unauthorized shell",
            parameters_json=json.dumps({"app_name": "powershell.exe"}),
            step_number=1,
            session_checkpoint_json=json.dumps({"task_id": task.id, "remaining_steps": [], "step_results": []})
        )
        task_id = task.id
        appr_id = appr.id

    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        res = await SupervisorAgent.resume_approved_task(task_id, approval_id=appr_id, decision=False)
        assert res["status"] == "rejected"
        assert mock_exec.call_count == 0

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        t = await repo.get_task(task_id)
        assert t.status == "cancelled"
        a = await repo.get_approval_request(appr_id)
        assert a.status == "rejected"
        assert a.resolved_at is not None

@pytest.mark.asyncio
async def test_approval_acceptance_revalidates_executes_once_and_resumes():
    """Verify approval revalidates browser state, executes tool exactly once, restores checkpoint, and completes task."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Approved Task", "Export data upon approval")
        task_id = task.id

        remaining_subsequent = [
            {
                "id": 2,
                "agent": "verifier",
                "action": "verify_task",
                "description": "Verify task outcome",
                "parameters": {}
            }
        ]
        checkpoint_data = {
            "task_id": task_id,
            "step_number": 1,
            "remaining_steps": remaining_subsequent,
            "step_results": [],
            "total_steps": 2
        }

        appr = await repo.create_approval_request(
            task_id=task_id,
            tool_name="export_csv",
            action_type="sensitive_operation",
            description="User approved data export",
            parameters_json=json.dumps({"filename": "approved.csv", "headers": ["A"], "rows": [["1"]]}),
            step_number=1,
            session_checkpoint_json=json.dumps(checkpoint_data)
        )
        appr_id = appr.id

        # Add initial DB step 1
        await repo.add_task_step(task_id, 1, "Export step", tool_name="export_csv")

    executed_tools = []
    real_execute = ToolExecutor.execute

    async def tracking_execute(tool_name, params, bypass_approval=False):
        if tool_name == "export_csv":
            executed_tools.append((tool_name, params, bypass_approval))
            return {"status": "success", "tool_name": "export_csv", "exported_file": "approved.csv", "result": {}, "evidence": {}, "error": None}
        return await real_execute(tool_name, params, bypass_approval=bypass_approval)

    with patch.object(bridge, "call", new_callable=AsyncMock) as mock_bridge, \
         patch.object(ToolExecutor, "execute", side_effect=tracking_execute):
        mock_bridge.return_value = {"title": "Revalidated Page", "url": "https://example.com/app"}

        res = await SupervisorAgent.resume_approved_task(task_id, approval_id=appr_id, decision=True)

        assert res["status"] == "approved"
        # Bridge inspect must have been called for browser state revalidation
        mock_bridge.assert_any_call("browser.inspect", {})
        # Approved tool must have been executed exactly once
        assert len(executed_tools) == 1
        assert executed_tools[0][0] == "export_csv"
        assert executed_tools[0][2] is True # bypass_approval flag was True

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        t = await repo.get_task(task_id)
        assert t.status == "completed"
        a = await repo.get_approval_request(appr_id)
        assert a.status == "executed"
        assert a.resolved_at is not None

@pytest.mark.asyncio
async def test_api_endpoints_wired_to_supervisor_resumption():
    """Verify REST /tasks/{id}/approve and JSON-RPC tasks.approve delegate to SupervisorAgent.resume_approved_task."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("API Approval Task", "Testing API approve endpoint")
        task_id = task.id
        appr = await repo.create_approval_request(
            task_id=task_id,
            tool_name="export_csv",
            action_type="sensitive",
            description="Approve export",
            parameters_json=json.dumps({"filename": "api.csv"}),
            step_number=1,
            session_checkpoint_json=json.dumps({"task_id": task_id, "remaining_steps": [], "step_results": []})
        )
        appr_id = appr.id

    with patch.object(SupervisorAgent, "resume_approved_task", new_callable=AsyncMock) as mock_resume:
        mock_resume.return_value = {"status": "approved", "id": task_id, "approval_id": appr_id}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(f"/api/v1/tasks/{task_id}/approve?approval_id={appr_id}")
            assert resp.status_code == 200
            assert resp.json()["status"] == "approved"
            mock_resume.assert_called_with(task_id, approval_id=appr_id, decision=True)

        # Test JSON-RPC handle_tasks_approve
        rpc_res = await handle_tasks_approve({"task_id": task_id, "approval_id": appr_id, "decision": True})
        assert rpc_res["status"] == "approved"

# ============================================================================
# GROUP 2: DEFECT 2 — Browser-Use Security Interception
# ============================================================================

def test_electron_remote_debugging_port_9222_removed():
    """Verify remote-debugging-port 9222 is removed from apps/desktop/electron/main.ts."""
    main_ts_path = os.path.join(os.getcwd(), "apps", "desktop", "electron", "main.ts")
    assert os.path.exists(main_ts_path)
    with open(main_ts_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "remote-debugging-port" not in content
    assert "9222" not in content

def test_default_agent_engine_is_native():
    """Verify DEFAULT_AGENT_ENGINE is configured to 'native'."""
    assert settings.DEFAULT_AGENT_ENGINE == "native"

@pytest.mark.asyncio
async def test_browser_use_no_duplicate_rerun_on_exception():
    """Verify BrowserUseEngine failure does not trigger a duplicate rerun of SupervisorAgent."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("BrowserUse Task", "Testing no rerun on failure")
        task_id = task.id

    with patch("browser_use.Agent.run", side_effect=RuntimeError("CDP connection lost")), \
         patch.object(SupervisorAgent, "run_task", new_callable=AsyncMock) as mock_supervisor_run:
        res = await BrowserUseEngine.execute_task(task_id, "Fail gracefully")
        assert res["status"] == "failed"
        assert res.get("fallback_used") is False
        # Must NOT rerun SupervisorAgent
        assert mock_supervisor_run.call_count == 0

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        t = await repo.get_task(task_id)
        assert t.status == "failed"

# ============================================================================
# GROUP 3: DEFECT 3 — Canonical Execution Results & Consumers
# ============================================================================

@pytest.mark.asyncio
async def test_toolexecutor_canonical_result_structure():
    """Verify all tool execution outputs adhere to canonical schema with backward-compatible aliases."""
    with patch.object(bridge, "call", new_callable=AsyncMock) as mock_bridge:
        mock_bridge.return_value = {
            "title": "Example Domain",
            "url": "https://example.com",
            "visibleText": "Example Text Header",
            "interactiveElements": []
        }
        res = await ToolExecutor.execute("get_page_content", {})

        # Canonical schema keys
        assert "status" in res
        assert res["status"] == "success"
        assert "tool_name" in res
        assert res["tool_name"] == "get_page_content"
        assert "result" in res
        assert "evidence" in res
        assert "error" in res
        assert res["error"] is None

        # Backward-compatible alias keys
        assert res["url"] == "https://example.com"
        assert res["title"] == "Example Domain"
        assert "visible_text_snippet" in res
        assert "text" in res
        assert res["text"] == res["visible_text_snippet"]

@pytest.mark.asyncio
async def test_dataagent_contract_alignment_with_canonical_status():
    """Verify DataAgent extracts content when ToolExecutor returns status='success' and visible_text_snippet."""
    with patch.object(bridge, "call", new_callable=AsyncMock) as mock_bridge:
        mock_bridge.return_value = {
            "title": "Data Page",
            "url": "https://example.com/data",
            "visibleText": "Col1 | Col2\nValA | ValB\nValC | ValD",
            "interactiveElements": []
        }
        res = await DataAgent.extract_table_data(max_pages=1)
        assert res["status"] in ("ok", "success")
        assert res["row_count"] >= 2
        assert len(res["data"]) >= 2

@pytest.mark.asyncio
async def test_research_service_contract_alignment():
    """Verify ResearchService extracts results when search_web returns status='success'."""
    mock_search_item = MagicMock()
    mock_search_item.title = "AI in Browser"
    mock_search_item.url = "https://example.com/ai"
    mock_search_item.snippet = "Advancements in agentic web browsers"

    with patch("backend.app.search.registry.search_registry.get") as mock_search_reg, \
         patch.object(bridge, "call", new_callable=AsyncMock):
        mock_prov = MagicMock()
        mock_prov.search = AsyncMock(return_value=[mock_search_item])
        mock_search_reg.return_value = mock_prov

        report = await ResearchService.synthesize(topic="Agentic AI", depth="quick")
        assert report["status"] in ("ok", "success", "completed")
        assert report["sources_count"] >= 1
        assert any("example.com/ai" in s["url"] for s in report["sources"])

@pytest.mark.asyncio
async def test_workflow_engine_approval_handling():
    """Verify WorkflowEngine pauses execution on approval_required without running subsequent steps."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Approval Workflow",
            steps=[
                {"step": 1, "action": "open_new_tab", "params": {"url": "https://example.com"}},
                {"step": 2, "action": "desktop_launch_app", "params": {"app_name": "cmd.exe"}}, # requires approval
                {"step": 3, "action": "take_screenshot", "params": {}} # should NOT be executed
            ]
        )
        wf_id = wf.id

    step3_executed = False

    async def mock_workflow_exec(action, params):
        nonlocal step3_executed
        if action == "open_new_tab":
            return {"status": "success", "tool_name": action, "result": {}, "evidence": {}, "error": None}
        elif action == "desktop_launch_app":
            return {"status": "approval_required", "tool_name": action, "reason": "Requires approval", "result": None, "evidence": {}, "error": None}
        elif action == "take_screenshot":
            step3_executed = True
            return {"status": "success", "tool_name": action, "result": {}, "evidence": {}, "error": None}
        return {"status": "error", "tool_name": action, "error": "unknown"}

    with patch.object(ToolExecutor, "execute", side_effect=mock_workflow_exec):
        res = await WorkflowEngine.execute_workflow(wf_id)
        assert res["status"] == "approval_required"
        assert res["paused_step"] == 2
        assert step3_executed is False

# ============================================================================
# GROUP 4: DEFECT 4 — Goal-Based Objective Verification
# ============================================================================

@pytest.mark.asyncio
async def test_verifier_dom_assertion():
    """Verify VerifierAgent dom_assertion verifies element presence, visibility, and text match."""
    # 1. Matching element
    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            "status": "success",
            "result": {"found": True, "visible": True, "text": "Order Confirmed #12345"}
        }
        res = await VerifierAgent.execute_step("dom_assertion", {
            "selector": ".confirmation-msg",
            "text": "Order Confirmed",
            "expected_state": "visible"
        })
        assert res["status"] == "success"
        assert res["verified"] is True
        assert res["evidence"]["found"] is True

    # 2. Missing element -> verified False
    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            "status": "success",
            "result": {"found": False, "visible": False, "text": ""}
        }
        res = await VerifierAgent.execute_step("dom_assertion", {
            "selector": "#missing-item"
        })
        assert res["verified"] is False
        assert "not found" in res["reason"]

    # 3. Expected absent element
    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            "status": "success",
            "result": {"found": False, "visible": False, "text": ""}
        }
        res = await VerifierAgent.execute_step("dom_assertion", {
            "selector": ".error-banner",
            "expected_state": "absent"
        })
        assert res["verified"] is True

@pytest.mark.asyncio
async def test_verifier_url_match():
    """Verify VerifierAgent url_match validates patterns and domains."""
    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            "status": "success",
            "url": "https://app.example.com/dashboard/analytics"
        }
        # Success pattern
        res1 = await VerifierAgent.execute_step("url_match", {"pattern": r"example\.com/dashboard"})
        assert res1["verified"] is True

        # Failed pattern
        res2 = await VerifierAgent.execute_step("url_match", {"pattern": r"github\.com"})
        assert res2["verified"] is False
        assert "did not match" in res2["reason"]

@pytest.mark.asyncio
async def test_verifier_data_validation():
    """Verify VerifierAgent data_validation validates row count and schema keys."""
    # Valid data
    valid_data = [
        {"id": 1, "name": "Item A", "price": 10.5},
        {"id": 2, "name": "Item B", "price": 20.0}
    ]
    res1 = await VerifierAgent.execute_step("data_validation", {
        "records": valid_data,
        "min_records": 2,
        "required_fields": ["name", "price"]
    })
    assert res1["verified"] is True
    assert res1["evidence"]["record_count"] == 2

    # Insufficient records
    res2 = await VerifierAgent.execute_step("data_validation", {
        "records": valid_data,
        "min_records": 5
    })
    assert res2["verified"] is False

    # Missing required field
    res3 = await VerifierAgent.execute_step("data_validation", {
        "records": valid_data,
        "required_fields": ["non_existent_column"]
    })
    assert res3["verified"] is False

@pytest.mark.asyncio
async def test_verifier_file_validation():
    """Verify VerifierAgent file_validation checks file existence and non-empty size."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(b"col1,col2\nval1,val2\n")
        tmp_path = tmp.name

    try:
        # Existing non-empty file
        res1 = await VerifierAgent.execute_step("file_validation", {"file_path": tmp_path})
        assert res1["verified"] is True
        assert res1["evidence"]["size_bytes"] > 0

        # Non-existing file
        res2 = await VerifierAgent.execute_step("file_validation", {"file_path": tmp_path + ".nonexistent"})
        assert res2["verified"] is False
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@pytest.mark.asyncio
async def test_verifier_form_submission():
    """Verify VerifierAgent form_submission evaluates confirmation text and error banners."""
    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        # Mock get_page_content
        async def mock_tool_call(tool, params):
            if tool == "get_page_content":
                return {"status": "success", "visible_text_snippet": "Thank you! Your response has been recorded.", "url": "https://example.com/thanks"}
            if tool == "evaluate_javascript":
                return {"status": "success", "result": False} # no error banner
            return {"status": "success"}

        mock_exec.side_effect = mock_tool_call

        res = await VerifierAgent.execute_step("form_submission", {
            "success_text": "Thank you",
            "redirect_url": "thanks",
            "error_selector": ".form-error"
        })
        assert res["verified"] is True

        # Error banner present -> fails
        async def mock_tool_call_err(tool, params):
            if tool == "get_page_content":
                return {"status": "success", "visible_text_snippet": "Error submitting", "url": "https://example.com/form"}
            if tool == "evaluate_javascript":
                return {"status": "success", "result": True} # error banner found!
            return {"status": "success"}

        mock_exec.side_effect = mock_tool_call_err
        res_err = await VerifierAgent.execute_step("form_submission", {
            "error_selector": ".form-error"
        })
        assert res_err["verified"] is False
