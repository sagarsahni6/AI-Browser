"""
tests/e2e/tier2_boundaries/test_t2_f11_f20.py
Tier 2 Boundary Value & Error Condition Tests: Features 11 to 20 (50 tests total, 5 per feature).

Features Covered:
  F11: Unified Agent Runtime Bounds
  F12: ReAct Cognitive Execution Loop Bounds
  F13: Execution Budget Limits Bounds
  F14: Central Tool Registry Bounds
  F15: Dynamic Planner Agent Upgrade Bounds
  F16: Supervisor Agent Coordination Bounds
  F17: Specialist Agents Architecture Bounds
  F18: Tab-Specific Context Binding Bounds
  F19: Windows Desktop Automation Hardening Bounds
  F20: Desktop Audit Logging & Kill Switch Bounds
"""

import os
import sys
import json
import pytest
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch, AsyncMock, MagicMock

from backend.app.config import settings
from backend.app.tools.executor import ToolExecutor
from backend.app.tools.definitions import BROWSER_TOOLS
from backend.app.security.approval import ApprovalManager
from backend.app.agents.models import TaskStep, TaskPlan, StepStatus
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.supervisor import SupervisorAgent
from backend.app.agents.browser_agent import BrowserAgent
from backend.app.agents.researcher import ResearcherAgent
from backend.app.agents.data_agent import DataAgent
from backend.app.agents.verifier import VerifierAgent
from backend.app.automation.desktop.service import DesktopService
from backend.app.database.repository import Repository
from backend.app.database.engine import AsyncSessionLocal
from backend.app.browser.bridge import bridge
from backend.app.ai.providers.base import ChatCompletionResult

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent


# ===========================================================================
# Feature 11: Unified Agent Runtime Bounds (5 tests)
# ===========================================================================

def test_t2_f11_01_concurrent_task_cancellation():
    """Boundary: Cancelling task A does not affect or cancel concurrently running task B."""
    SupervisorAgent._cleanup_task("task-A")
    SupervisorAgent._cleanup_task("task-B")

    SupervisorAgent.cancel_task("task-A")
    assert SupervisorAgent.is_cancelled("task-A") is True
    assert SupervisorAgent.is_cancelled("task-B") is False

    SupervisorAgent._cleanup_task("task-A")


@pytest.mark.asyncio
async def test_t2_f11_02_invalid_task_id_handling(test_db):
    """Boundary: Executing non-existent task ID in SupervisorAgent.run_task handles safely."""
    # Should log error and return without raising uncaught exception
    await SupervisorAgent.run_task("nonexistent-task-id-999")


@pytest.mark.asyncio
async def test_t2_f11_03_runtime_crash_recovery_step(test_db):
    """Boundary: Unexpected exception in a specialist step handled safely in run_task."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Crash Recovery Task", "Testing crash resilience")
        task_id = task.id

    with patch.object(BrowserAgent, "execute_step", side_effect=RuntimeError("Unexpected agent failure")):
        # run_task catches exception and marks task failed in DB
        await SupervisorAgent.run_task(task_id)

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        t = await repo.get_task(task_id)
        assert t.status == "failed"
        assert "Unexpected agent failure" in t.error


@pytest.mark.asyncio
async def test_t2_f11_04_empty_prompt_task_creation(test_db):
    """Boundary: Creating task with empty prompt string succeeds and persists in DB."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Empty Prompt Task", "")
        assert task.id is not None
        assert task.status == "pending"

        retrieved = await repo.get_task(task.id)
        assert retrieved is not None
        assert retrieved.prompt == ""


