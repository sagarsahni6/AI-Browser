"""
tests/e2e/tier2_boundaries/test_t2_f01_f10.py
Tier 2 Boundary Value & Error Condition Tests: Features 1 to 10 (50 tests total, 5 per feature).

Features Covered:
  F01: Repository Audit Document Bounds
  F02: Architecture & Tech Stack Preservation Bounds
  F03: Persistent Approval Lifecycle Bounds
  F04: Browser-Use Security Interception Bounds
  F05: Canonical Execution Results Bounds
  F06: Eliminate Duplicate Tool Implementations Bounds
  F07: DataAgent Bounds
  F08: ResearchService Bounds
  F09: WorkflowEngine Bounds
  F10: Goal-Based Objective Verification Bounds
"""

import os
import sys
import json
import pytest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, AsyncMock, MagicMock

from backend.app.config import settings
from backend.app.tools.executor import ToolExecutor
from backend.app.security.approval import ApprovalManager
from backend.app.agents.data_agent import DataAgent
from backend.app.research.service import ResearchService
from backend.app.agents.verifier import VerifierAgent
from backend.app.workflows.engine import WorkflowEngine
from backend.app.database.repository import Repository
from backend.app.database.engine import AsyncSessionLocal
from backend.app.agents.supervisor import SupervisorAgent
from backend.app.agents.browser_use_agent import BrowserUseEngine
from backend.app.browser.bridge import bridge

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent


# ===========================================================================
# Feature 1: Repository Audit Document Bounds (5 tests)
# ===========================================================================

def test_t2_f01_01_audit_doc_empty_file():
    """Boundary: docs/UPGRADE_AUDIT.md must exist and not be a 0-byte empty file."""
    audit_file = WORKSPACE_ROOT / "docs" / "UPGRADE_AUDIT.md"
    assert audit_file.exists(), "docs/UPGRADE_AUDIT.md must exist"
    assert audit_file.stat().st_size > 0, "docs/UPGRADE_AUDIT.md cannot be 0 bytes"


def test_t2_f01_02_audit_doc_minimum_length():
    """Boundary: docs/UPGRADE_AUDIT.md must contain >= 50 lines to ensure thoroughness."""
    audit_file = WORKSPACE_ROOT / "docs" / "UPGRADE_AUDIT.md"
    lines = audit_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 50, f"docs/UPGRADE_AUDIT.md has only {len(lines)} lines; expected >= 50"


def test_t2_f01_03_audit_doc_malformed_tables():
    """Boundary: Markdown tables in docs/UPGRADE_AUDIT.md must have consistent column delimiters."""
    audit_file = WORKSPACE_ROOT / "docs" / "UPGRADE_AUDIT.md"
    content = audit_file.read_text(encoding="utf-8")
    table_lines = [line.strip() for line in content.splitlines() if line.strip().startswith("|") and line.strip().endswith("|")]
    assert len(table_lines) >= 5, "Audit document must contain structured markdown table rows"
    col_counts = [len(line.split("|")) - 2 for line in table_lines if not set(line.replace("|", "").strip()).issubset({"-", ":", " "})]
    # Validate non-separator rows share the expected column count
    expected_cols = col_counts[0]
    assert expected_cols >= 4, f"Table header has {expected_cols} columns; expected >= 4"
    for idx, count in enumerate(col_counts[:10]):
        assert count == expected_cols, f"Table row {idx} has {count} columns, expected {expected_cols}"


def test_t2_f01_04_audit_doc_encoding():
    """Boundary: docs/UPGRADE_AUDIT.md must be valid UTF-8 without unicode replacement characters."""
    audit_file = WORKSPACE_ROOT / "docs" / "UPGRADE_AUDIT.md"
    raw_bytes = audit_file.read_bytes()
    decoded = raw_bytes.decode("utf-8")
    assert "\ufffd" not in decoded, "docs/UPGRADE_AUDIT.md contains corrupted UTF-8 replacement characters"


