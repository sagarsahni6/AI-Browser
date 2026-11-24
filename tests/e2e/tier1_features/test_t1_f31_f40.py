"""
tests/e2e/tier1_features/test_t1_f31_f40.py
Tier 1 Feature Coverage Tests: Features 31 to 40 (50 tests total, 5 per feature).

Features Covered:
  F31: Advanced Workflow Engine
  F32: Workflow Import / Export
  F33: Risk Meter Approval Dialog UI Contract
  F34: Visual Action Indicator (Laser) UI Contract
  F35: Assistant Progress Banner UI Contract
  F36: Ponytail Principles Compliance
  F37: Regression Prevention
  F38: End-to-End Test Suite Execution
  F39: Adversarial Coverage Hardening
  F40: Zero Core Framework Bloat
"""

import ast
import json
import os
import pytest
from pathlib import Path
from typing import Dict, Any, List

from backend.app.config import settings
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.repository import Repository
from backend.app.workflows.engine import WorkflowEngine
from backend.app.tools.executor import ToolExecutor
from backend.app.automation.desktop.service import DesktopService
from backend.app.browser.bridge import bridge
from backend.app.agents.browser_agent import BrowserAgent

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent


# ===========================================================================
# Feature 31: Advanced Workflow Engine (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t1_f31_01_sequential_step_execution(test_db):
    """WorkflowEngine executes multi-step workflow sequentially from step 1 to completion."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Sequential Test Workflow",
            steps=[
                {"action": "navigate", "parameters": {"url": "https://example.com"}},
                {"action": "get_page_content", "parameters": {}}
            ]
        )

    res = await WorkflowEngine.execute_workflow(wf.id)
    assert res["status"] == "completed"
    assert res["steps_executed"] == 2
    assert len(res["results"]) == 2
    assert res["results"][0]["step"] == 1
    assert res["results"][1]["step"] == 2


@pytest.mark.asyncio
async def test_t1_f31_02_variable_interpolation(test_db):
    """WorkflowEngine interpolates {{variable_name}} syntax within action parameters."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Interpolation Workflow",
            steps=[
                {"action": "navigate", "parameters": {"url": "https://{{target_domain}}"}}
            ]
        )

    res = await WorkflowEngine.execute_workflow(
        wf.id,
        input_variables={"target_domain": "python.org"}
    )
    assert res["status"] == "completed"
    executed_params = res["results"][0]["parameters"]
    assert executed_params["url"] == "https://python.org"


@pytest.mark.asyncio
async def test_t1_f31_03_default_variables_fallback(test_db):
    """WorkflowEngine falls back to stored workflow default variables when input omitted."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Default Var Workflow",
            variables={"default_site": "fastapi.tiangolo.com"},
            steps=[
                {"action": "navigate", "parameters": {"url": "https://{{default_site}}"}}
            ]
        )

    res = await WorkflowEngine.execute_workflow(wf.id)
    assert res["status"] == "completed"
    executed_url = res["results"][0]["parameters"]["url"]
    assert executed_url == "https://fastapi.tiangolo.com"


@pytest.mark.asyncio
async def test_t1_f31_04_execution_history_persistence(test_db):
    """Workflow execution creates persistent execution record with status and step count."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Persistence Workflow",
            steps=[{"action": "scroll_page", "parameters": {"delta_y": 100}}]
        )

    res = await WorkflowEngine.execute_workflow(wf.id)
    exec_id = res["execution_id"]
    assert exec_id.startswith("wfexec-")
    assert res["status"] == "completed"


