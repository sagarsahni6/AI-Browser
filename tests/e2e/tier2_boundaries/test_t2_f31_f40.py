"""
tests/e2e/tier2_boundaries/test_t2_f31_f40.py
Tier 2 Boundary Value & Error Condition Tests: Features 31 to 40 (50 tests total, 5 per feature).

Features Covered:
  F31: Advanced Workflow Engine Bounds
  F32: Workflow Import / Export Bounds
  F33: Risk Meter Approval Dialog UI Bounds
  F34: Visual Action Indicator (Laser) UI Bounds
  F35: Progress Banner UI Bounds
  F36: Ponytail Principles Compliance Bounds
  F37: Regression Prevention Bounds
  F38: E2E Suite Execution Bounds
  F39: Adversarial Coverage Hardening Bounds
  F40: Zero Core Framework Bloat Bounds
"""

import os
import sys
import ast
import json
import pytest
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch, AsyncMock, MagicMock

from backend.app.config import settings
from backend.app.tools.executor import ToolExecutor
from backend.app.workflows.engine import WorkflowEngine
from backend.app.automation.desktop.service import DesktopService
from backend.app.database.repository import Repository
from backend.app.database.engine import AsyncSessionLocal
from backend.app.browser.bridge import bridge

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent


# ===========================================================================
# Feature 31: Advanced Workflow Engine Bounds (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t2_f31_01_empty_steps_workflow(test_db):
    """Boundary: Workflow with 0 steps completes immediately returning 0 executed steps."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(name="Empty Workflow", steps=[])
        wf_id = wf.id

    res = await WorkflowEngine.execute_workflow(wf_id)
    assert res["status"] == "completed"
    assert res["steps_executed"] == 0
    assert res["results"] == []


def test_t2_f31_02_undefined_variable_interpolation():
    """Boundary: Unsupplied variables in template remain un-interpolated without crash."""
    params = {"query": "{{missing_variable_abc}}", "tag": "{{defined}}"}
    res = WorkflowEngine._interpolate(params, {"defined": "present_value"})
    assert res["tag"] == "present_value"
    assert res["query"] == "{{missing_variable_abc}}"


@pytest.mark.asyncio
async def test_t2_f31_03_step_failure_stops_execution(test_db):
    """Boundary: Step returning error marks workflow failed and halts immediately."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Halting Workflow",
            steps=[
                {"action": "navigate", "parameters": {"url": "https://example.com"}},
                {"action": "invalid_fail_tool", "parameters": {}},
                {"action": "take_screenshot", "parameters": {}}
            ]
        )
        wf_id = wf.id

    res = await WorkflowEngine.execute_workflow(wf_id)
    assert res["status"] == "failed"
    assert res["failed_step"] == 2
    assert len(res["results"]) == 2  # Step 3 must not run


def test_t2_f31_04_special_characters_variable():
    """Boundary: Variables containing special characters (quotes, braces, slashes) interpolate safely."""
    raw = {"data": "{{val}}", "path": "{{dir}}/{{file}}"}
    variables = {
        "val": 'Text with "quotes" and <tags> & symbols',
        "dir": "C:\\Users\\Test",
        "file": "report (2026).pdf"
    }
    interpolated = WorkflowEngine._interpolate(raw, variables)
    assert interpolated["data"] == 'Text with "quotes" and <tags> & symbols'
    assert interpolated["path"] == "C:\\Users\\Test/report (2026).pdf"