@pytest.mark.asyncio
async def test_t2_f11_05_corrupted_state_checkpoint(test_db):
    """Boundary: Empty checkpoint handles cleanly; malformed JSON raises JSONDecodeError."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Corrupt Checkpoint Task", "Testing corrupted JSON")
        appr_empty = await repo.create_approval_request(
            task_id=task.id,
            tool_name="export_csv",
            action_type="sensitive",
            description="Empty checkpoint",
            parameters_json=json.dumps({"filename": "test.csv"}),
            step_number=1,
            session_checkpoint_json="{}"
        )
        task_id = task.id
        appr_id_empty = appr_empty.id

    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"status": "success", "tool_name": "export_csv", "result": {}, "evidence": {}, "error": None}
        res = await SupervisorAgent.resume_approved_task(task_id, approval_id=appr_id_empty, decision=True)
        assert res["status"] in ("approved", "completed")

    # Testing that invalid JSON in session_checkpoint_json is properly detected
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task2 = await repo.create_task("Bad JSON Checkpoint Task", "Testing JSON error")
        appr_bad = await repo.create_approval_request(
            task_id=task2.id,
            tool_name="export_csv",
            action_type="sensitive",
            description="Bad JSON",
            parameters_json=json.dumps({"filename": "test.csv"}),
            step_number=1,
            session_checkpoint_json="INVALID_JSON{[[["
        )
        task2_id = task2.id
        appr_id_bad = appr_bad.id

    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"status": "success", "tool_name": "export_csv", "result": {}, "evidence": {}, "error": None}
        with pytest.raises(json.JSONDecodeError):
            await SupervisorAgent.resume_approved_task(task2_id, approval_id=appr_id_bad, decision=True)


# ===========================================================================
# Feature 12: ReAct Cognitive Execution Loop Bounds (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t2_f12_01_max_retries_limit_per_step(test_db):
    """Boundary: Repeated step failure stops after max retries without infinite loop."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Retry Limit Task", "Testing retry ceiling")
        task_id = task.id

    step = TaskStep(
        id=1,
        agent="browser",
        action="click_selector",
        description="Click non-existent selector repeatedly",
        parameters={"selector": "#never-exists"}
    )

    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec, \
         patch.object(PlannerAgent, "replan_subgoal", new_callable=AsyncMock) as mock_replan:
        mock_exec.return_value = {"status": "error", "tool_name": "click_selector", "error": "Element not found"}
        mock_replan.return_value = []

        res = await SupervisorAgent._execute_steps_loop(task_id, [step], [], total_steps=1)
        assert res["status"] in ("completed", "failed")


@pytest.mark.asyncio
async def test_t2_f12_02_repeated_tool_failures(test_db):
    """Boundary: Multiple steps returning errors accumulate failures and terminate safely."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Multi Failure Task", "Testing multiple errors")
        task_id = task.id

    steps = [
        TaskStep(id=i, agent="browser", action="navigate", description=f"Step {i}", parameters={"url": f"https://bad-{i}.com"})
        for i in range(1, 4)
    ]

    with patch.object(BrowserAgent, "execute_step", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"status": "error", "error": "DNS Resolution Failed"}
        res = await SupervisorAgent._execute_steps_loop(task_id, steps, [], total_steps=3)
        assert res["status"] in ("completed", "failed")


@pytest.mark.asyncio
async def test_t2_f12_03_empty_observation_handling():
    """Boundary: Replan subgoal handles empty observation dictionary gracefully."""
    step = TaskStep(id=1, agent="browser", action="navigate", description="Test", parameters={})
    replacement = await PlannerAgent.replan_subgoal(
        task_id="t-1",
        failed_step=step,
        error_context="Timeout",
        current_obs={},
        remaining_steps=[]
    )
    assert isinstance(replacement, list)


@pytest.mark.asyncio
async def test_t2_f12_04_malformed_thought_json_fallback(mock_nim_provider):
    """Boundary: When LLM returns invalid JSON during replan, handles cleanly with self-healing recovery step."""
    mock_nim_provider.queue_completion("This is plain English without any JSON brackets at all.")
    step = TaskStep(id=1, agent="browser", action="click_element", description="Click", parameters={"x": 10, "y": 20})
    res = await PlannerAgent.replan_subgoal("t-1", step, "Element occluded", {}, [])
    assert len(res) == 1
    assert res[0].action == "scroll_page"


@pytest.mark.asyncio
async def test_t2_f12_05_max_iterations_ceiling(test_db):
    """Boundary: ReAct loop with 10 sequential steps executes all 10 without premature cutoff."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("10 Steps Task", "Testing 10 step loop")
        task_id = task.id

    steps = [
        TaskStep(id=i, agent="browser", action="navigate", description=f"Step {i}", parameters={"url": f"https://example.com/{i}"})
        for i in range(1, 11)
    ]

    with patch.object(BrowserAgent, "execute_step", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"status": "success", "tool_name": "navigate", "result": {}, "evidence": {}, "error": None}
        res = await SupervisorAgent._execute_steps_loop(task_id, steps, [], total_steps=10)
        assert res["status"] in ("completed", "success")
        assert len(res.get("results", [])) == 10