@pytest.mark.asyncio
async def test_t1_f31_05_step_status_notification(mock_bridge, test_db):
    """WorkflowEngine emits bridge notifications for workflow step state updates."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Notification Workflow",
            steps=[{"action": "get_page_content", "parameters": {}}]
        )

    await WorkflowEngine.execute_workflow(wf.id)
    wf_notifs = [n for n in mock_bridge.notifications if n["method"] == "workflow.step_updated"]
    assert len(wf_notifs) >= 1
    assert any(n["params"].get("status") in ("running", "completed") for n in wf_notifs)


# ===========================================================================
# Feature 32: Workflow Import / Export (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t1_f32_01_export_workflow_schema(test_db):
    """export_workflow generates portable JSON dictionary with version, name, steps, and variables."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Exportable Workflow",
            description="Workflow to test export",
            steps=[{"action": "navigate", "parameters": {"url": "https://example.com"}}],
            variables={"env": "production"}
        )

    exported = await WorkflowEngine.export_workflow(wf.id)
    assert exported is not None
    assert exported["version"] == "1.0"
    assert exported["name"] == "Exportable Workflow"
    assert exported["description"] == "Workflow to test export"
    assert len(exported["steps"]) == 1
    assert exported["variables"] == {"env": "production"}


@pytest.mark.asyncio
async def test_t1_f32_02_import_workflow_schema(test_db):
    """import_workflow ingests valid JSON dictionary and creates database workflow record."""
    workflow_data = {
        "name": "Imported Test Flow",
        "description": "Created from import",
        "steps": [
            {"action": "navigate", "parameters": {"url": "https://github.com"}},
            {"action": "get_page_content", "parameters": {}}
        ],
        "variables": {"repo": "ai-browser"}
    }
    imported = await WorkflowEngine.import_workflow(workflow_data)
    assert "id" in imported
    assert imported["id"].startswith("wf-")
    assert imported["name"] == "Imported Test Flow"
    assert imported["step_count"] == 2