def test_t2_f01_05_audit_doc_relative_paths():
    """Boundary: All source files referenced in UPGRADE_AUDIT.md findings must exist in workspace."""
    audit_file = WORKSPACE_ROOT / "docs" / "UPGRADE_AUDIT.md"
    content = audit_file.read_text(encoding="utf-8")
    critical_paths = [
        "backend/app/tools/executor.py",
        "backend/app/agents/data_agent.py",
        "backend/app/research/service.py",
        "backend/app/workflows/engine.py",
        "backend/app/agents/verifier.py",
        "apps/desktop/electron/main.ts"
    ]
    for p in critical_paths:
        assert p in content, f"Audit doc must cite critical component path '{p}'"
        assert (WORKSPACE_ROOT / p).exists(), f"Path '{p}' referenced in audit doc must exist in repo"


# ===========================================================================
# Feature 2: Architecture & Tech Stack Preservation Bounds (5 tests)
# ===========================================================================

def test_t2_f02_01_no_unauthorized_frameworks():
    """Boundary: Prohibited external agent frameworks must not be in dependencies."""
    pyproject_path = WORKSPACE_ROOT / "backend" / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8").lower()
    prohibited = ["langchain", "crewai", "autogen", "llamaindex", "semantic-kernel"]
    for framework in prohibited:
        assert framework not in content, f"Unauthorized framework '{framework}' declared in backend dependencies"


def test_t2_f02_02_no_external_databases():
    """Boundary: No external SQL or vector DB drivers added to pyproject.toml."""
    pyproject_path = WORKSPACE_ROOT / "backend" / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8").lower()
    external_dbs = ["psycopg2", "asyncpg", "pymongo", "motor", "mysqlclient", "chromadb", "pinecone"]
    for db in external_dbs:
        assert db not in content, f"Unauthorized external database driver '{db}' declared in backend"


def test_t2_f02_03_python_version_guard():
    """Boundary: Python runtime version must strictly be >= 3.11."""
    assert sys.version_info >= (3, 11), f"Python version {sys.version} is lower than required 3.11"
    pyproject_path = WORKSPACE_ROOT / "backend" / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8")
    assert ">=3.11" in content or ">= 3.11" in content, "requires-python must specify >= 3.11"


def test_t2_f02_04_electron_unauthorized_ipc():
    """Boundary: Electron preload must only expose the approved electronAPI contract."""
    preload_path = WORKSPACE_ROOT / "apps" / "desktop" / "electron" / "preload.ts"
    assert preload_path.exists(), "apps/desktop/electron/preload.ts must exist"
    content = preload_path.read_text(encoding="utf-8")
    assert "contextBridge.exposeInMainWorld" in content
    assert "electronAPI" in content
    # Ensure no node process or child_process leaked directly to window
    assert "exposeInMainWorld('process'" not in content
    assert "exposeInMainWorld('child_process'" not in content


def test_t2_f02_05_strict_dependencies_lock():
    """Boundary: Root package.json and backend pyproject.toml must be structurally valid."""
    pkg_json_path = WORKSPACE_ROOT / "package.json"
    assert pkg_json_path.exists(), "Root package.json must exist"
    data = json.loads(pkg_json_path.read_text(encoding="utf-8"))
    assert "dependencies" in data or "devDependencies" in data
    assert data.get("name") in ("ai-browser", "ai-browser-monorepo") or "ai" in data.get("name", "")


# ===========================================================================
# Feature 3: Persistent Approval Lifecycle Bounds (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t2_f03_01_double_approval_idempotency(test_db):
    """Boundary: Submitting approval for an already executed/resolved request returns error."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Double Approval Task", "Testing idempotency")
        appr = await repo.create_approval_request(
            task_id=task.id,
            tool_name="export_csv",
            action_type="sensitive",
            description="First approval",
            parameters_json=json.dumps({"filename": "test.csv"}),
            step_number=1,
            session_checkpoint_json=json.dumps({"task_id": task.id, "remaining_steps": []})
        )
        task_id = task.id
        appr_id = appr.id

    # First resolution: reject to mark it resolved
    res1 = await SupervisorAgent.resume_approved_task(task_id, approval_id=appr_id, decision=False)
    assert res1["status"] == "rejected"

    # Second approval attempt on the same resolved approval must return error
    res2 = await SupervisorAgent.resume_approved_task(task_id, approval_id=appr_id, decision=True)
    assert res2["status"] == "error"
    assert "No pending approval" in res2["error"]


@pytest.mark.asyncio
async def test_t2_f03_02_invalid_approval_id(test_db):
    """Boundary: Calling resume_approved_task with nonexistent approval_id returns error."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Invalid ID Task", "Testing bad approval ID")
        task_id = task.id

    res = await SupervisorAgent.resume_approved_task(task_id, approval_id="nonexistent-approval-9999", decision=True)
    assert res["status"] == "error"
    assert "No pending approval" in res["error"]