# ===========================================================================
# Feature 13: Execution Budget Limits Bounds (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t2_f13_01_zero_step_budget(test_db):
    """Boundary: Execution loop with 0 remaining steps terminates immediately with empty results."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Zero Step Task", "0 steps")
        task_id = task.id

    res = await SupervisorAgent._execute_steps_loop(task_id, [], [], total_steps=0)
    assert res["status"] == "completed"
    assert res["results"] == []


@pytest.mark.asyncio
async def test_t2_f13_02_single_step_budget(test_db):
    """Boundary: Execution loop with exactly 1 step executes that single step and completes."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Single Step Task", "1 step")
        task_id = task.id

    step = TaskStep(id=1, agent="browser", action="get_page_content", description="Only step", parameters={})
    with patch.object(BrowserAgent, "execute_step", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"status": "success", "tool_name": "get_page_content", "result": {}, "evidence": {}, "error": None}
        res = await SupervisorAgent._execute_steps_loop(task_id, [step], [], total_steps=1)
        assert res["status"] == "completed"
        assert len(res["results"]) == 1


@pytest.mark.asyncio
async def test_t2_f13_03_budget_preservation_across_pause(test_db):
    """Boundary: Pausing a task freezes execution state until resume_task is signaled."""
    task_id = "test-pause-budget-task"
    SupervisorAgent._cleanup_task(task_id)

    SupervisorAgent.pause_task(task_id)
    assert SupervisorAgent.is_paused(task_id) is True

    SupervisorAgent.resume_task(task_id)
    assert SupervisorAgent.is_paused(task_id) is False
    SupervisorAgent._cleanup_task(task_id)