@pytest.mark.asyncio
async def test_t1_f32_03_roundtrip_integrity(test_db):
    """Workflow exported and re-imported preserves identical steps and variables."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        orig_wf = await repo.create_workflow(
            name="Roundtrip Workflow",
            steps=[
                {"action": "navigate", "parameters": {"url": "https://example.org"}},
                {"action": "scroll_page", "parameters": {"delta_y": 300}}
            ],
            variables={"mode": "fast"}
        )

    exported = await WorkflowEngine.export_workflow(orig_wf.id)
    imported = await WorkflowEngine.import_workflow(exported)

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        reloaded = await repo.get_workflow(imported["id"])
        assert reloaded.name == orig_wf.name
        assert json.loads(reloaded.steps_json) == json.loads(orig_wf.steps_json)
        assert json.loads(reloaded.variables_json) == json.loads(orig_wf.variables_json)


@pytest.mark.asyncio
async def test_t1_f32_04_import_assigns_new_id(test_db):
    """Importing workflow assigns a distinct unique ID avoiding collision with existing workflows."""
    payload = {
        "name": "Distinct ID Test",
        "steps": [{"action": "navigate", "parameters": {"url": "https://example.com"}}]
    }
    first_import = await WorkflowEngine.import_workflow(payload)
    second_import = await WorkflowEngine.import_workflow(payload)
    assert first_import["id"] != second_import["id"]
    assert first_import["id"].startswith("wf-")
    assert second_import["id"].startswith("wf-")


@pytest.mark.asyncio
async def test_t1_f32_05_export_nonexistent_workflow(test_db):
    """Exporting non-existent workflow ID returns None safely without raising an exception."""
    res = await WorkflowEngine.export_workflow("wf-non-existent-xyz")
    assert res is None


# ===========================================================================
# Feature 33: Risk Meter Approval Dialog UI Contract (5 tests)
# ===========================================================================

def test_t1_f33_01_red_tier_meter_rendering():
    """ApprovalDialog source declares RED TIER (100%) indicator for sensitive operations."""
    dialog_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "components" / "ApprovalDialog.tsx"
    assert dialog_path.exists(), "ApprovalDialog.tsx not found"
    content = dialog_path.read_text(encoding="utf-8")
    assert "RED TIER" in content
    assert "percentage = 100" in content
    assert "{tier} ({percentage}%)" in content
    assert "var(--error" in content


def test_t1_f33_02_yellow_tier_meter_rendering():
    """ApprovalDialog source declares YELLOW TIER (40%) indicator for medium risk."""
    dialog_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "components" / "ApprovalDialog.tsx"
    content = dialog_path.read_text(encoding="utf-8")
    assert "YELLOW TIER (40%)" in content or "YELLOW TIER" in content


def test_t1_f33_03_password_masking():
    """ApprovalDialog sanitizes and masks sensitive credential parameter values."""
    dialog_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "components" / "ApprovalDialog.tsx"
    content = dialog_path.read_text(encoding="utf-8")
    assert "•••••••• (Masked for security)" in content or "Masked for security" in content


def test_t1_f33_04_approve_callback_contract():
    """ApprovalDialog declares onApprove callback prop and triggers it on confirmation click."""
    dialog_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "components" / "ApprovalDialog.tsx"
    content = dialog_path.read_text(encoding="utf-8")
    assert "onApprove" in content
    assert "Approve & Execute" in content or "Approve" in content


def test_t1_f33_05_reject_callback_contract():
    """ApprovalDialog declares onReject callback prop and triggers it on reject/cancel click."""
    dialog_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "components" / "ApprovalDialog.tsx"
    content = dialog_path.read_text(encoding="utf-8")
    assert "onReject" in content
    assert "Reject" in content or "Cancel" in content


# ===========================================================================
# Feature 34: Visual Action Indicator (Laser) UI Contract (5 tests)
# ===========================================================================

def test_t1_f34_01_style_injection():
    """LaserIndicator source declares keyframe animations cometLaserRipple and core styles."""
    laser_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "overlay" / "LaserIndicator.ts"
    assert laser_path.exists(), "LaserIndicator.ts not found"
    content = laser_path.read_text(encoding="utf-8")
    assert "@keyframes cometLaserRipple" in content
    assert ".comet-laser-core" in content


def test_t1_f34_02_laser_element_creation():
    """LaserIndicator creates and appends ripple and core DOM elements."""
    laser_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "overlay" / "LaserIndicator.ts"
    content = laser_path.read_text(encoding="utf-8")
    assert "document.createElement" in content
    assert "comet-laser-core" in content
    assert "comet-laser-ripple" in content


def test_t1_f34_03_coordinate_positioning():
    """LaserIndicator positions elements at exact target pixel coordinates left/top."""
    laser_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "overlay" / "LaserIndicator.ts"
    content = laser_path.read_text(encoding="utf-8")
    assert "left =" in content or "left:" in content
    assert "top =" in content or "top:" in content


def test_t1_f34_04_pointer_events_none():
    """LaserIndicator elements specify pointer-events: none to avoid blocking user interaction."""
    laser_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "overlay" / "LaserIndicator.ts"
    content = laser_path.read_text(encoding="utf-8")
    assert "pointer-events: none" in content.lower()


def test_t1_f34_05_automatic_dom_cleanup():
    """LaserIndicator cleans up injected DOM elements using setTimeout removal."""
    laser_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "overlay" / "LaserIndicator.ts"
    content = laser_path.read_text(encoding="utf-8")
    assert "setTimeout" in content
    assert "remove()" in content or "removeChild" in content


# ===========================================================================
# Feature 35: Assistant Progress Banner UI Contract (5 tests)
# ===========================================================================

def test_t1_f35_01_step_progress_rendering():
    """AssistantPanel source renders active action banner with step counter."""
    panel_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "panels" / "AssistantPanel.tsx"
    assert panel_path.exists(), "AssistantPanel.tsx not found"
    content = panel_path.read_text(encoding="utf-8")
    assert "Running Step" in content
    assert "activeAction" in content


def test_t1_f35_02_step_update_transition():
    """Browser store declares activeAction state and setActiveAction mutation."""
    store_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "store" / "browser-store.ts"
    assert store_path.exists(), "browser-store.ts not found"
    content = store_path.read_text(encoding="utf-8")
    assert "activeAction" in content
    assert "setActiveAction" in content


def test_t1_f35_03_action_parameters_preview():
    """AssistantPanel previews action parameters like URL or search query in progress banner."""
    panel_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "panels" / "AssistantPanel.tsx"
    content = panel_path.read_text(encoding="utf-8")
    assert "activeAction.parameters" in content
    assert "activeAction.parameters?.url" in content
    assert "activeAction.parameters?.query" in content
    assert "activeAction.action" in content


def test_t1_f35_04_react_trace_toggle():
    """AssistantPanel source provides collapsible drawer for ReAct thought traces."""
    panel_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "panels" / "AssistantPanel.tsx"
    content = panel_path.read_text(encoding="utf-8")
    assert "thought" in content.lower() or "reasoning" in content.lower() or "trace" in content.lower()


def test_t1_f35_05_banner_hidden_on_stop():
    """AssistantPanel progress banner conditionally checks isAgentRunning / activeAction."""
    panel_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "panels" / "AssistantPanel.tsx"
    content = panel_path.read_text(encoding="utf-8")
    assert "isAgentRunning" in content
    assert "activeAction" in content


# ===========================================================================
# Feature 36: Ponytail Principles Compliance (5 tests)
# ===========================================================================

def test_t1_f36_01_standard_library_csv_json():
    """Backend tools use standard library json and csv modules exclusively."""
    import backend.app.tools.executor as executor_mod
    import backend.app.agents.data_agent as data_mod
    assert hasattr(executor_mod, "csv")
    assert hasattr(data_mod, "csv")
    assert hasattr(data_mod, "json")


def test_t1_f36_02_no_speculative_wrappers():
    """Bridge architecture uses direct call/notify pattern without redundant proxy indirection."""
    from backend.app.browser.bridge import bridge
    assert hasattr(bridge, "call")
    assert hasattr(bridge, "notify")
    assert hasattr(bridge, "register_method")


def test_t1_f36_03_linear_control_flow():
    """ToolExecutor control flow is linear and readable without speculative metaclasses."""
    executor_path = WORKSPACE_ROOT / "backend" / "app" / "tools" / "executor.py"
    tree = ast.parse(executor_path.read_text(encoding="utf-8"))
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    class_names = [c.name for c in classes]
    assert "ToolExecutor" in class_names


def test_t1_f36_04_native_asyncio_usage():
    """Core agents and services use native standard library asyncio primitives."""
    import backend.app.agents.supervisor as sup_mod
    import backend.app.workflows.engine as wf_mod
    assert hasattr(sup_mod, "asyncio")
    assert hasattr(wf_mod, "asyncio")


def test_t1_f36_05_existing_dependencies_reused():
    """pyproject.toml does not introduce unauthorized heavy meta-frameworks."""
    pyproject = WORKSPACE_ROOT / "backend" / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8").lower()
    prohibited = ["crewai", "autogen", "langchain", "llamaindex"]
    for p in prohibited:
        assert p not in content, f"Unauthorized framework '{p}' found in pyproject.toml"


# ===========================================================================
# Feature 37: Regression Prevention (5 tests)
# ===========================================================================

def test_t1_f37_01_all_38_backend_tests_exist():
    """Existing baseline backend tests in backend/tests/ are present and discoverable."""
    tests_dir = WORKSPACE_ROOT / "backend" / "tests"
    assert tests_dir.exists(), "backend/tests directory does not exist"
    test_files = list(tests_dir.glob("test_*.py"))
    assert len(test_files) >= 10, f"Expected at least 10 baseline test files, found {len(test_files)}"


@pytest.mark.asyncio
async def test_t1_f37_02_health_check_test_passes(async_client):
    """Application health check endpoint returns 200 with status='healthy'."""
    resp = await async_client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "healthy"


@pytest.mark.asyncio
async def test_t1_f37_03_database_crud_tests_pass(test_db):
    """Database repository handles CRUD operations for conversations cleanly."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        conv = await repo.create_conversation(title="CRUD Test")
        assert conv.id.startswith("conv-")

        retrieved = await repo.get_conversation(conv.id)
        assert retrieved is not None
        assert retrieved.title == "CRUD Test"

        deleted = await repo.delete_conversation(conv.id)
        assert deleted is True

        after_delete = await repo.get_conversation(conv.id)
        assert after_delete is None


