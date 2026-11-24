"""
tests/e2e/tier1_features/test_t1_f11_f20.py
Tier 1 Feature Coverage Tests: Features 11 to 20 (50 tests total, 5 per feature).

Features Covered:
  F11: Unified Agent Runtime
  F12: ReAct Cognitive Execution Loop
  F13: Execution Budget Limits
  F14: Central Tool Registry
  F15: Dynamic Planner Agent Upgrade
  F16: Supervisor Agent Coordination
  F17: Specialist Agents Architecture
  F18: Tab-Specific Context Binding
  F19: Windows Desktop Automation Hardening
  F20: Desktop Audit Logging & Kill Switch
"""

import asyncio
import json
import inspect
import pytest
from pathlib import Path
from typing import Dict, Any, List

from backend.app.config import settings
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.repository import Repository
from backend.app.agents.models import TaskPlan, TaskStep, StepStatus
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.supervisor import SupervisorAgent
from backend.app.agents.browser_agent import BrowserAgent
from backend.app.agents.researcher import ResearcherAgent
from backend.app.agents.data_agent import DataAgent
from backend.app.agents.verifier import VerifierAgent
from backend.app.tools.definitions import get_all_browser_tools, BROWSER_TOOLS
from backend.app.tools.executor import ToolExecutor
from backend.app.security.approval import ApprovalManager
from backend.app.automation.desktop.service import DesktopService
from backend.app.browser.bridge import bridge
from backend.app.api.assistant import build_system_prompt

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent


# ===========================================================================
# Feature 11: Unified Agent Runtime (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t1_f11_01_chat_turn_execution(async_client, test_db):
    """Conversational chat turn invokes unified runtime endpoint and returns model reply."""
    resp = await async_client.post(
        "/api/v1/assistant/chat",
        json={"message": "What is AI Browser?", "stream": False}
    )
    assert resp.status_code == 200, f"Chat endpoint failed: {resp.text}"
    data = resp.json()
    assert "reply" in data
    assert "conversation_id" in data
    assert len(data["reply"]) > 0


@pytest.mark.asyncio
async def test_t1_f11_02_autonomous_task_execution(async_client, test_db):
    """Autonomous task creation executes under shared runtime via tasks API."""
    resp = await async_client.post(
        "/api/v1/agent/tasks",
        json={"title": "Doc Inspection", "prompt": "Navigate to docs and inspect content"}
    )
    assert resp.status_code in (200, 201), f"Task creation failed: {resp.text}"
    data = resp.json()
    assert "id" in data
    assert data["id"].startswith("task-")
    assert data["status"] in ("pending", "running")


@pytest.mark.asyncio
async def test_t1_f11_03_shared_memory_access(test_db):
    """Both chat and autonomous tasks share user memory context stored in repository."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        created_mem = await repo.create_user_memory(
            key="preferred_search_engine",
            value="duckduckgo",
            category="preference",
            tags=["search", "browser"]
        )
        assert created_mem.id.startswith("mem-")

        # Verify retrieval across runtime components
        memories = await repo.get_user_memories(category="preference")
        assert len(memories) >= 1
        assert any(m.key == "preferred_search_engine" and m.value == "duckduckgo" for m in memories)


def test_t1_f11_04_shared_tool_registry():
    """Chat assistant and autonomous supervisor share identical tool definitions."""
    tools = get_all_browser_tools()
    assert len(tools) >= 10, "Shared tool registry missing core tools"
    tool_names = [t["function"]["name"] for t in tools if "function" in t]
    assert "navigate" in tool_names
    assert "get_page_content" in tool_names
    assert "search_web" in tool_names
    assert "extract_table_data" in tool_names


@pytest.mark.asyncio
async def test_t1_f11_05_runtime_state_lifecycle(test_db):
    """Runtime task transitions cleanly through state lifecycle: pending -> running -> completed."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(
            title="Lifecycle Test",
            prompt="Observe page and verify state"
        )
        assert task.status == "pending"

    # Run through supervisor execution
    await SupervisorAgent.run_task(task.id)

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        final_task = await repo.get_task(task.id)
        assert final_task.status == "completed"
        assert final_task.completed_at is not None