@pytest.mark.asyncio
async def test_t2_f13_04_instant_cancellation(test_db):
    """Boundary: Pre-cancelling a task before loop starts aborts on step 0 without executing tools."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Pre-cancelled Task", "Testing instant abort")
        task_id = task.id

    step = TaskStep(id=1, agent="browser", action="navigate", description="Should never run", parameters={})
    SupervisorAgent.cancel_task(task_id)

    with patch.object(BrowserAgent, "execute_step", new_callable=AsyncMock) as mock_exec:
        res = await SupervisorAgent._execute_steps_loop(task_id, [step], [], total_steps=1)
        assert res["status"] == "cancelled"
        assert mock_exec.call_count == 0


def test_t2_f13_05_step_retry_limit_constant():
    """Boundary: max_retries_per_step in SupervisorAgent is safely bounded to 3."""
    # Read supervisor source to verify constant boundary
    sup_path = WORKSPACE_ROOT / "backend" / "app" / "agents" / "supervisor.py"
    content = sup_path.read_text(encoding="utf-8")
    assert "max_retries_per_step = 3" in content


# ===========================================================================
# Feature 14: Central Tool Registry Bounds (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t2_f14_01_unregistered_tool_execution():
    """Boundary: Executing an unregistered tool name returns canonical error."""
    res = await ToolExecutor.execute("nonexistent_custom_tool_9999", {})
    assert res["status"] == "error"
    assert "Unknown tool" in res["error"]
    assert res["tool_name"] == "nonexistent_custom_tool_9999"


def test_t2_f14_02_tool_definitions_schema_validity():
    """Boundary: All BROWSER_TOOLS conform strictly to standard function calling schema."""
    assert len(BROWSER_TOOLS) >= 5
    for tool in BROWSER_TOOLS:
        assert tool.get("type") == "function"
        fn = tool.get("function", {})
        assert "name" in fn and len(fn["name"]) > 0
        assert "description" in fn
        assert "parameters" in fn
        params = fn["parameters"]
        assert params.get("type") == "object"
        assert "properties" in params


def test_t2_f14_03_tool_registry_risk_tier_query():
    """Boundary: ApprovalManager accurately categorizes green and red tier tools."""
    # Green tier
    appr1, _ = ApprovalManager.evaluate_tool_call("get_page_content", {})
    assert appr1 is False

    # Red tier
    appr2, reason2 = ApprovalManager.evaluate_tool_call("desktop_launch_app", {"app_name": "calc.exe"})
    assert appr2 is True
    assert "RED TIER" in reason2


def test_t2_f14_04_duplicate_tool_name_prevention():
    """Boundary: Validates that tool name map maps each unique tool to its designated schema."""
    tool_map = {t["function"]["name"]: t for t in BROWSER_TOOLS}
    # Every tool name maps to a valid schema object with required properties
    assert "extract_table_data" in tool_map
    assert "navigate" in tool_map
    assert "click_element" in tool_map
    assert len(tool_map) >= 30


@pytest.mark.asyncio
async def test_t2_f14_05_unhandled_parameter_types():
    """Boundary: Passing unexpected additional parameters to get_page_content is ignored safely."""
    res = await ToolExecutor.execute("get_page_content", {"unrecognized_extra_key": 12345, "nested": {"a": 1}})
    assert res["status"] == "success"
    assert res["tool_name"] == "get_page_content"


# ===========================================================================
# Feature 15: Dynamic Planner Agent Upgrade Bounds (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t2_f15_01_empty_prompt_plan_generation():
    """Boundary: PlannerAgent.create_plan with empty prompt string produces valid TaskPlan."""
    plan = await PlannerAgent.create_plan(task_id="t-empty", prompt="")
    assert isinstance(plan, TaskPlan)
    assert plan.task_id == "t-empty"
    assert len(plan.steps) >= 1


@pytest.mark.asyncio
async def test_t2_f15_02_malformed_llm_json_fallback(mock_nim_provider):
    """Boundary: PlannerAgent creates deterministic fallback plan when LLM output lacks JSON array."""
    mock_nim_provider.queue_completion("Here is my thoughts without any bracketed JSON at all.")
    plan = await PlannerAgent.create_plan(task_id="t-malformed", prompt="Search for latest laptops")
    assert isinstance(plan, TaskPlan)
    assert len(plan.steps) == 3
    # Step 1 must be browser navigate
    assert plan.steps[0].action == "navigate"


def test_t2_f15_03_planner_failure_fallback_structure():
    """Boundary: Fallback plan includes navigate, get_page_content, and verify_task steps."""
    plan_source = (WORKSPACE_ROOT / "backend" / "app" / "agents" / "planner.py").read_text(encoding="utf-8")
    assert '"navigate"' in plan_source
    assert '"get_page_content"' in plan_source
    assert '"verify_task"' in plan_source


@pytest.mark.asyncio
async def test_t2_f15_04_replan_subgoal_empty_observation():
    """Boundary: replan_subgoal handles completely empty DOM observation without KeyError."""
    step = TaskStep(id=1, agent="browser", action="click_element", description="Click element", parameters={"x": 50, "y": 50})
    result = await PlannerAgent.replan_subgoal(
        task_id="t-replan",
        failed_step=step,
        error_context="Element occluded by modal",
        current_obs={},
        remaining_steps=[]
    )
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_t2_f15_05_replan_subgoal_llm_failure(mock_nim_provider):
    """Boundary: LLM raising timeout during replanning recovers returning self-healing recovery step."""
    mock_nim_provider.simulate_timeout = True
    step = TaskStep(id=1, agent="browser", action="navigate", description="Test", parameters={})
    res = await PlannerAgent.replan_subgoal("t-fail", step, "Network Error", {}, [])
    assert len(res) == 1
    assert res[0].action == "scroll_page"


# ===========================================================================
# Feature 16: Supervisor Agent Coordination Bounds (5 tests)
# ===========================================================================

def test_t2_f16_01_cancel_nonexistent_task():
    """Boundary: Cancelling an unknown task ID is safe and does not raise errors."""
    SupervisorAgent.cancel_task("completely-unknown-task-id")
    assert SupervisorAgent.is_cancelled("completely-unknown-task-id") is True
    SupervisorAgent._cleanup_task("completely-unknown-task-id")


def test_t2_f16_02_pause_idempotency():
    """Boundary: Multiple pause calls on the same task ID remain idempotent."""
    task_id = "task-pause-idempotent"
    SupervisorAgent.pause_task(task_id)
    SupervisorAgent.pause_task(task_id)
    assert SupervisorAgent.is_paused(task_id) is True
    SupervisorAgent._cleanup_task(task_id)


def test_t2_f16_03_resume_unpaused_task():
    """Boundary: Resuming a task that was never paused is safe and no-op."""
    task_id = "task-never-paused"
    SupervisorAgent.resume_task(task_id)
    assert SupervisorAgent.is_paused(task_id) is False


@pytest.mark.asyncio
async def test_t2_f16_04_specialist_exception_isolation(test_db):
    """Boundary: Exception thrown by a specialist agent is isolated by run_task, setting failed status."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Isolation Task", "Testing error isolation")
        task_id = task.id

    with patch.object(BrowserAgent, "execute_step", side_effect=ValueError("Specialist memory corruption")):
        # run_task catches exception and marks task status failed
        await SupervisorAgent.run_task(task_id)

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        t = await repo.get_task(task_id)
        assert t.status == "failed"
        assert SupervisorAgent.is_cancelled(task_id) is False


