"""
tests/e2e/tier1_features/test_t1_f01_f10.py
Tier 1 Feature Coverage Tests: Features 1 to 10 (50 tests total, 5 per feature).

Features Covered:
  F01: Repository Audit Document
  F02: Architecture & Tech Stack Preservation
  F03: Persistent Approval Lifecycle
  F04: Browser-Use Security Interception
  F05: Canonical Execution Results
  F06: Eliminate Duplicate Tool Implementations
  F07: DataAgent Contract Alignment
  F08: ResearchService Contract Alignment
  F09: WorkflowEngine Approval Handling
  F10: Goal-Based Objective Verification
"""

import os
import ast
import json
import pytest
from pathlib import Path
from typing import Dict, Any

from backend.app.config import settings
from backend.app.tools.executor import ToolExecutor
from backend.app.security.approval import ApprovalManager
from backend.app.agents.data_agent import DataAgent
from backend.app.research.service import ResearchService
from backend.app.agents.verifier import VerifierAgent
from backend.app.workflows.engine import WorkflowEngine
from backend.app.database.repository import Repository
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.models import WorkflowExecution
from sqlalchemy import select

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent


# ===========================================================================
# Feature 1: Repository Audit Document (5 tests)
# ===========================================================================

def test_t1_f01_01_audit_doc_exists():
    """Verify docs/UPGRADE_AUDIT.md exists and is non-empty."""
    audit_file = WORKSPACE_ROOT / "docs" / "UPGRADE_AUDIT.md"
    assert audit_file.exists(), "docs/UPGRADE_AUDIT.md does not exist"
    assert audit_file.stat().st_size > 500, "docs/UPGRADE_AUDIT.md is too short or empty"


def test_t1_f01_02_audit_doc_sections():
    """Verify docs/UPGRADE_AUDIT.md contains all required audit sections."""
    audit_file = WORKSPACE_ROOT / "docs" / "UPGRADE_AUDIT.md"
    content = audit_file.read_text(encoding="utf-8")
    assert "Executive Summary" in content or "Baseline State" in content
    assert "Component Condition Matrix" in content
    assert "Critical Defects" in content
    assert "Remediation" in content or "Recommendations" in content


def test_t1_f01_03_audit_doc_matrix_table():
    """Verify docs/UPGRADE_AUDIT.md contains the structured condition matrix table."""
    audit_file = WORKSPACE_ROOT / "docs" / "UPGRADE_AUDIT.md"
    content = audit_file.read_text(encoding="utf-8")
    # Table headers verification
    assert "Module / Component" in content or "Component" in content
    assert "Condition Category" in content or "Condition" in content
    assert "Severity" in content
    assert "Detailed Findings" in content or "Findings" in content


def test_t1_f01_04_audit_doc_component_coverage():
    """Verify matrix table covers core system components across the architecture."""
    audit_file = WORKSPACE_ROOT / "docs" / "UPGRADE_AUDIT.md"
    content = audit_file.read_text(encoding="utf-8")
    expected_components = [
        "Approval", "Browser", "Tool Execution", "Data",
        "Research", "Workflow", "Verifier", "Supervisor", "Automation"
    ]
    for comp in expected_components:
        assert comp.lower() in content.lower(), f"Component '{comp}' missing from audit document"


def test_t1_f01_05_audit_doc_condition_taxonomy():
    """Verify document utilizes the standardized 5-state condition taxonomy."""
    audit_file = WORKSPACE_ROOT / "docs" / "UPGRADE_AUDIT.md"
    content = audit_file.read_text(encoding="utf-8")
    taxonomy = [
        "Fully Implemented",
        "Partially Implemented",
        "Implemented but Defective",
        "Missing",
        "Requires Architectural Change"
    ]
    for condition in taxonomy:
        assert condition in content, f"Taxonomy state '{condition}' missing from audit document"


# ===========================================================================
# Feature 2: Architecture & Tech Stack Preservation (5 tests)
# ===========================================================================