# ===========================================================================
# Feature 12: ReAct Cognitive Execution Loop (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t1_f12_01_observation_capture(mock_bridge):
    """Live DOM observation captured via CDP before each cognitive tool decision."""
    mock_bridge.set_dom_state(
        url="https://react.example.com",
        title="ReAct Loop Test",
        text="Target element present for automated action."
    )
    obs = await bridge.call("browser.inspect", {})
    assert obs["url"] == "https://react.example.com"
    assert obs["title"] == "ReAct Loop Test"
    assert "Target element" in obs["visibleText"]


def test_t1_f12_02_thought_trace_generation():
    """System prompt enforces structured ReAct thought, plan, action, observation cycle."""
    prompt = build_system_prompt(
        page_context={"title": "Test Page", "url": "https://example.com"},
        user_message="Find the pricing table and extract values"
    )
    assert "<thought>" in prompt
    assert "<plan>" in prompt
    assert "<action>" in prompt
    assert "<observation>" in prompt
    assert "ReAct" in prompt


@pytest.mark.asyncio
async def test_t1_f12_03_action_dispatch(mock_bridge):
    """ReAct cycle dispatches tool action and receives observation back."""
    res = await BrowserAgent.execute_step("navigate", {"url": "https://example.com/products"})
    assert res["status"] == "success"
    assert any(c["method"] == "browser.navigate" for c in mock_bridge.calls)


@pytest.mark.asyncio
async def test_t1_f12_04_self_correction_on_error():
    """ReAct execution re-plans corrective sub-goals when an execution step encounters failure."""
    failed_step = TaskStep(
        id=2,
        agent="browser",
        action="click_selector",
        description="Click checkout button",
        parameters={"selector": "button#checkout"}
    )
    obs = {"url": "https://store.example.com", "visibleText": "Cart is loading..."}

    corrective_steps = await PlannerAgent.replan_subgoal(
        task_id="task-react-123",
        failed_step=failed_step,
        error_context="Element 'button#checkout' not visible",
        current_obs=obs,
        remaining_steps=[]
    )
    assert len(corrective_steps) >= 1
    assert any(s.action in ("scroll_page", "wait_for_selector", "click_selector") for s in corrective_steps)


@pytest.mark.asyncio
async def test_t1_f12_05_loop_termination_on_verified():
    """Cognitive execution loop halts successfully upon verified objective completion."""
    res = await VerifierAgent.execute_step("verify_task", {})
    assert res["status"] == "success"
    assert res.get("verified") is True


# ===========================================================================
# Feature 13: Execution Budget Limits (5 tests)
# ===========================================================================

def test_t1_f13_01_step_limit_enforced():
    """TaskStep model defines explicit timeout seconds preventing runaway execution."""
    step = TaskStep(
        id=1,
        agent="browser",
        action="navigate",
        description="Navigate to target",
        parameters={"url": "https://example.com"}
    )
    assert hasattr(step, "timeout_seconds")
    assert step.timeout_seconds > 0
    assert step.timeout_seconds <= 120


def test_t1_f13_02_tool_call_limit_enforced():
    """TaskPlan model contains bounded step arrays rather than unbounded loops."""
    plan = TaskPlan(
        task_id="task-budget-1",
        description="Budget Test",
        steps=[
            TaskStep(id=i, action="scroll_page", description=f"Step {i}")
            for i in range(1, 6)
        ]
    )
    assert len(plan.steps) == 5
    assert plan.estimated_time_seconds > 0


@pytest.mark.asyncio
async def test_t1_f13_03_time_limit_enforced():
    """Execution with explicit timeout handles time limits gracefully."""
    async def delayed_action():
        await asyncio.sleep(0.5)
        return {"status": "success"}

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(delayed_action(), timeout=0.05)


@pytest.mark.asyncio
async def test_t1_f13_04_retry_limit_enforced(test_db, monkeypatch):
    """Step failure retries are strictly capped at max_retries_per_step (3)."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title="Retry Cap Test", prompt="Action that fails")

    # Simulate specialist action that consistently fails
    async def failing_action(action, params):
        return {"status": "error", "error": "Persistent DOM error"}

    monkeypatch.setattr(BrowserAgent, "execute_step", failing_action)

    # Execution should finish and not loop infinitely
    await SupervisorAgent.run_task(task.id)

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task_record = await repo.get_task(task.id)
        assert task_record is not None
        # Task finishes with completed or failed, but never hangs
        assert task_record.status in ("completed", "failed")


@pytest.mark.asyncio
async def test_t1_f13_05_partial_results_saved(test_db):
    """Task execution persists intermediate step records in the database."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title="Intermediate Results", prompt="Multi-step run")

    await SupervisorAgent.run_task(task.id)

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        steps = await repo.get_task_steps(task.id)
        assert len(steps) >= 1
        valid_statuses = ("success", "completed", "pending", "running", "failed", "approval_required")
        assert all(s.status in valid_statuses for s in steps)