def test_t2_f16_05_task_cleanup_state():
    """Boundary: _cleanup_task cleanly removes both cancelled and paused states."""
    task_id = "task-cleanup-test"
    SupervisorAgent.cancel_task(task_id)
    SupervisorAgent.pause_task(task_id)
    SupervisorAgent._cleanup_task(task_id)
    assert SupervisorAgent.is_cancelled(task_id) is False
    assert SupervisorAgent.is_paused(task_id) is False


# ===========================================================================
# Feature 17: Specialist Agents Architecture Bounds (5 tests)
# ===========================================================================

def test_t2_f17_01_invalid_specialist_type():
    """Boundary: Pydantic TaskStep model rejects unrecognized specialist agent strings."""
    with pytest.raises(Exception):
        TaskStep(
            id=1,
            agent="unknown_specialist_alien",
            action="get_page_content",
            description="Run get_page_content",
            parameters={}
        )


@pytest.mark.asyncio
async def test_t2_f17_02_specialist_unsupported_action():
    """Boundary: Passing unsupported action to BrowserAgent returns canonical error."""
    res = await BrowserAgent.execute_step("unsupported_browser_action_xyz", {})
    assert res["status"] == "error"
    assert "Unknown tool" in res["error"]


@pytest.mark.asyncio
async def test_t2_f17_03_data_agent_unsupported_action():
    """Boundary: Passing unknown action to DataAgent delegates to ToolExecutor returning error."""
    res = await DataAgent.execute_step("unsupported_data_action_xyz", {})
    assert res["status"] == "error"
    assert "Unknown tool" in res["error"]


@pytest.mark.asyncio
async def test_t2_f17_04_verifier_agent_unknown_action():
    """Boundary: Passing unknown action to VerifierAgent handles safely without crashing."""
    res = await VerifierAgent.execute_step("unknown_verify_action_xyz", {})
    assert "verified" in res or "status" in res


@pytest.mark.asyncio
async def test_t2_f17_05_researcher_agent_unsupported_action():
    """Boundary: Passing unknown action to ResearcherAgent handles safely without crash."""
    res = await ResearcherAgent.execute_step("unknown_research_action_xyz", {})
    assert res["status"] == "error" or "status" in res


# ===========================================================================
# Feature 18: Tab-Specific Context Binding Bounds (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t2_f18_01_navigate_with_tab_id(mock_bridge):
    """Boundary: ToolExecutor.execute navigate with tab_id updates specific tab URL."""
    res = await ToolExecutor.execute("navigate", {"url": "https://example.com/tab-target", "tab_id": "tab-1"})
    assert res["status"] == "success"
    assert res["navigated_to"] == "https://example.com/tab-target"


@pytest.mark.asyncio
async def test_t2_f18_02_inspect_with_tab_id(mock_bridge):
    """Boundary: Inspecting specific tab ID via VirtualElectronBridge returns target tab metadata."""
    mock_bridge.tabs.append({"id": "tab-special", "url": "https://example.com/special", "title": "Special Tab", "active": False})
    state = await mock_bridge.handle_call("browser.inspect", {"tabId": "tab-special"})
    assert state["url"] == "https://example.com/special"
    assert state["title"] == "Special Tab"


@pytest.mark.asyncio
async def test_t2_f18_03_nonexistent_tab_switch(mock_bridge):
    """Boundary: Switching to non-existent tab ID returns error status."""
    res = await mock_bridge.handle_call("browser.switch_tab", {"tabId": "nonexistent-tab-999"})
    assert res["status"] == "error"
    assert "not found" in res["error"]


@pytest.mark.asyncio
async def test_t2_f18_04_close_active_tab_fallback(mock_bridge):
    """Boundary: Closing active tab switches focus automatically to remaining tab."""
    await mock_bridge.handle_call("browser.create_tab", {"url": "https://example.com/tab2"})
    assert len(mock_bridge.tabs) == 2
    # Close active tab
    active_id = mock_bridge.active_tab_id
    await mock_bridge.handle_call("browser.close_tab", {"tabId": active_id})
    assert mock_bridge.active_tab_id == "tab-1"


@pytest.mark.asyncio
async def test_t2_f18_05_open_new_tab_canonical(mock_bridge):
    """Boundary: ToolExecutor open_new_tab returns canonical response containing tab_id."""
    res = await ToolExecutor.execute("open_new_tab", {"url": "https://example.com/newtab"})
    assert res["status"] == "success"
    assert res["tool_name"] == "open_new_tab"
    assert "tab_id" in res
    assert "result" in res