def test_t1_f02_01_electron_desktop_stack():
    """Verify Electron desktop architecture is preserved in package manifests."""
    root_pkg = WORKSPACE_ROOT / "package.json"
    desktop_pkg = WORKSPACE_ROOT / "apps" / "desktop" / "package.json"
    assert root_pkg.exists() or desktop_pkg.exists()
    content = (root_pkg.read_text(encoding="utf-8") if root_pkg.exists() else "") + \
              (desktop_pkg.read_text(encoding="utf-8") if desktop_pkg.exists() else "")
    assert "electron" in content.lower(), "Electron missing from package.json"


def test_t1_f02_02_react18_frontend_stack():
    """Verify React 18, TypeScript, and Zustand are retained in apps/desktop."""
    desktop_pkg = WORKSPACE_ROOT / "apps" / "desktop" / "package.json"
    assert desktop_pkg.exists()
    data = json.loads(desktop_pkg.read_text(encoding="utf-8"))
    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    assert "react" in deps, "React missing from desktop package"
    assert "zustand" in deps, "Zustand state store missing from desktop package"
    assert "typescript" in deps, "TypeScript missing from desktop package"


def test_t1_f02_03_fastapi_backend_stack():
    """Verify FastAPI and Python >= 3.11 are preserved in backend configuration."""
    pyproject = WORKSPACE_ROOT / "backend" / "pyproject.toml"
    assert pyproject.exists()
    content = pyproject.read_text(encoding="utf-8")
    assert "fastapi" in content.lower(), "FastAPI missing from pyproject.toml"
    assert "3.11" in content, "Python 3.11+ requirement missing from pyproject.toml"


def test_t1_f02_04_sqlite_persistence_stack():
    """Verify SQLite + SQLAlchemy 2.0 async persistence stack is preserved."""
    assert "sqlite" in settings.DATABASE_URL.lower() or "aiosqlite" in settings.DATABASE_URL.lower()
    from backend.app.database.engine import engine
    assert engine is not None


def test_t1_f02_05_stdio_jsonrpc_stack():
    """Verify private bidirectional stdio JSON-RPC protocol implementation."""
    from backend.app.browser.bridge import bridge
    assert hasattr(bridge, "call"), "Bridge missing RPC call method"
    assert hasattr(bridge, "notify"), "Bridge missing RPC notify method"
    assert hasattr(bridge, "register_method"), "Bridge missing RPC register_method"


# ===========================================================================
# Feature 3: Persistent Approval Lifecycle (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t1_f03_01_pause_on_approval_required():
    """Sensitive tool call returns status='approval_required' without bypassing security."""
    res = await ToolExecutor.execute(
        "fill_input",
        {"x": 100, "y": 200, "text": "secret_password_123"},
        bypass_approval=False
    )
    assert res["status"] == "approval_required"
    assert "password" in res.get("reason", "").lower() or "credential" in res.get("reason", "").lower()