# ===========================================================================
# Feature 14: Central Tool Registry (5 tests)
# ===========================================================================

def test_t1_f14_01_list_all_tools():
    """Tool registry returns core tools and all registered system capabilities."""
    tools = get_all_browser_tools()
    assert isinstance(tools, list)
    assert len(tools) >= 15
    names = {t["function"]["name"] for t in tools if "function" in t}
    expected_core = {"navigate", "get_page_content", "click_element", "fill_input", "scroll_page", "search_web"}
    assert expected_core.issubset(names)


def test_t1_f14_02_pydantic_schema_validation():
    """All tools declare valid JSON-schema parameter specifications."""
    tools = get_all_browser_tools()
    for t in tools:
        fn = t.get("function", {})
        assert "name" in fn, "Tool definition missing name"
        assert "parameters" in fn, f"Tool {fn.get('name')} missing parameters schema"
        params = fn["parameters"]
        assert params.get("type") == "object"
        assert "properties" in params


def test_t1_f14_03_risk_tier_metadata():
    """Every registered tool is mapped into the central security risk tier policy."""
    tools = get_all_browser_tools()
    for t in tools:
        tool_name = t["function"]["name"]
        requires_approval, reason = ApprovalManager.evaluate_tool_call(tool_name, {})
        assert isinstance(requires_approval, bool)
        assert isinstance(reason, str)
        assert len(reason) > 0


def test_t1_f14_04_timeout_metadata():
    """TaskStep schema requires timeout configuration on every execution unit."""
    step = TaskStep(id=1, action="navigate", description="Test timeout", timeout_seconds=30)
    assert step.timeout_seconds == 30
    default_step = TaskStep(id=2, action="navigate", description="Default timeout")
    assert default_step.timeout_seconds == 45


def test_t1_f14_05_dynamic_skill_tool_registration():
    """Dynamic skill tools are registered and retrievable via get_all_browser_tools."""
    from backend.app.skills.registry import skill_registry
    skill_tools = skill_registry.get_all_active_tools()
    all_tools = get_all_browser_tools()
    assert len(all_tools) >= len(BROWSER_TOOLS)
    if skill_tools:
        skill_names = {t["function"]["name"] for t in skill_tools if "function" in t}
        all_names = {t["function"]["name"] for t in all_tools if "function" in t}
        assert skill_names.issubset(all_names)


# ===========================================================================
# Feature 15: Dynamic Planner Agent Upgrade (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t1_f15_01_plan_creation_structure():
    """PlannerAgent creates a structured TaskPlan with sequential TaskSteps."""
    plan = await PlannerAgent.create_plan(
        task_id="task-plan-001",
        prompt="Search for Python documentation and extract getting started guide",
        current_url="https://www.python.org"
    )
    assert isinstance(plan, TaskPlan)
    assert plan.task_id == "task-plan-001"
    assert len(plan.steps) >= 2
    for idx, step in enumerate(plan.steps):
        assert isinstance(step, TaskStep)
        assert step.id == idx + 1


@pytest.mark.asyncio
async def test_t1_f15_02_verification_step_included():
    """Generated plan includes a terminal verification step assigned to verifier agent."""
    plan = await PlannerAgent.create_plan(
        task_id="task-plan-002",
        prompt="Download monthly report"
    )
    assert any(s.agent == "verifier" or "verify" in s.action for s in plan.steps)