@pytest.mark.asyncio
async def test_t2_f03_03_missing_decision_parameter(test_db):
    """Boundary: Omitting decision parameter defaults to decision=True safely."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Default Decision Task", "Testing default param")
        appr = await repo.create_approval_request(
            task_id=task.id,
            tool_name="export_csv",
            action_type="sensitive",
            description="Approve without explicit decision flag",
            parameters_json=json.dumps({"filename": "default.csv", "headers": ["A"], "rows": [["1"]]}),
            step_number=1,
            session_checkpoint_json=json.dumps({"task_id": task.id, "remaining_steps": [], "step_results": []})
        )
        task_id = task.id
        appr_id = appr.id

    with patch.object(bridge, "call", new_callable=AsyncMock) as mock_bridge, \
         patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_bridge.return_value = {"title": "Page", "url": "https://example.com"}
        mock_exec.return_value = {"status": "success", "tool_name": "export_csv", "result": {}, "evidence": {}, "error": None}

        # Call without decision kwarg (defaults to decision=True)
        res = await SupervisorAgent.resume_approved_task(task_id, approval_id=appr_id)
        assert res["status"] == "approved"
        assert mock_exec.call_count >= 1
        assert any(call.args[0] == "export_csv" for call in mock_exec.call_args_list)


@pytest.mark.asyncio
async def test_t2_f03_04_context_revalidation_failure_handled(test_db):
    """Boundary: If browser.inspect throws during revalidation, resumption proceeds safely."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Revalidation Fault Task", "Testing inspection exception")
        appr = await repo.create_approval_request(
            task_id=task.id,
            tool_name="export_csv",
            action_type="sensitive",
            description="Inspection fails",
            parameters_json=json.dumps({"filename": "fault.csv"}),
            step_number=1,
            session_checkpoint_json=json.dumps({"task_id": task.id, "remaining_steps": [], "step_results": []})
        )
        task_id = task.id
        appr_id = appr.id

    with patch.object(bridge, "call", side_effect=RuntimeError("CDP connection dropped")), \
         patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"status": "success", "tool_name": "export_csv", "result": {}, "evidence": {}, "error": None}

        # Should not raise uncaught exception
        res = await SupervisorAgent.resume_approved_task(task_id, approval_id=appr_id, decision=True)
        assert res["status"] == "approved"
        assert mock_exec.call_count >= 1
        assert any(call.args[0] == "export_csv" for call in mock_exec.call_args_list)


@pytest.mark.asyncio
async def test_t2_f03_05_rejection_marks_cancelled(test_db):
    """Boundary: Rejection immediately cancels task and sets resolved_at timestamp."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Rejection Test Task", "Verify cancellation")
        appr = await repo.create_approval_request(
            task_id=task.id,
            tool_name="desktop_launch_app",
            action_type="sensitive",
            description="Launch terminal",
            parameters_json=json.dumps({"app_name": "cmd.exe"}),
            step_number=1,
            session_checkpoint_json=json.dumps({"task_id": task.id, "remaining_steps": []})
        )
        task_id = task.id
        appr_id = appr.id

    res = await SupervisorAgent.resume_approved_task(task_id, approval_id=appr_id, decision=False)
    assert res["status"] == "rejected"

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        t = await repo.get_task(task_id)
        assert t.status == "cancelled"
        a = await repo.get_approval_request(appr_id)
        assert a.status == "rejected"
        assert a.resolved_at is not None


# ===========================================================================
# Feature 4: Browser-Use Security Interception Bounds (5 tests)
# ===========================================================================

def test_t2_f04_01_external_cdp_port_connection_refused():
    """Boundary: Electron launch configuration must not expose CDP port 9222."""
    main_ts_path = WORKSPACE_ROOT / "apps" / "desktop" / "electron" / "main.ts"
    content = main_ts_path.read_text(encoding="utf-8")
    assert "remote-debugging-port" not in content, "remote-debugging-port switch must not exist in main.ts"
    assert "9222" not in content, "Port 9222 must not be opened in Electron main"


def test_t2_f04_02_browser_use_unauthorized_eval():
    """Boundary: evaluate_javascript with restricted patterns requires RED TIER approval."""
    patterns = ["document.cookie", "fetch('https://malicious.com')", "window.location = 'http://attacker.com'"]
    for pat in patterns:
        requires_appr, reason = ApprovalManager.evaluate_tool_call("evaluate_javascript", {"script": pat})
        assert requires_appr is True, f"Script pattern '{pat}' must require approval"
        assert "RED TIER" in reason


@pytest.mark.asyncio
async def test_t2_f04_03_browser_use_crash_recovery(test_db):
    """Boundary: Exception inside BrowserUseEngine execution must mark task failed and not crash runtime."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("BrowserUse Crash Task", "Testing crash resilience")
        task_id = task.id

    with patch("browser_use.Agent.run", side_effect=Exception("Unrecoverable CDP crash")):
        res = await BrowserUseEngine.execute_task(task_id, "Trigger browser-use crash")
        assert res["status"] == "failed"
        assert "Unrecoverable CDP crash" in res["error"]

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        t = await repo.get_task(task_id)
        assert t.status == "failed"