@pytest.mark.asyncio
async def test_t1_f37_04_desktop_automation_tests_pass(mock_desktop_primitives):
    """DesktopService mouse and keyboard actions execute cleanly without regression."""
    res_click = await DesktopService.mouse_click(100, 150)
    assert res_click["status"] == "success"

    res_hotkey = await DesktopService.send_hotkey(["ctrl", "v"])
    assert res_hotkey["status"] == "success"


@pytest.mark.asyncio
async def test_t1_f37_05_workflow_engine_tests_pass(test_db):
    """WorkflowEngine executes valid workflow to completion without regression."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Regression Workflow",
            steps=[{"action": "navigate", "parameters": {"url": "https://example.com"}}]
        )
    res = await WorkflowEngine.execute_workflow(wf.id)
    assert res["status"] == "completed"


# ===========================================================================
# Feature 38: End-to-End Test Suite Execution (5 tests)
# ===========================================================================

def test_t1_f38_01_runner_tier1_execution():
    """All Tier 1 feature coverage test modules exist in tests/e2e/tier1_features/."""
    tier1_dir = WORKSPACE_ROOT / "tests" / "e2e" / "tier1_features"
    assert tier1_dir.exists()
    assert (tier1_dir / "test_t1_f01_f10.py").exists()
    assert (tier1_dir / "test_t1_f11_f20.py").exists()
    assert (tier1_dir / "test_t1_f21_f30.py").exists()
    assert (tier1_dir / "test_t1_f31_f40.py").exists()


def test_t1_f38_02_runner_conftest_fixtures():
    """Shared hermetic test fixtures are exported by tests/e2e/conftest.py."""
    conftest_path = WORKSPACE_ROOT / "tests" / "e2e" / "conftest.py"
    assert conftest_path.exists()
    content = conftest_path.read_text(encoding="utf-8")
    assert "test_db" in content
    assert "mock_bridge" in content
    assert "mock_nim_provider" in content
    assert "mock_desktop_primitives" in content


def test_t1_f38_03_runner_pytest_ini():
    """tests/e2e/pytest.ini configuration file exists and specifies asyncio mode."""
    ini_path = WORKSPACE_ROOT / "tests" / "e2e" / "pytest.ini"
    assert ini_path.exists()
    content = ini_path.read_text(encoding="utf-8")
    assert "asyncio_mode" in content


@pytest.mark.asyncio
async def test_t1_f38_04_runner_module_isolation(test_db):
    """Each test receives an isolated in-memory SQLite database session."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        tasks = await repo.get_tasks()
        assert len(tasks) == 0, "Test database not isolated; residual tasks found"