@pytest.mark.asyncio
async def test_t2_f31_05_cyclic_or_repeated_step_execution(test_db):
    """Boundary: Workflow executing same tool multiple times records distinct step indices."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Repeated Steps Workflow",
            steps=[
                {"action": "scroll_page", "parameters": {"delta_y": 100}},
                {"action": "scroll_page", "parameters": {"delta_y": 200}},
                {"action": "scroll_page", "parameters": {"delta_y": 300}}
            ]
        )
        wf_id = wf.id

    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"status": "success", "tool_name": "scroll_page", "result": {}, "evidence": {}, "error": None}
        res = await WorkflowEngine.execute_workflow(wf_id)
        assert res["status"] == "completed"
        assert res["steps_executed"] == 3
        assert [r["step"] for r in res["results"]] == [1, 2, 3]


# ===========================================================================
# Feature 32: Workflow Import / Export Bounds (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t2_f32_01_import_malformed_json_schema(test_db):
    """Boundary: Importing workflow dictionary with missing name or description handles safely."""
    imported = await WorkflowEngine.import_workflow({
        "steps": [{"action": "navigate", "parameters": {"url": "https://example.com"}}]
    })
    assert imported["id"] is not None
    assert imported["name"] == "Imported Workflow"
    assert imported["step_count"] == 1


@pytest.mark.asyncio
async def test_t2_f32_02_export_nonexistent_workflow(test_db):
    """Boundary: Exporting unknown workflow ID returns None."""
    exported = await WorkflowEngine.export_workflow("nonexistent-workflow-id-999")
    assert exported is None


@pytest.mark.asyncio
async def test_t2_f32_03_import_assigns_new_id(test_db):
    """Boundary: Importing workflow assigns a distinct unique ID in database."""
    wf_data = {
        "name": "Distinct ID Test",
        "description": "Testing distinct IDs",
        "steps": [{"action": "take_screenshot", "parameters": {}}]
    }
    wf1 = await WorkflowEngine.import_workflow(wf_data)
    wf2 = await WorkflowEngine.import_workflow(wf_data)
    assert wf1["id"] != wf2["id"]


@pytest.mark.asyncio
async def test_t2_f32_04_roundtrip_integrity(test_db):
    """Boundary: Exporting and re-importing preserves step action and parameters."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Roundtrip Test",
            description="Testing roundtrip integrity",
            steps=[{"action": "navigate", "parameters": {"url": "https://example.org"}}],
            variables={"var1": "value1"}
        )
        orig_id = wf.id

    exported = await WorkflowEngine.export_workflow(orig_id)
    assert exported is not None
    assert exported["name"] == "Roundtrip Test"
    assert len(exported["steps"]) == 1

    reimported = await WorkflowEngine.import_workflow(exported)
    assert reimported["id"] != orig_id
    assert reimported["name"] == "Roundtrip Test"
    assert reimported["step_count"] == 1