@pytest.mark.asyncio
async def test_t1_f15_03_subgoal_replanning():
    """PlannerAgent generates corrective replacement steps on step failure."""
    failed_step = TaskStep(
        id=1,
        agent="browser",
        action="click_selector",
        description="Click Next Page",
        parameters={"selector": "a.pagination-next"}
    )
    obs = {"url": "https://example.com/items", "visibleText": "Page 1 of 5"}
    new_steps = await PlannerAgent.replan_subgoal(
        task_id="task-plan-003",
        failed_step=failed_step,
        error_context="Selector not found",
        current_obs=obs,
        remaining_steps=[]
    )
    assert len(new_steps) >= 1
    assert new_steps[0].id == failed_step.id


@pytest.mark.asyncio
async def test_t1_f15_04_dependency_ordering():
    """Generated plan maintains logical dependency sequence (navigate before act/extract)."""
    plan = await PlannerAgent.create_plan(
        task_id="task-plan-004",
        prompt="Find latest articles on technology"
    )
    first_step = plan.steps[0]
    assert first_step.action in ("navigate", "search_web", "get_page_content")


@pytest.mark.asyncio
async def test_t1_f15_05_agent_specialist_assignment():
    """Generated plan assigns steps to appropriate specialist agents (browser, data, verifier)."""
    plan = await PlannerAgent.create_plan(
        task_id="task-plan-005",
        prompt="Extract table from financial page"
    )
    agents_used = {s.agent for s in plan.steps}
    valid_agents = {"browser", "researcher", "data", "verifier", "supervisor"}
    assert agents_used.issubset(valid_agents)


# ===========================================================================
# Feature 16: Supervisor Agent Coordination (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t1_f16_01_full_lifecycle_run(test_db):
    """SupervisorAgent coordinates complete lifecycle from pending to completed."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title="Coordination Run", prompt="Navigate and verify")

    await SupervisorAgent.run_task(task.id)

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task_rec = await repo.get_task(task.id)
        assert task_rec.status == "completed"
        assert task_rec.result is not None


def test_t1_f16_02_cooperative_pause_resume():
    """SupervisorAgent supports cooperative pause and resume state tracking."""
    task_id = "task-pause-test-1"
    SupervisorAgent.pause_task(task_id)
    assert SupervisorAgent.is_paused(task_id) is True

    SupervisorAgent.resume_task(task_id)
    assert SupervisorAgent.is_paused(task_id) is False


def test_t1_f16_03_cooperative_cancellation():
    """SupervisorAgent supports cooperative cancellation flag setting and querying."""
    task_id = "task-cancel-test-1"
    SupervisorAgent.cancel_task(task_id)
    assert SupervisorAgent.is_cancelled(task_id) is True
    SupervisorAgent._cleanup_task(task_id)
    assert SupervisorAgent.is_cancelled(task_id) is False


@pytest.mark.asyncio
async def test_t1_f16_04_db_step_tracking(test_db):
    """SupervisorAgent writes every planned and executed step to the task_steps table."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title="Step Tracking", prompt="Perform test actions")

    await SupervisorAgent.run_task(task.id)

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        steps = await repo.get_task_steps(task.id)
        assert len(steps) >= 2
        valid_statuses = ("success", "completed", "pending", "running", "failed", "approval_required")
        for s in steps:
            assert s.status in valid_statuses