@pytest.mark.asyncio
async def test_t2_f04_04_browser_use_empty_prompt(test_db):
    """Boundary: Empty prompt to BrowserUseEngine handled safely without hanging."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Empty Prompt Task", "")
        task_id = task.id

    with patch("browser_use.Agent.run", side_effect=ValueError("Prompt cannot be empty")):
        res = await BrowserUseEngine.execute_task(task_id, "")
        assert res["status"] == "failed"
        assert "empty" in res["error"].lower()


def test_t2_f04_05_default_engine_is_native():
    """Boundary: DEFAULT_AGENT_ENGINE must be set to 'native' to prevent unintercepted browser-use."""
    assert settings.DEFAULT_AGENT_ENGINE == "native", "DEFAULT_AGENT_ENGINE must be 'native'"


# ===========================================================================
# Feature 5: Canonical Execution Results Bounds (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t2_f05_01_empty_tool_name():
    """Boundary: Empty tool_name returns canonical error structure."""
    res = await ToolExecutor.execute("", {})
    assert res["status"] == "error"
    assert res["tool_name"] == ""
    assert "result" in res
    assert "evidence" in res
    assert res["error"] is not None
    assert "Unknown tool" in res["error"] or "error" in res["status"]


@pytest.mark.asyncio
async def test_t2_f05_02_none_params_handling():
    """Boundary: ToolExecutor.execute with params=None does not raise unhandled exception."""
    res = await ToolExecutor.execute("get_page_content", None)
    assert res["status"] == "success"
    assert res["tool_name"] == "get_page_content"
    assert "result" in res
    assert "evidence" in res
    assert res["error"] is None


@pytest.mark.asyncio
async def test_t2_f05_03_tool_exception_wrapping():
    """Boundary: Unhandled tool implementation exceptions are wrapped into canonical status='error'."""
    with patch.object(bridge, "call", side_effect=RuntimeError("IPC bridge pipe broken")):
        res = await ToolExecutor.execute("get_page_content", {})
        assert res["status"] == "error"
        assert res["tool_name"] == "get_page_content"
        assert "IPC bridge pipe broken" in str(res["error"])
        assert "result" in res
        assert "evidence" in res


@pytest.mark.asyncio
async def test_t2_f05_04_malformed_param_types():
    """Boundary: Passing invalid parameter types (e.g. dict for URL) handled with canonical schema."""
    res = await ToolExecutor.execute("navigate", {"url": {"bad": "object"}})
    assert "status" in res
    assert res["tool_name"] == "navigate"
    assert "result" in res
    assert "evidence" in res


@pytest.mark.asyncio
async def test_t2_f05_05_large_payload_handling():
    """Boundary: 1MB text input payload executes without memory overflow."""
    large_payload = "A" * (1024 * 1024)  # 1MB string
    res = await ToolExecutor.execute("fill_input", {"x": 50, "y": 50, "text": large_payload})
    assert "status" in res
    assert res["tool_name"] == "fill_input"
    assert "result" in res
    assert "evidence" in res


# ===========================================================================
# Feature 6: Eliminate Duplicate Tool Implementations Bounds (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t2_f06_01_no_table_found(mock_bridge):
    """Boundary: When DOM has no tabular text, DataAgent returns 0 rows without exception."""
    mock_bridge.set_dom_state(
        url="https://example.com/notable",
        title="Empty Page",
        text="Just a plain paragraph with no tables or lists."
    )
    res = await DataAgent.extract_table_data(max_pages=1)
    assert res["status"] in ("ok", "success")
    assert isinstance(res["rows"], list)


@pytest.mark.asyncio
async def test_t2_f06_02_invalid_css_selector(mock_bridge):
    """Boundary: Malformed CSS selector does not cause DataAgent to crash."""
    mock_bridge.set_dom_state(
        url="https://example.com/badselector",
        title="Bad Selector",
        text="Col1 | Col2\nVal1 | Val2"
    )
    res = await DataAgent.extract_table_data(selector="table[[[[invalid", max_pages=1)
    assert res["status"] in ("ok", "success")
    assert res["row_count"] >= 1


@pytest.mark.asyncio
async def test_t2_f06_03_huge_table_bounds(mock_bridge):
    """Boundary: Huge table text with 2,000 lines is bounded safely without memory exhaustion."""
    large_table = "\n".join([f"Item {i} | Value {i * 10}" for i in range(2000)])
    mock_bridge.set_dom_state(
        url="https://example.com/huge",
        title="Huge Table",
        text=large_table
    )
    res = await DataAgent.extract_table_data(max_pages=1)
    assert res["status"] in ("ok", "success")
    # Verified bounded to maximum reasonable chunk
    assert len(res["rows"]) <= 100


@pytest.mark.asyncio
async def test_t2_f06_04_empty_dom(mock_bridge):
    """Boundary: Extraction on empty DOM text returns 0 rows."""
    mock_bridge.set_dom_state(
        url="about:blank",
        title="Blank",
        text=""
    )
    res = await DataAgent.extract_table_data(max_pages=1)
    assert res["status"] in ("ok", "success")
    assert len(res["rows"]) == 0
    assert res["row_count"] == 0


@pytest.mark.asyncio
async def test_t2_f06_05_table_with_special_characters(mock_bridge):
    """Boundary: Table containing HTML entities and emojis parsed safely."""
    special_text = "Name | Price | Status\nCoffee &amp; Tea ☕ | $4.50 | In Stock &lt;New&gt;\nBurger 🍔 | $9.99 | Hot 🔥"
    mock_bridge.set_dom_state(
        url="https://example.com/special",
        title="Menu",
        text=special_text
    )
    res = await DataAgent.extract_table_data(max_pages=1)
    assert res["status"] in ("ok", "success")
    assert res["row_count"] >= 2


# ===========================================================================
# Feature 7: DataAgent Bounds (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t2_f07_01_dom_error_status_handling():
    """Boundary: DataAgent halts cleanly when get_page_content returns error."""
    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            "status": "error",
            "tool_name": "get_page_content",
            "error": "Tab crashed",
            "result": None,
            "evidence": {}
        }
        res = await DataAgent.extract_table_data(max_pages=3)
        assert res["status"] in ("ok", "success")
        assert len(res["rows"]) == 0


@pytest.mark.asyncio
async def test_t2_f07_02_empty_visible_text(mock_bridge):
    """Boundary: Empty visible text snippet produces empty dataset without crash."""
    mock_bridge.set_dom_state("https://example.com/empty", "Empty", "")
    res = await DataAgent.extract_table_data(max_pages=1)
    assert res["row_count"] == 0
    assert res["rows"] == []


def test_t2_f07_03_single_row_table():
    """Boundary: Exporting dataset with single record works cleanly in CSV and JSON."""
    data = [{"single_col": "single_val"}]
    res_csv = DataAgent.export_data(data, format="csv")
    assert res_csv["status"] == "ok"
    assert "single_col" in res_csv["data"]
    assert "single_val" in res_csv["data"]

    res_json = DataAgent.export_data(data, format="json")
    assert res_json["status"] == "ok"
    parsed = json.loads(res_json["data"])
    assert len(parsed) == 1
    assert parsed[0]["single_col"] == "single_val"


def test_t2_f07_04_missing_columns_ragged_rows():
    """Boundary: Ragged rows with disparate keys export without CSV writer error."""
    data = [
        {"a": 1, "b": 2},
        {"b": 3, "c": 4, "d": 5},
        {"e": 6}
    ]
    res = DataAgent.export_data(data, format="csv")
    assert res["status"] == "ok"
    assert res["row_count"] == 3


def test_t2_f07_05_export_empty_records():
    """Boundary: Exporting empty records list produces valid empty CSV and JSON."""
    res_csv = DataAgent.export_data([], format="csv")
    assert res_csv["status"] == "ok"
    assert res_csv["data"] == ""

    res_json = DataAgent.export_data([], format="json")
    assert res_json["status"] == "ok"
    assert json.loads(res_json["data"]) == []


# ===========================================================================
# Feature 8: ResearchService Bounds (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t2_f08_01_empty_query():
    """Boundary: ResearchService handles empty topic gracefully with direct analysis fallback."""
    report = await ResearchService.synthesize(topic="", sources=[])
    assert report["status"] in ("ok", "success", "completed")
    assert "content_markdown" in report
    assert len(report["content_markdown"]) > 50


@pytest.mark.asyncio
async def test_t2_f08_02_status_not_success_handling():
    """Boundary: When search_web returns status='error', ResearchService falls back cleanly."""
    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            "status": "error",
            "tool_name": "search_web",
            "error": "Rate limit exceeded",
            "result": None,
            "evidence": {}
        }
        report = await ResearchService.synthesize(topic="Quantum Encryption", sources=[])
        assert report["status"] in ("ok", "success", "completed")
        assert report["sources_count"] >= 1
        assert "local://analysis" in report["sources"][0]["url"]


@pytest.mark.asyncio
async def test_t2_f08_03_zero_search_results():
    """Boundary: When search_web returns 0 items, ResearchService falls back to local synthesis."""
    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            "status": "success",
            "tool_name": "search_web",
            "results": [],
            "result": {"results": []},
            "evidence": {},
            "error": None
        }
        report = await ResearchService.synthesize(topic="Extremely Obscure Topic 12345", sources=[])
        assert report["status"] in ("ok", "success", "completed")
        assert report["sources_count"] >= 1


@pytest.mark.asyncio
async def test_t2_f08_04_malformed_search_results():
    """Boundary: Search items missing title or snippet handled safely."""
    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            "status": "success",
            "tool_name": "search_web",
            "results": [
                {"bad_key": "bad_val"},
                {"url": "https://example.com/no-title"}
            ],
            "result": None,
            "evidence": {},
            "error": None
        }
        report = await ResearchService.synthesize(topic="Malformed Search Test", sources=[])
        assert report["status"] in ("ok", "success", "completed")
        assert len(report["sources"]) >= 1


@pytest.mark.asyncio
async def test_t2_f08_05_search_exception_recovery():
    """Boundary: Unhandled search exception recovers cleanly to local topic analysis."""
    with patch.object(ToolExecutor, "execute", side_effect=RuntimeError("Search network unreachable")):
        report = await ResearchService.synthesize(topic="Resilient AI", sources=[])
        assert report["status"] in ("ok", "success", "completed")
        assert "content_markdown" in report
        assert "## 1. Executive Summary" in report["content_markdown"]


# ===========================================================================
# Feature 9: WorkflowEngine Bounds (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t2_f09_01_missing_action(test_db):
    """Boundary: Workflow step with missing action returns failure status cleanly."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Missing Action Workflow",
            steps=[{"parameters": {"url": "https://example.com"}}]
        )
        wf_id = wf.id

    res = await WorkflowEngine.execute_workflow(wf_id)
    assert res["status"] in ("failed", "error")