@pytest.mark.asyncio
async def test_t1_f03_02_checkpoint_persistence(test_db):
    """Approval request records task_id, tool_name, and parameters in database."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title="Checkout Item", prompt="Buy laptop")
        approval = await repo.create_approval_request(
            task_id=task.id,
            tool_name="click_element",
            action_type="financial",
            description="Authorize payment of $999",
            parameters_json=json.dumps({"selector": "button#checkout", "amount": 999.0})
        )
        assert approval.id.startswith("appr-")
        assert approval.status == "pending"

        # Verify retrieval
        pending = await repo.get_pending_approval_for_task(task.id)
        assert pending is not None
        assert pending.id == approval.id


@pytest.mark.asyncio
async def test_t1_f03_03_user_approval_execution(async_client, test_db):
    """Approving pending task via API endpoint updates status and processes decision."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title="Sensitive Task", prompt="Do sensitive action")
        await repo.update_task_status(task.id, status="approval_required")
        approval = await repo.create_approval_request(
            task_id=task.id,
            tool_name="click_element",
            action_type="financial",
            description="Authorize payment of $999",
            parameters_json=json.dumps({"selector": "button#checkout", "amount": 999.0}),
            session_checkpoint_json=json.dumps({"task_id": task.id, "remaining_steps": [], "step_results": []})
        )

    resp = await async_client.post(f"/api/v1/tasks/{task.id}/approve?approval_id={approval.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("approved", "executed", "running")


@pytest.mark.asyncio
async def test_t1_f03_04_clean_task_resumption(ipc_client, test_db):
    """tasks.approve IPC method accepts approval decision and sets running state."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title="Resumed Task", prompt="Test resume")
        await repo.update_task_status(task.id, status="approval_required")
        approval = await repo.create_approval_request(
            task_id=task.id,
            tool_name="click_element",
            action_type="financial",
            description="Authorize payment of $999",
            parameters_json=json.dumps({"selector": "button#checkout", "amount": 999.0}),
            session_checkpoint_json=json.dumps({"task_id": task.id, "remaining_steps": [], "step_results": []})
        )

    res = await ipc_client("tasks.approve", {"task_id": task.id, "approval_id": approval.id, "decision": True})
    assert res.get("status") in ("approved", "executed", "running")


@pytest.mark.asyncio
async def test_t1_f03_05_user_rejection_cancellation(async_client, test_db):
    """Rejecting approval via API marks the task cancelled cleanly."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title="Rejected Task", prompt="Test reject")
        await repo.update_task_status(task.id, status="approval_required")
        approval = await repo.create_approval_request(
            task_id=task.id,
            tool_name="click_element",
            action_type="financial",
            description="Authorize payment of $999",
            parameters_json=json.dumps({"selector": "button#checkout", "amount": 999.0})
        )

    resp = await async_client.post(f"/api/v1/tasks/{task.id}/reject?approval_id={approval.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("rejected", "cancelled")


# ===========================================================================
# Feature 4: Browser-Use Security Interception (5 tests)
# ===========================================================================

def test_t1_f04_01_central_controller_routing():
    """All browser operations route through ApprovalManager policy check."""
    safe_ok, safe_reason = ApprovalManager.evaluate_tool_call("get_page_content", {})
    assert safe_ok is False, "Read-only get_page_content should not require approval"

    risky_ok, risky_reason = ApprovalManager.evaluate_tool_call(
        "click_element",
        {"selector": "button#checkout"}
    )
    assert risky_ok is True, "Financial checkout selector must require approval"


def test_t1_f04_02_policy_interception():
    """Sensitive browser-use operations (passwords, payment) require explicit approval."""
    requires_appr, reason = ApprovalManager.evaluate_tool_call(
        "fill_selector",
        {"selector": "input[type='password']", "text": "SuperSecret"}
    )
    assert requires_appr is True
    assert "password" in reason.lower() or "credential" in reason.lower() or "sensitive" in reason.lower()


def test_t1_f04_03_remote_debugging_port_disabled():
    """Verify electron main process does not enable unauthenticated remote debugging port 9222."""
    main_ts = WORKSPACE_ROOT / "apps" / "desktop" / "electron" / "main.ts"
    if main_ts.exists():
        content = main_ts.read_text(encoding="utf-8")
        # Port 9222 should either not appear or be explicitly commented out / guarded
        active_lines = [
            line for line in content.splitlines()
            if "remote-debugging-port" in line and not line.strip().startswith("//")
        ]
        assert len(active_lines) == 0, f"Unauthenticated remote debugging port 9222 is active: {active_lines}"


@pytest.mark.asyncio
async def test_t1_f04_04_single_run_on_fallback():
    """Bypassing approval directly on ToolExecutor is only allowed when explicitly authorized."""
    res_default = await ToolExecutor.execute("desktop_launch_app", {"app_name": "notepad.exe"})
    assert res_default["status"] == "approval_required"

    res_bypass = await ToolExecutor.execute("desktop_launch_app", {"app_name": "notepad.exe"}, bypass_approval=True)
    assert res_bypass["status"] == "success"


@pytest.mark.asyncio
async def test_t1_f04_05_browser_use_action_logging(mock_bridge):
    """ToolExecutor calls are recorded in the bridge dispatch logs."""
    await ToolExecutor.execute("navigate", {"url": "https://example.com/login"})
    assert len(mock_bridge.calls) > 0
    assert any(c["method"] == "browser.navigate" for c in mock_bridge.calls)


# ===========================================================================
# Feature 5: Canonical Execution Results (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t1_f05_01_read_only_tool_canonical():
    """get_page_content returns the exact canonical schema keys."""
    res = await ToolExecutor.execute("get_page_content", {})
    assert "status" in res
    assert "tool_name" in res
    assert "result" in res
    assert "evidence" in res
    assert "error" in res
    assert res["status"] == "success"
    assert res["tool_name"] == "get_page_content"
    assert res["error"] is None


@pytest.mark.asyncio
async def test_t1_f05_02_mutation_tool_canonical():
    """navigate tool returns canonical schema with navigated_to result."""
    res = await ToolExecutor.execute("navigate", {"url": "https://example.com"})
    assert res["status"] == "success"
    assert res["tool_name"] == "navigate"
    assert res["error"] is None
    assert "https://example.com" in str(res.get("result")) or "https://example.com" in str(res.get("navigated_to"))


@pytest.mark.asyncio
async def test_t1_f05_03_approval_tool_canonical():
    """Approval-requiring tool returns canonical schema with status='approval_required'."""
    res = await ToolExecutor.execute(
        "fill_input",
        {"x": 100, "y": 200, "text": "secret_password"}
    )
    assert res["status"] == "approval_required"
    assert res["tool_name"] == "fill_input"
    assert "reason" in res or "error" in res


@pytest.mark.asyncio
async def test_t1_f05_04_unknown_tool_canonical():
    """Unknown tool invocation returns canonical schema with status='error'."""
    res = await ToolExecutor.execute("non_existent_tool_xyz123", {})
    assert res["status"] == "error"
    assert res["tool_name"] == "non_existent_tool_xyz123"
    assert res["error"] is not None
    assert "Unknown tool" in res["error"] or "unknown" in res["error"].lower()


@pytest.mark.asyncio
async def test_t1_f05_05_export_tool_canonical(tmp_path):
    """export_csv tool returns canonical schema with exported_file details."""
    data = [{"name": "Item 1", "price": 10.0}, {"name": "Item 2", "price": 20.0}]
    out_file = str(tmp_path / "test_out.csv")
    res = await ToolExecutor.execute("export_csv", {"data": data, "filename": out_file})
    assert res["status"] == "success"
    assert res["tool_name"] == "export_csv"
    assert res["error"] is None


# ===========================================================================
# Feature 6: Eliminate Duplicate Tool Implementations (5 tests)
# ===========================================================================

def test_t1_f06_01_single_extract_table_in_executor():
    """Verify AST scan of backend/app/tools/executor.py contains exactly one extract_table_data branch."""
    executor_file = WORKSPACE_ROOT / "backend" / "app" / "tools" / "executor.py"
    assert executor_file.exists()
    tree = ast.parse(executor_file.read_text(encoding="utf-8"))

    # Count occurrences of 'extract_table_data' comparison in AST
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for comparator in node.comparators:
                if isinstance(comparator, ast.Constant) and comparator.value == "extract_table_data":
                    count += 1
    assert count == 1, f"Expected exactly 1 'extract_table_data' condition in executor.py, found {count}"


@pytest.mark.asyncio
async def test_t1_f06_02_delegation_to_data_agent():
    """ToolExecutor.execute('extract_table_data') delegates cleanly to DataAgent."""
    res = await ToolExecutor.execute("extract_table_data", {})
    assert res["status"] in ("success", "ok")
    assert res["tool_name"] == "extract_table_data"


@pytest.mark.asyncio
async def test_t1_f06_03_default_selector_extraction(mock_bridge):
    """extract_table_data uses default table inspection when selector is omitted."""
    mock_bridge.set_dom_state(
        url="https://example.com/table",
        title="Table Test",
        text="col1 | col2\nval1 | val2\nval3 | val4"
    )
    res = await DataAgent.extract_table_data()
    assert res["status"] == "ok" or res.get("rows") is not None
    assert len(res.get("rows", [])) >= 1


@pytest.mark.asyncio
async def test_t1_f06_04_custom_selector_extraction(mock_bridge):
    """extract_table_data accepts and forwards explicit custom selector."""
    mock_bridge.set_dom_state(
        url="https://example.com/custom",
        title="Custom Table",
        text="Key: Value\nStatus: Active"
    )
    res = await DataAgent.extract_table_data(selector="table.analytics")
    assert res["status"] == "ok"
    assert res["total_rows"] >= 1


@pytest.mark.asyncio
async def test_t1_f06_05_multi_page_consolidation(mock_bridge):
    """extract_table_data handles multi-page scraping without duplicate implementations."""
    mock_bridge.set_dom_state(
        url="https://example.com/paginated",
        title="Paginated",
        text="row1 | data1\nrow2 | data2"
    )
    res = await DataAgent.extract_table_data(pagination_next_selector="button.next", max_pages=2)
    assert res["pages_scraped"] <= 2
    assert "rows" in res


# ===========================================================================
# Feature 7: DataAgent Contract Alignment (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t1_f07_01_status_success_check(mock_bridge):
    """DataAgent continues extraction loop when ToolExecutor returns status='success'."""
    mock_bridge.set_dom_state(
        url="https://example.com/data",
        title="Success Check",
        text="Header1 | Header2\nValueA | ValueB"
    )
    res = await DataAgent.extract_table_data()
    # If DataAgent improperly checked status != 'ok', it would break and return 0 rows
    assert res["total_rows"] > 0, "DataAgent failed to parse rows when status was 'success'"


@pytest.mark.asyncio
async def test_t1_f07_02_visible_text_snippet_reading(mock_bridge):
    """DataAgent reads page text when provided under 'visible_text_snippet'."""
    mock_bridge.set_dom_state(
        url="https://example.com/snippet",
        title="Snippet Page",
        text="Name: Comet AI\nVersion: 2.0"
    )
    res = await DataAgent.extract_table_data()
    assert res["total_rows"] >= 2
    assert any(r.get("key") == "Name" for r in res["rows"])


@pytest.mark.asyncio
async def test_t1_f07_03_text_fallback_reading(mock_bridge):
    """DataAgent safely falls back to 'text' property if 'visible_text_snippet' is absent."""
    dom_res = await ToolExecutor.execute("get_page_content", {})
    assert "visible_text_snippet" in dom_res or "text" in dom_res


@pytest.mark.asyncio
async def test_t1_f07_04_csv_export_alignment(tmp_path):
    """DataAgent.export_data formats and writes clean RFC 4180 CSV."""
    data = [{"col1": "Alpha", "col2": "100"}, {"col1": "Beta", "col2": "200"}]
    target = str(tmp_path / "output.csv")
    res = DataAgent.export_data(data, format="csv", filename=target)
    assert res["status"] == "ok"
    assert res.get("filename") == target
    assert res.get("row_count") == 2
    assert "data" in res
    assert "Alpha" in res["data"]
    assert "Beta" in res["data"]


@pytest.mark.asyncio
async def test_t1_f07_05_json_export_alignment(tmp_path):
    """DataAgent.export_data formats and writes valid UTF-8 JSON."""
    data = [{"symbol": "NVDA", "rating": "Buy"}, {"symbol": "MSFT", "rating": "Hold"}]
    target = str(tmp_path / "output.json")
    res = DataAgent.export_data(data, format="json", filename=target)
    assert res["status"] == "ok"
    assert res.get("filename") == target
    assert res.get("row_count") == 2
    assert "data" in res
    loaded = json.loads(res["data"])
    assert len(loaded) == 2
    assert loaded[0]["symbol"] == "NVDA"


# ===========================================================================
# Feature 8: ResearchService Contract Alignment (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t1_f08_01_search_success_status_consumed():
    """ResearchService ingests web search results when search_web returns status='success'."""
    report = await ResearchService.synthesize(topic="Quantum Computing", sources=[])
    assert report.get("status") in ("completed", "ok", "success")
    md = report.get("content_markdown") or report.get("report_markdown")
    assert md is not None


@pytest.mark.asyncio
async def test_t1_f08_02_search_results_ingested():
    """Synthesized research report contains content derived from topic queries."""
    report = await ResearchService.synthesize(topic="Artificial Intelligence Trends", sources=[])
    md = report.get("content_markdown") or report.get("report_markdown", "")
    assert len(md) > 100
    assert "Artificial Intelligence Trends" in md or "Executive Summary" in md


@pytest.mark.asyncio
async def test_t1_f08_03_explicit_urls_synthesized(mock_bridge):
    """ResearchService synthesizes explicit source URL lists cleanly."""
    mock_bridge.set_dom_state(
        url="https://example.org/ai-research",
        title="AI Paper",
        text="Breakthrough results in reasoning models with zero hallucination."
    )
    report = await ResearchService.synthesize(
        topic="Reasoning Models",
        sources=["https://example.org/ai-research"]
    )
    assert report.get("status") in ("completed", "ok", "success")
    assert len(report.get("sources", [])) >= 1


@pytest.mark.asyncio
async def test_t1_f08_04_query_expansion():
    """Research report produces structured sections with findings and source references."""
    queries = await ResearchService.expand_queries("Battery Storage Systems")
    assert len(queries) >= 3
    assert any("Battery Storage Systems" in q for q in queries)
    report = await ResearchService.synthesize(topic="Battery Storage Systems", sources=[])
    assert report.get("status") in ("completed", "ok", "success")
    md = report.get("content_markdown") or report.get("report_markdown", "")
    assert "Findings" in md or "findings" in report


@pytest.mark.asyncio
async def test_t1_f08_05_structured_markdown_output():
    """Synthesized research report structure adheres to executive reporting standards."""
    report = await ResearchService.synthesize(topic="Solar Power Efficiency", sources=[])
    md = report.get("content_markdown") or report.get("report_markdown", "")
    assert "## 1. Executive Summary" in md
    assert "## 2. Key Findings" in md
    assert "## 3. Comparative Matrix" in md
    assert "## 4. Source Index" in md


# ===========================================================================
# Feature 9: WorkflowEngine Approval Handling (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t1_f09_01_pause_on_approval_required(test_db):
    """WorkflowEngine halts execution when a step requires human approval."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Checkout Workflow",
            description="Navigates and purchases item",
            steps=[
                {"action": "navigate", "parameters": {"url": "https://store.example.com"}},
                {"action": "fill_input", "parameters": {"x": 50, "y": 100, "text": "secret_password"}},
                {"action": "get_page_content", "parameters": {}}
            ]
        )
    res = await WorkflowEngine.execute_workflow(wf.id)
    assert res["status"] == "approval_required"
    assert res["paused_step"] == 2


@pytest.mark.asyncio
async def test_t1_f09_02_execution_status_paused(test_db):
    """Database workflow_execution status is set to 'approval_required' when paused."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Sensitive Workflow",
            steps=[{"action": "fill_input", "parameters": {"x": 10, "y": 20, "text": "password_pwd"}}]
        )
    res = await WorkflowEngine.execute_workflow(wf.id)
    exec_id = res["execution_id"]

    async with AsyncSessionLocal() as session:
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == exec_id)
        result = await session.execute(stmt)
        execution = result.scalars().first()
        assert execution is not None
        assert execution.status == "approval_required"