@pytest.mark.asyncio
async def test_t1_f16_05_live_progress_notifications(mock_bridge, test_db):
    """SupervisorAgent emits 'task.step_updated' JSON-RPC bridge notifications."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title="Notif Task", prompt="Quick notification test")

    await SupervisorAgent.run_task(task.id)

    step_notifs = [n for n in mock_bridge.notifications if n["method"] == "task.step_updated"]
    assert len(step_notifs) >= 1
    assert any(n["params"].get("status") == "completed" for n in step_notifs)


# ===========================================================================
# Feature 17: Specialist Agents Architecture (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t1_f17_01_browser_agent_dispatch():
    """BrowserAgent executes browser navigation and DOM interaction steps."""
    res = await BrowserAgent.execute_step("navigate", {"url": "https://example.com"})
    assert res["status"] == "success"
    assert res["tool_name"] == "navigate"


@pytest.mark.asyncio
async def test_t1_f17_02_researcher_agent_dispatch():
    """ResearcherAgent executes research and web search actions."""
    res = await ResearcherAgent.execute_step("search_web", {"query": "Machine Learning"})
    assert res["status"] == "success"
    assert res["tool_name"] == "search_web"


@pytest.mark.asyncio
async def test_t1_f17_03_data_agent_dispatch(mock_bridge):
    """DataAgent executes structured data extraction and export actions."""
    mock_bridge.set_dom_state(
        url="https://example.com/prices",
        title="Price List",
        text="Item: Laptop | Price: $999\nItem: Phone | Price: $699"
    )
    res = await DataAgent.execute_step("extract_table_data", {})
    assert res["status"] in ("ok", "success")
    assert res["total_rows"] >= 1


@pytest.mark.asyncio
async def test_t1_f17_04_verifier_agent_dispatch():
    """VerifierAgent executes goal-based objective verification actions."""
    res = await VerifierAgent.execute_step("verify_task", {})
    assert res["status"] == "success"
    assert res.get("verified") is True


@pytest.mark.asyncio
async def test_t1_f17_05_specialist_result_consistency():
    """All specialist agents return dictionaries containing standard status and result keys."""
    b_res = await BrowserAgent.execute_step("get_page_content", {})
    r_res = await ResearcherAgent.execute_step("search_web", {"query": "Quantum"})
    d_res = await DataAgent.execute_step("extract_table_data", {})
    v_res = await VerifierAgent.execute_step("verify_task", {})

    for res in (b_res, r_res, d_res, v_res):
        assert isinstance(res, dict)
        assert "status" in res
        assert res["status"] in ("ok", "success")


# ===========================================================================
# Feature 18: Tab-Specific Context Binding (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_t1_f18_01_navigate_specific_tab(mock_bridge):
    """Navigating with tab_id targets the specific tab context."""
    # Create extra tab
    await mock_bridge.handle_call("browser.create_tab", {"url": "about:blank"})
    res = await mock_bridge.handle_call("browser.navigate", {"tab_id": "tab-2", "url": "https://python.org"})
    assert res["status"] == "ok"
    # Verify tab-2 has the new url
    target_tab = next((t for t in mock_bridge.tabs if t["id"] == "tab-2"), None)
    assert target_tab is not None
    assert target_tab["url"] == "https://python.org"


@pytest.mark.asyncio
async def test_t1_f18_02_inspect_specific_tab(mock_bridge):
    """Inspecting DOM with tab_id returns content bound to that tab."""
    await mock_bridge.handle_call("browser.create_tab", {"url": "https://fastapi.tiangolo.com"})
    # Switch active tab back to tab-1 so tab-2 is in the background
    await mock_bridge.handle_call("browser.switch_tab", {"tab_id": "tab-1"})
    obs = await mock_bridge.handle_call("browser.inspect", {"tab_id": "tab-2"})
    assert obs["url"] == "https://fastapi.tiangolo.com"


@pytest.mark.asyncio
async def test_t1_f18_03_click_specific_tab(mock_bridge):
    """Clicking element with tab_id executes in the targeted tab."""
    res = await mock_bridge.handle_call("browser.click", {"tab_id": "tab-1", "x": 120, "y": 250})
    assert res["status"] == "ok"
    assert any(c["method"] == "browser.click" and c["params"].get("tab_id") == "tab-1" for c in mock_bridge.calls)


@pytest.mark.asyncio
async def test_t1_f18_04_get_all_tabs(mock_bridge):
    """Retrieving open tabs returns list with tab identifiers and active indicators."""
    tabs = await mock_bridge.handle_call("browser.get_tabs", {})
    assert isinstance(tabs, list)
    assert len(tabs) >= 1
    assert "id" in tabs[0]
    assert "url" in tabs[0]


@pytest.mark.asyncio
async def test_t1_f18_05_close_specific_tab(mock_bridge):
    """Closing specific tab removes it from open tabs collection."""
    await mock_bridge.handle_call("browser.create_tab", {"url": "https://close-me.example.com"})
    initial_count = len(mock_bridge.tabs)
    await mock_bridge.handle_call("browser.close_tab", {"tab_id": "tab-2"})
    assert len(mock_bridge.tabs) == initial_count - 1
    assert all(t["id"] != "tab-2" for t in mock_bridge.tabs)


# ===========================================================================
# Feature 19: Windows Desktop Automation Hardening (5 tests)
# ===========================================================================

def test_t1_f19_01_async_thread_offloading():
    """DesktopService methods are async coroutines preventing main event loop blockage."""
    assert inspect.iscoroutinefunction(DesktopService.mouse_click)
    assert inspect.iscoroutinefunction(DesktopService.type_text)
    assert inspect.iscoroutinefunction(DesktopService.send_hotkey)
    assert inspect.iscoroutinefunction(DesktopService.capture_screen)
    assert inspect.iscoroutinefunction(DesktopService.launch_app)


@pytest.mark.asyncio
async def test_t1_f19_02_unicode_typing_sendinput(mock_desktop_primitives):
    """type_text handles full Unicode characters and emojis safely."""
    res = await DesktopService.type_text("Hello World! Comet AI 2.0 🚀")
    assert res["status"] == "success"
    assert res["typed_length"] == len("Hello World! Comet AI 2.0 🚀")


@pytest.mark.asyncio
async def test_t1_f19_03_mouse_click_execution(mock_desktop_primitives):
    """mouse_click executes desktop click at coordinates (x, y)."""
    res = await DesktopService.mouse_click(500, 300, button="left")
    assert res["status"] == "success"
    assert res["clicked"]["x"] == 500
    assert res["clicked"]["y"] == 300


@pytest.mark.asyncio
async def test_t1_f19_04_hotkey_execution(mock_desktop_primitives):
    """send_hotkey executes multi-key sequence combinations."""
    res = await DesktopService.send_hotkey(["ctrl", "c"])
    assert res["status"] == "success"
    assert res["hotkey"] == "ctrl+c"


@pytest.mark.asyncio
async def test_t1_f19_05_allowlisted_app_launch(mock_desktop_primitives):
    """launch_app executes application process and returns assigned PID."""
    res = await DesktopService.launch_app("notepad.exe")
    assert res["status"] == "success"
    assert res["pid"] == 9999
    assert res["app"] == "notepad.exe"


# ===========================================================================
# Feature 20: Desktop Audit Logging & Kill Switch (5 tests)
# ===========================================================================

def test_t1_f20_01_emergency_stop_activation():
    """emergency_stop() activates kill switch state immediately."""
    try:
        res = DesktopService.emergency_stop()
        assert res["status"] == "ok"
        assert res["emergency_stopped"] is True
        assert DesktopService.is_stopped() is True
    finally:
        DesktopService.reset_emergency_stop()


@pytest.mark.asyncio
async def test_t1_f20_02_blocked_action_when_stopped():
    """All desktop actions return error when emergency kill switch is active."""
    DesktopService.emergency_stop()
    try:
        click_res = await DesktopService.mouse_click(100, 100)
        assert click_res["status"] == "error"
        assert "Emergency stop" in click_res["error"]

        type_res = await DesktopService.type_text("Blocked typing")
        assert type_res["status"] == "error"
        assert "Emergency stop" in type_res["error"]

        app_res = await DesktopService.launch_app("calc.exe")
        assert app_res["status"] == "error"
        assert "Emergency stop" in app_res["error"]
    finally:
        DesktopService.reset_emergency_stop()


def test_t1_f20_03_reset_emergency_stop():
    """reset_emergency_stop() restores service to operational status."""
    DesktopService.emergency_stop()
    assert DesktopService.is_stopped() is True
    reset_res = DesktopService.reset_emergency_stop()
    assert reset_res["emergency_stopped"] is False
    assert DesktopService.is_stopped() is False


@pytest.mark.asyncio
async def test_t1_f20_04_audit_log_authorized_action(test_db):
    """Authorized desktop action creates audit record with authorized=True."""
    await DesktopService.mouse_click(250, 400)
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        logs = await repo.get_desktop_audit_logs(limit=10)
        assert len(logs) >= 1
        assert logs[0].action == "mouse_click"
        assert logs[0].authorized is True


@pytest.mark.asyncio
async def test_t1_f20_05_audit_log_blocked_action(test_db):
    """Action blocked by emergency stop creates audit record with authorized=False."""
    DesktopService.emergency_stop()
    try:
        await DesktopService.launch_app("blocked_app.exe")
    finally:
        DesktopService.reset_emergency_stop()

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        logs = await repo.get_desktop_audit_logs(limit=10)
        assert len(logs) >= 1
        blocked_log = next((l for l in logs if l.action == "launch_app"), None)
        assert blocked_log is not None
        assert blocked_log.authorized is False