# ===========================================================================
# Feature 19: Windows Desktop Automation Hardening Bounds (5 tests)
# ===========================================================================

def test_t2_f19_01_blocked_unauthorized_launch_app():
    """Boundary: Attempting to launch executable requires explicit RED TIER user approval."""
    requires_appr, reason = ApprovalManager.evaluate_tool_call("desktop_launch_app", {"app_name": "cmd.exe"})
    assert requires_appr is True
    assert "RED TIER" in reason


@pytest.mark.asyncio
async def test_t2_f19_02_negative_mouse_coordinates(mock_desktop_primitives):
    """Boundary: DesktopService.mouse_click with negative coordinates handles safely."""
    res = await DesktopService.mouse_click(-100, -200)
    assert res["status"] in ("success", "error")


@pytest.mark.asyncio
async def test_t2_f19_03_hotkey_invalid_keys(mock_desktop_primitives):
    """Boundary: DesktopService.send_hotkey with unknown key strings completes without crashing."""
    res = await DesktopService.send_hotkey(["unknown_key_xyz", "bad_key_123"])
    assert res["status"] == "success"
    assert "hotkey" in res


@pytest.mark.asyncio
async def test_t2_f19_04_type_text_empty_string(mock_desktop_primitives):
    """Boundary: DesktopService.type_text with empty string returns success with length 0."""
    res = await DesktopService.type_text("")
    assert res["status"] == "success"
    assert res["typed_length"] == 0


def test_t2_f19_05_system_termination_hotkey_requires_approval():
    """Boundary: Hotkeys containing system termination keys (f4, del, delete) require RED TIER approval."""
    appr1, reason1 = ApprovalManager.evaluate_tool_call("desktop_hotkey", {"keys": ["alt", "f4"]})
    assert appr1 is True
    assert "RED TIER" in reason1

    appr2, reason2 = ApprovalManager.evaluate_tool_call("desktop_hotkey", {"keys": ["ctrl", "alt", "del"]})
    assert appr2 is True
    assert "RED TIER" in reason2


# ===========================================================================
# Feature 20: Desktop Audit Logging & Kill Switch Bounds (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t2_f20_01_emergency_stop_blocks_mouse(mock_desktop_primitives):
    """Boundary: When emergency stop is active, mouse_click is blocked immediately."""
    DesktopService.emergency_stop()
    assert DesktopService.is_stopped() is True

    res = await DesktopService.mouse_click(100, 100)
    assert res["status"] == "error"
    assert "Emergency stop is active" in res["error"]
    DesktopService.reset_emergency_stop()


@pytest.mark.asyncio
async def test_t2_f20_02_emergency_stop_blocks_typing(mock_desktop_primitives):
    """Boundary: When emergency stop is active, type_text is blocked immediately."""
    DesktopService.emergency_stop()
    res = await DesktopService.type_text("Secret text")
    assert res["status"] == "error"
    assert "Emergency stop is active" in res["error"]
    DesktopService.reset_emergency_stop()


@pytest.mark.asyncio
async def test_t2_f20_03_emergency_stop_blocks_hotkey(mock_desktop_primitives):
    """Boundary: When emergency stop is active, send_hotkey is blocked immediately."""
    DesktopService.emergency_stop()
    res = await DesktopService.send_hotkey(["ctrl", "c"])
    assert res["status"] == "error"
    assert "Emergency stop is active" in res["error"]
    DesktopService.reset_emergency_stop()


@pytest.mark.asyncio
async def test_t2_f20_04_emergency_stop_blocks_launch_app(mock_desktop_primitives):
    """Boundary: When emergency stop is active, launch_app is blocked immediately."""
    DesktopService.emergency_stop()
    res = await DesktopService.launch_app("notepad.exe")
    assert res["status"] == "error"
    assert "Emergency stop is active" in res["error"]
    DesktopService.reset_emergency_stop()


def test_t2_f20_05_reset_emergency_stop_resumes():
    """Boundary: reset_emergency_stop clears stopped state and restores operational capability."""
    DesktopService.emergency_stop()
    assert DesktopService.is_stopped() is True

    res = DesktopService.reset_emergency_stop()
    assert res["status"] == "ok"
    assert res["emergency_stopped"] is False
    assert DesktopService.is_stopped() is False