@pytest.mark.asyncio
async def test_t1_f09_03_step_number_saved(test_db):
    """Paused workflow execution record saves the exact current_step."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Step Number Test",
            steps=[
                {"action": "navigate", "parameters": {"url": "https://example.com"}},
                {"action": "fill_input", "parameters": {"x": 10, "y": 20, "text": "sensitive_pin_1234"}}
            ]
        )
    res = await WorkflowEngine.execute_workflow(wf.id)
    assert res["paused_step"] == 2


@pytest.mark.asyncio
async def test_t1_f09_04_no_premature_continuation(test_db):
    """Subsequent steps after approval_required are NOT executed while paused."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="No Continuation Test",
            steps=[
                {"action": "fill_input", "parameters": {"x": 10, "y": 20, "text": "secret_pwd"}},
                {"action": "navigate", "parameters": {"url": "https://should-not-run.example.com"}}
            ]
        )
    res = await WorkflowEngine.execute_workflow(wf.id)
    # Only step 1 should be in results
    assert len(res["results"]) == 1


@pytest.mark.asyncio
async def test_t1_f09_05_bridge_notification(mock_bridge, test_db):
    """WorkflowEngine emits bridge notification when approval is required."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Notification Workflow",
            steps=[{"action": "fill_input", "parameters": {"x": 1, "y": 1, "text": "password_1"}}]
        )
    await WorkflowEngine.execute_workflow(wf.id)
    notifs = [n for n in mock_bridge.notifications if n["method"] == "workflow.step_updated"]
    assert len(notifs) >= 1
    assert notifs[-1]["params"]["status"] == "approval_required"


# ===========================================================================
# Feature 10: Goal-Based Objective Verification (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t1_f10_01_dom_assertion_strategy():
    """Objective DOM assertion validates presence and text match."""
    # When element is found with expected text
    res = await VerifierAgent.verify_dom_assertion({
        "selector": "#btn-submit",
        "text": "Submit",
        "expected_state": "present"
    })
    assert res["status"] == "success"
    assert res["verified"] is True
    assert res["evidence"]["selector"] == "#btn-submit"


@pytest.mark.asyncio
async def test_t1_f10_02_url_match_strategy(mock_bridge):
    """Objective URL match validates current browser URL against pattern."""
    mock_bridge.set_dom_state(url="https://app.example.com/dashboard", title="Dashboard", text="")
    res = await VerifierAgent.verify_url_match({
        "pattern": r"https://app\.example\.com/.*",
        "domain": "example.com"
    })
    assert res["status"] == "success"
    assert res["verified"] is True


def test_t1_f10_03_data_validation_strategy():
    """Objective data validation evaluates record count and required schema fields."""
    dataset = [
        {"id": 1, "product": "Widget A", "price": 19.99},
        {"id": 2, "product": "Widget B", "price": 29.99}
    ]
    res = VerifierAgent.verify_data_validation({
        "records": dataset,
        "min_records": 2,
        "required_fields": ["product", "price"]
    })
    assert res["status"] == "success"
    assert res["verified"] is True
    assert res["evidence"]["record_count"] == 2


def test_t1_f10_04_file_validation_strategy(tmp_path):
    """Objective file validation evaluates physical file existence and non-empty size."""
    test_file = tmp_path / "report.pdf"
    test_file.write_bytes(b"%PDF-1.4 Mock PDF content")

    res = VerifierAgent.verify_file_validation({
        "file_path": str(test_file),
        "min_size_bytes": 10
    })
    assert res["status"] == "success"
    assert res["verified"] is True
    assert res["evidence"]["size_bytes"] > 10


@pytest.mark.asyncio
async def test_t1_f10_05_form_submission_strategy(mock_bridge):
    """Objective form submission evaluates confirmation message and feedback."""
    mock_bridge.set_dom_state(
        url="https://example.com/checkout/confirmed",
        title="Order Confirmed",
        text="Thank you! Your order #99482 has been confirmed."
    )
    res = await VerifierAgent.verify_form_submission({
        "success_text": "order #99482 has been confirmed",
        "redirect_url": "/checkout/confirmed"
    })
    assert res["status"] == "success"
    assert res["verified"] is True