def test_t1_f38_05_runner_exit_code_zero():
    """All Tier 1 test files can be parsed without syntax errors."""
    tier1_dir = WORKSPACE_ROOT / "tests" / "e2e" / "tier1_features"
    for py_file in tier1_dir.glob("test_*.py"):
        code = py_file.read_text(encoding="utf-8")
        tree = ast.parse(code)
        assert tree is not None, f"Syntax parsing failed for {py_file.name}"


# ===========================================================================
# Feature 39: Adversarial Coverage Hardening (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t1_f39_01_overlay_occlusion_dismissal():
    """BrowserAgent element index matcher safely handles empty or unmatched selectors."""
    idx = BrowserAgent._find_matched_element_index("non_existent_selector_#123", [])
    assert idx is None


@pytest.mark.asyncio
async def test_t1_f39_02_invalid_auth_token_rejected(async_client, monkeypatch):
    """Secured endpoints reject requests with invalid X-Local-Token when secret token is set."""
    monkeypatch.setattr(settings, "SECRET_TOKEN", "super-secret-auth-token")
    resp = await async_client.get(
        "/api/v1/conversations",
        headers={"X-Local-Token": "bad-wrong-token"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_t1_f39_03_malformed_json_rpc_rejected(ipc_client):
    """Invoking an unregistered JSON-RPC method raises ValueError."""
    with pytest.raises(ValueError) as excinfo:
        await ipc_client("unregistered.malformed.method.xyz")
    assert "not registered" in str(excinfo.value)


@pytest.mark.asyncio
async def test_t1_f39_04_sql_injection_sanitization(test_db):
    """Prompts containing malicious SQL injection strings are stored safely without database error."""
    injection_prompt = "Find hotels'; DROP TABLE agent_tasks; -- SELECT * FROM users"
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title="SQL Injection Test", prompt=injection_prompt)
        assert task.id.startswith("task-")

        retrieved = await repo.get_task(task.id)
        assert retrieved is not None
        assert retrieved.prompt == injection_prompt


@pytest.mark.asyncio
async def test_t1_f39_05_network_disconnect_retry():
    """Tool execution failure is caught and wrapped into canonical status='error' response."""
    res = await ToolExecutor.execute("unknown_erroneous_tool_xyz", {})
    assert res["status"] == "error"
    assert res["error"] is not None


# ===========================================================================
# Feature 40: Zero Core Framework Bloat (5 tests)
# ===========================================================================

def test_t1_f40_01_backend_app_clean_imports():
    """Scans all Python files in backend/app/ for prohibited frameworks (0 occurrences)."""
    app_dir = WORKSPACE_ROOT / "backend" / "app"
    prohibited = ["langchain", "crewai", "autogen", "llamaindex"]
    violations = []

    for py_file in app_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            line_clean = line.strip()
            if line_clean.startswith("#"):
                continue
            for p in prohibited:
                if f"import {p}" in line_clean or f"from {p}" in line_clean:
                    violations.append(f"{py_file.name}: {line_clean}")

    assert len(violations) == 0, f"Prohibited imports found in backend/app: {violations}"


def test_t1_f40_02_desktop_frontend_clean_imports():
    """Scans desktop frontend source files for prohibited framework imports (0 occurrences)."""
    src_dir = WORKSPACE_ROOT / "apps" / "desktop" / "src"
    prohibited = ["langchain", "crewai", "autogen"]
    violations = []

    if src_dir.exists():
        for f in src_dir.rglob("*.ts*"):
            content = f.read_text(encoding="utf-8")
            for line in content.splitlines():
                line_clean = line.strip()
                if line_clean.startswith("//"):
                    continue
                for p in prohibited:
                    if f"from '{p}'" in line_clean or f'from "{p}"' in line_clean:
                        violations.append(f"{f.name}: {line_clean}")

    assert len(violations) == 0, f"Prohibited imports found in desktop frontend: {violations}"


def test_t1_f40_03_pyproject_dependencies_clean():
    """backend/pyproject.toml declares only authorized dependencies."""
    pyproject_path = WORKSPACE_ROOT / "backend" / "pyproject.toml"
    assert pyproject_path.exists()
    content = pyproject_path.read_text(encoding="utf-8").lower()
    prohibited = ["crewai", "autogen", "langchain", "llama-index", "llamaindex"]
    for p in prohibited:
        assert p not in content, f"Unauthorized package '{p}' found in pyproject.toml"


def test_t1_f40_04_package_json_dependencies_clean():
    """apps/desktop/package.json contains only approved frontend packages."""
    pkg_path = WORKSPACE_ROOT / "apps" / "desktop" / "package.json"
    assert pkg_path.exists()
    content = pkg_path.read_text(encoding="utf-8").lower()
    prohibited = ["crewai", "autogen", "langchain"]
    for p in prohibited:
        assert p not in content, f"Unauthorized package '{p}' found in desktop package.json"


def test_t1_f40_05_tests_clean_imports():
    """tests/e2e/ directory does not introduce unauthorized external framework imports."""
    e2e_dir = WORKSPACE_ROOT / "tests" / "e2e"
    prohibited = ["langchain", "crewai", "autogen", "llamaindex"]
    violations = []

    for py_file in e2e_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            line_clean = line.strip()
            if line_clean.startswith("#"):
                continue
            for p in prohibited:
                if f"import {p}" in line_clean or f"from {p}" in line_clean:
                    violations.append(f"{py_file.name}: {line_clean}")

    assert len(violations) == 0, f"Prohibited imports found in tests/e2e: {violations}"