@pytest.mark.asyncio
async def test_t2_f09_02_unapproved_step_rejection(test_db):
    """Boundary: Workflow containing sensitive step pauses on approval without running subsequent steps."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Approval Pause Workflow",
            steps=[
                {"action": "open_new_tab", "parameters": {"url": "https://example.com"}},
                {"action": "desktop_launch_app", "parameters": {"app_name": "calc.exe"}},
                {"action": "take_screenshot", "parameters": {}}
            ]
        )
        wf_id = wf.id

    res = await WorkflowEngine.execute_workflow(wf_id)
    assert res["status"] == "approval_required"
    assert res["paused_step"] == 2
    assert len(res["results"]) == 2  # Step 3 must NOT have been executed


@pytest.mark.asyncio
async def test_t2_f09_03_nonexistent_workflow_id():
    """Boundary: Executing nonexistent workflow ID returns error status."""
    res = await WorkflowEngine.execute_workflow("nonexistent-wf-1234")
    assert res["status"] == "error"
    assert "not found" in res["error"]


@pytest.mark.asyncio
async def test_t2_f09_04_step_failure_stops_execution(test_db):
    """Boundary: Failing tool step halts workflow immediately."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Failing Step Workflow",
            steps=[
                {"action": "unknown_tool_xyz", "parameters": {}},
                {"action": "take_screenshot", "parameters": {}}
            ]
        )
        wf_id = wf.id

    res = await WorkflowEngine.execute_workflow(wf_id)
    assert res["status"] == "failed"
    assert res["failed_step"] == 1
    assert len(res["results"]) == 1