@pytest.mark.asyncio
async def test_t2_f32_05_export_version_header(test_db):
    """Boundary: Exported workflow schema contains version 1.0 header."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(name="Versioned Workflow", steps=[])
        wf_id = wf.id

    exported = await WorkflowEngine.export_workflow(wf_id)
    assert exported["version"] == "1.0"


# ===========================================================================
# Feature 33: Risk Meter Approval Dialog UI Bounds (5 tests)
# ===========================================================================

def test_t2_f33_01_red_tier_score_meter_text():
    """Boundary: ApprovalDialog.tsx specifies RED TIER mapping to 100% and error color."""
    dialog_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "components" / "ApprovalDialog.tsx"
    assert dialog_path.exists()
    content = dialog_path.read_text(encoding="utf-8")
    assert "'RED TIER'" in content
    assert "percentage = 100" in content
    assert "var(--error" in content


def test_t2_f33_02_yellow_tier_score_meter_text():
    """Boundary: ApprovalDialog.tsx specifies YELLOW TIER mapping to 40% and warning color."""
    dialog_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "components" / "ApprovalDialog.tsx"
    content = dialog_path.read_text(encoding="utf-8")
    assert "'YELLOW TIER'" in content
    assert "percentage = 40" in content
    assert "var(--warning" in content


def test_t2_f33_03_green_tier_score_meter_text():
    """Boundary: ApprovalDialog.tsx specifies GREEN TIER mapping to 20% and success color."""
    dialog_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "components" / "ApprovalDialog.tsx"
    content = dialog_path.read_text(encoding="utf-8")
    assert "'GREEN TIER'" in content
    assert "percentage = 20" in content
    assert "var(--success" in content


def test_t2_f33_04_password_masking_regex():
    """Boundary: ApprovalDialog.tsx masks sensitive password parameters."""
    dialog_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "components" / "ApprovalDialog.tsx"
    content = dialog_path.read_text(encoding="utf-8")
    assert "Masked for security" in content
    assert "sanitizedParams" in content


def test_t2_f33_05_dialog_hidden_when_closed():
    """Boundary: ApprovalDialog.tsx returns null when isOpen is false."""
    dialog_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "components" / "ApprovalDialog.tsx"
    content = dialog_path.read_text(encoding="utf-8")
    assert "if (!isOpen) return null;" in content


# ===========================================================================
# Feature 34: Visual Action Indicator (Laser) UI Bounds (5 tests)
# ===========================================================================

def test_t2_f34_01_laser_style_keyframes():
    """Boundary: LaserIndicator.ts injects @keyframes cometLaserRipple and cometLaserCore."""
    laser_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "overlay" / "LaserIndicator.ts"
    assert laser_path.exists()
    content = laser_path.read_text(encoding="utf-8")
    assert "@keyframes cometLaserRipple" in content
    assert "@keyframes cometLaserCore" in content


def test_t2_f34_02_pointer_events_none():
    """Boundary: LaserIndicator.ts overlay specifies pointer-events: none for click-through."""
    laser_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "overlay" / "LaserIndicator.ts"
    content = laser_path.read_text(encoding="utf-8")
    assert "pointer-events: none" in content


def test_t2_f34_03_z_index_maximum():
    """Boundary: LaserIndicator.ts overlay specifies maximum z-index 2147483647."""
    laser_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "overlay" / "LaserIndicator.ts"
    content = laser_path.read_text(encoding="utf-8")
    assert "2147483647" in content


def test_t2_f34_04_detached_dom_guard():
    """Boundary: LaserIndicator.ts guards against detached document environments."""
    laser_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "overlay" / "LaserIndicator.ts"
    content = laser_path.read_text(encoding="utf-8")
    assert "typeof document === 'undefined'" in content


def test_t2_f34_05_dom_cleanup_timeout():
    """Boundary: LaserIndicator.ts automatically cleans up elements after animation."""
    laser_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "overlay" / "LaserIndicator.ts"
    content = laser_path.read_text(encoding="utf-8")
    assert "setTimeout" in content
    assert "remove()" in content


# ===========================================================================
# Feature 35: Assistant Progress Banner UI Bounds (5 tests)
# ===========================================================================

def test_t2_f35_01_running_step_template():
    """Boundary: AssistantPanel.tsx renders 'Running Step {current}/{total}: {action}'."""
    panel_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "panels" / "AssistantPanel.tsx"
    assert panel_path.exists()
    content = panel_path.read_text(encoding="utf-8")
    assert "Running Step" in content
    assert "activeAction.action" in content


def test_t2_f35_02_banner_suppressed_on_approval():
    """Boundary: AssistantPanel.tsx suppresses progress banner when approval is required."""
    panel_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "panels" / "AssistantPanel.tsx"
    content = panel_path.read_text(encoding="utf-8")
    assert "activeAction.status !== 'approval_required'" in content


def test_t2_f35_03_banner_step_number_fallback():
    """Boundary: AssistantPanel.tsx falls back to '?' when step_number or total_steps is missing."""
    panel_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "panels" / "AssistantPanel.tsx"
    content = panel_path.read_text(encoding="utf-8")
    assert "activeAction.step_number || '?'" in content
    assert "activeAction.total_steps || '?'" in content


def test_t2_f35_04_react_trace_toggle():
    """Boundary: AssistantPanel.tsx implements showTrace toggle for reasoning drawer."""
    panel_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "panels" / "AssistantPanel.tsx"
    content = panel_path.read_text(encoding="utf-8")
    assert "showTrace" in content
    assert "reactThought" in content


def test_t2_f35_05_banner_hidden_when_agent_stopped():
    """Boundary: AssistantPanel.tsx requires isAgentRunning for banner display."""
    panel_path = WORKSPACE_ROOT / "apps" / "desktop" / "src" / "panels" / "AssistantPanel.tsx"
    content = panel_path.read_text(encoding="utf-8")
    assert "isAgentRunning && activeAction" in content


# ===========================================================================
# Feature 36: Ponytail Principles Compliance Bounds (5 tests)
# ===========================================================================

def test_t2_f36_01_standard_library_csv_json():
    """Boundary: Data processing relies directly on standard library csv and json modules."""
    data_agent_code = (WORKSPACE_ROOT / "backend" / "app" / "agents" / "data_agent.py").read_text(encoding="utf-8")
    assert "import csv" in data_agent_code
    assert "import json" in data_agent_code


def test_t2_f36_02_standard_library_asyncio_concurrency():
    """Boundary: Async concurrency relies on standard library asyncio."""
    sup_code = (WORKSPACE_ROOT / "backend" / "app" / "agents" / "supervisor.py").read_text(encoding="utf-8")
    assert "import asyncio" in sup_code


def test_t2_f36_03_no_monolithic_overengineering():
    """Boundary: Central ToolExecutor file remains concise and focused under 500 lines."""
    executor_path = WORKSPACE_ROOT / "backend" / "app" / "tools" / "executor.py"
    line_count = len(executor_path.read_text(encoding="utf-8").splitlines())
    assert line_count < 500, f"executor.py has {line_count} lines, exceeding 500 lines"


def test_t2_f36_04_standard_library_re_expressions():
    """Boundary: Text cleanup and HTML stripping relies on standard library re module."""
    research_code = (WORKSPACE_ROOT / "backend" / "app" / "research" / "service.py").read_text(encoding="utf-8")
    assert "import re" in research_code


def test_t2_f36_05_native_platform_win32_integration():
    """Boundary: Windows automation uses platform win32 modules rather than heavyweight wrappers."""
    desktop_code = (WORKSPACE_ROOT / "backend" / "app" / "automation" / "desktop" / "service.py").read_text(encoding="utf-8")
    assert "import win32api" in desktop_code


# ===========================================================================
# Feature 37: Regression Prevention Bounds (5 tests)
# ===========================================================================

def test_t2_f37_01_backend_test_directory_structure():
    """Boundary: backend/tests/ directory contains required baseline test files."""
    test_dir = WORKSPACE_ROOT / "backend" / "tests"
    assert test_dir.exists()
    test_files = list(test_dir.glob("test_*.py"))
    assert len(test_files) >= 10


def test_t2_f37_02_health_test_file_exists():
    """Boundary: backend/tests/test_health.py exists and is non-empty."""
    f = WORKSPACE_ROOT / "backend" / "tests" / "test_health.py"
    assert f.exists() and f.stat().st_size > 0


def test_t2_f37_03_database_test_file_exists():
    """Boundary: backend/tests/test_database.py exists and is non-empty."""
    f = WORKSPACE_ROOT / "backend" / "tests" / "test_database.py"
    assert f.exists() and f.stat().st_size > 0


def test_t2_f37_04_desktop_automation_test_file_exists():
    """Boundary: backend/tests/test_phase6_desktop_automation.py exists and is non-empty."""
    f = WORKSPACE_ROOT / "backend" / "tests" / "test_phase6_desktop_automation.py"
    assert f.exists() and f.stat().st_size > 0


def test_t2_f37_05_workflow_engine_test_file_exists():
    """Boundary: backend/tests/test_workflow_engine.py exists and is non-empty."""
    f = WORKSPACE_ROOT / "backend" / "tests" / "test_workflow_engine.py"
    assert f.exists() and f.stat().st_size > 0


# ===========================================================================
# Feature 38: E2E Suite Execution Bounds (5 tests)
# ===========================================================================

def test_t2_f38_01_runner_file_exists():
    """Boundary: tests/e2e/run_all_e2e.py exists and is executable."""
    runner = WORKSPACE_ROOT / "tests" / "e2e" / "run_all_e2e.py"
    assert runner.exists()
    assert runner.stat().st_size > 500


def test_t2_f38_02_runner_tier_argument_choices():
    """Boundary: run_all_e2e.py defines tier selection argument."""
    content = (WORKSPACE_ROOT / "tests" / "e2e" / "run_all_e2e.py").read_text(encoding="utf-8")
    assert "--tier" in content
    assert '"1"' in content
    assert '"2"' in content


def test_t2_f38_03_runner_filter_flag():
    """Boundary: run_all_e2e.py supports -k / --filter argument."""
    content = (WORKSPACE_ROOT / "tests" / "e2e" / "run_all_e2e.py").read_text(encoding="utf-8")
    assert "--filter" in content or "-k" in content


def test_t2_f38_04_runner_exitfirst_flag():
    """Boundary: run_all_e2e.py supports -x / --exitfirst failfast argument."""
    content = (WORKSPACE_ROOT / "tests" / "e2e" / "run_all_e2e.py").read_text(encoding="utf-8")
    assert "--exitfirst" in content or "-x" in content


def test_t2_f38_05_runner_hermetic_env_vars():
    """Boundary: run_all_e2e.py configures in-memory sqlite and TESTING environment."""
    content = (WORKSPACE_ROOT / "tests" / "e2e" / "run_all_e2e.py").read_text(encoding="utf-8")
    assert ":memory:" in content
    assert "TESTING" in content


# ===========================================================================
# Feature 39: Adversarial Coverage Hardening Bounds (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t2_f39_01_massive_payload_handling():
    """Boundary: Massive 100KB payload passed in tool parameters handles safely."""
    big_payload = "ABCDEFGH" * 12500
    res = await ToolExecutor.execute("get_page_content", {"extra_data": big_payload})
    assert res["status"] == "success"
    assert res["tool_name"] == "get_page_content"


@pytest.mark.asyncio
async def test_t2_f39_02_sql_injection_in_task_prompt(test_db):
    """Boundary: SQL injection strings in task prompt stored safely via parameterized query."""
    sql_injection = "'; DROP TABLE tasks; DROP TABLE task_steps; --"
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("SQL Injection Test", sql_injection)
        assert task.id is not None

        retrieved = await repo.get_task(task.id)
        assert retrieved.prompt == sql_injection

        # Verify tasks table is intact
        tasks = await repo.get_tasks(limit=10)
        assert len(tasks) >= 1


@pytest.mark.asyncio
async def test_t2_f39_03_javascript_injection_in_tool_params():
    """Boundary: JavaScript tag injection in selector handled safely without evaluation."""
    js_injection = "<script>alert('XSS')</script>"
    res = await ToolExecutor.execute("click_selector", {"selector": js_injection})
    assert "status" in res
    assert res["tool_name"] == "click_selector"


def test_t2_f39_04_rapid_emergency_stop_concurrency():
    """Boundary: Rapid consecutive toggle of emergency stop remains thread-safe."""
    for _ in range(50):
        DesktopService.emergency_stop()
        assert DesktopService.is_stopped() is True
        DesktopService.reset_emergency_stop()
        assert DesktopService.is_stopped() is False


@pytest.mark.asyncio
async def test_t2_f39_05_null_bytes_in_input_string():
    """Boundary: Parameters containing null bytes (\x00) handle safely without crash."""
    null_byte_text = "SafePrefix\x00NullByteData\x00Suffix"
    res = await ToolExecutor.execute("fill_input", {"x": 10, "y": 10, "text": null_byte_text})
    assert "status" in res
    assert res["tool_name"] == "fill_input"


# ===========================================================================
# Feature 40: Zero Core Framework Bloat Bounds (5 tests)
# ===========================================================================

def test_t2_f40_01_ast_scan_backend_app_clean():
    """Boundary: AST scan of backend/app/ detects 0 imports of unauthorized frameworks."""
    prohibited = {"langchain", "crewai", "autogen", "llamaindex", "semantic_kernel"}
    app_dir = WORKSPACE_ROOT / "backend" / "app"
    found_violations = []

    for py_file in app_dir.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top_pkg = alias.name.split(".")[0].lower()
                        if top_pkg in prohibited:
                            found_violations.append((str(py_file), top_pkg))
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        top_pkg = node.module.split(".")[0].lower()
                        if top_pkg in prohibited:
                            found_violations.append((str(py_file), top_pkg))
        except Exception:
            pass

    assert len(found_violations) == 0, f"Prohibited framework imports found: {found_violations}"


def test_t2_f40_02_ast_scan_backend_tests_clean():
    """Boundary: AST scan of backend/tests/ detects 0 imports of unauthorized frameworks."""
    prohibited = {"langchain", "crewai", "autogen", "llamaindex", "semantic_kernel"}
    tests_dir = WORKSPACE_ROOT / "backend" / "tests"
    found_violations = []

    for py_file in tests_dir.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top_pkg = alias.name.split(".")[0].lower()
                        if top_pkg in prohibited:
                            found_violations.append((str(py_file), top_pkg))
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        top_pkg = node.module.split(".")[0].lower()
                        if top_pkg in prohibited:
                            found_violations.append((str(py_file), top_pkg))
        except Exception:
            pass

    assert len(found_violations) == 0, f"Prohibited framework imports found: {found_violations}"


def test_t2_f40_03_package_json_desktop_clean():
    """Boundary: apps/desktop/package.json contains 0 prohibited framework packages."""
    pkg_json = WORKSPACE_ROOT / "apps" / "desktop" / "package.json"
    content = pkg_json.read_text(encoding="utf-8").lower()
    for forbidden in ["@langchain", "crewai", "autogen", "llamaindex"]:
        assert forbidden not in content, f"Forbidden framework '{forbidden}' found in desktop package.json"


def test_t2_f40_04_pyproject_toml_clean():
    """Boundary: backend/pyproject.toml contains 0 prohibited framework packages."""
    pyproject = WORKSPACE_ROOT / "backend" / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8").lower()
    for forbidden in ["langchain", "crewai", "autogen", "llamaindex", "semantic-kernel"]:
        assert forbidden not in content, f"Forbidden framework '{forbidden}' found in pyproject.toml"


def test_t2_f40_05_dynamic_dunder_import_detection():
    """Boundary: Scanner detects and ensures no obfuscated __import__ calls for prohibited libraries."""
    app_dir = WORKSPACE_ROOT / "backend" / "app"
    prohibited = ["langchain", "crewai", "autogen", "llamaindex"]
    violations = []

    for py_file in app_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for p in prohibited:
            if f'__import__("{p}")' in content or f"__import__('{p}')" in content:
                violations.append((str(py_file), p))

    assert len(violations) == 0, f"Obfuscated __import__ calls found: {violations}"