def test_t2_f09_05_bad_variable_interpolation():
    """Boundary: Unclosed or missing variables in template interpolate without crashing."""
    raw_params = {
        "query": "{{valid_var}}",
        "missing": "{{unsupplied_var}}",
        "malformed": "{{unclosed_bracket",
        "nested": {"url": "https://example.com/search?q={{valid_var}}"}
    }
    interpolated = WorkflowEngine._interpolate(raw_params, {"valid_var": "ai_agents"})
    assert interpolated["query"] == "ai_agents"
    assert interpolated["missing"] == "{{unsupplied_var}}"
    assert interpolated["malformed"] == "{{unclosed_bracket"
    assert interpolated["nested"]["url"] == "https://example.com/search?q=ai_agents"


# ===========================================================================
# Feature 10: Goal-Based Objective Verification Bounds (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t2_f10_01_dom_element_missing():
    """Boundary: VerifierAgent dom_assertion returns verified=False when selector not found."""
    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            "status": "success",
            "result": {"found": False, "visible": False, "text": ""}
        }
        res = await VerifierAgent.execute_step("dom_assertion", {
            "selector": "#nonexistent-button"
        })
        assert res["status"] == "success"
        assert res["verified"] is False
        assert "not found" in res["reason"]


@pytest.mark.asyncio
async def test_t2_f10_02_partial_url_mismatch():
    """Boundary: VerifierAgent url_match returns verified=False when regex fails to match."""
    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            "status": "success",
            "url": "https://example.com/cart"
        }
        res = await VerifierAgent.execute_step("url_match", {
            "pattern": r"^https://example\.com/checkout/success$"
        })
        assert res["status"] == "success"
        assert res["verified"] is False
        assert "did not match" in res["reason"]


def test_t2_f10_03_zero_records_extracted():
    """Boundary: VerifierAgent data_validation returns verified=False when 0 records extracted."""
    res = VerifierAgent.verify_data_validation({
        "records": [],
        "min_records": 1
    })
    assert res["status"] == "success"
    assert res["verified"] is False
    assert "not a list" in res["reason"] or "fewer than required" in res["reason"]


def test_t2_f10_04_missing_exported_file():
    """Boundary: VerifierAgent file_validation returns verified=False when file does not exist."""
    res = VerifierAgent.verify_file_validation({
        "file_path": "nonexistent_export_file_12345.csv"
    })
    assert res["status"] == "success"
    assert res["verified"] is False
    assert "does not exist" in res["reason"]


@pytest.mark.asyncio
async def test_t2_f10_05_verifier_missing_parameters():
    """Boundary: VerifierAgent handles missing selector or invalid strategy gracefully."""
    # Missing selector
    res1 = await VerifierAgent.execute_step("dom_assertion", {})
    assert res1["status"] == "error"
    assert res1["verified"] is False

    # Missing file path
    res2 = await VerifierAgent.execute_step("file_validation", {})
    assert res2["status"] == "error"
    assert res2["verified"] is False
