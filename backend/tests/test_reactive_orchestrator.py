import pytest
from backend.app.agents.supervisor import SupervisorAgent
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.models import TaskStep
from backend.app.security.approval import ApprovalManager
from backend.app.tools.definitions import BROWSER_TOOLS

def test_supervisor_cooperative_lifecycle():
    task_id = "test-task-123"
    assert not SupervisorAgent.is_cancelled(task_id)
    assert not SupervisorAgent.is_paused(task_id)

    # Pause
    SupervisorAgent.pause_task(task_id)
    assert SupervisorAgent.is_paused(task_id)

    # Resume
    SupervisorAgent.resume_task(task_id)
    assert not SupervisorAgent.is_paused(task_id)

    # Cancel
    SupervisorAgent.cancel_task(task_id)
    assert SupervisorAgent.is_cancelled(task_id)

    # Cleanup
    SupervisorAgent._cleanup_task(task_id)
    assert not SupervisorAgent.is_cancelled(task_id)

@pytest.mark.asyncio
async def test_planner_replan_subgoal():
    failed_step = TaskStep(
        id=2,
        agent="browser",
        action="click_selector",
        description="Click submit button",
        parameters={"selector": "button.submit"},
        expected_outcome="Button clicked"
    )
    current_obs = {
        "url": "https://example.com/login",
        "visibleText": "Please log in to continue.",
        "interactiveElements": []
    }
    remaining = [
        TaskStep(
            id=3,
            agent="verifier",
            action="verify_task",
            description="Verify login success",
            parameters={},
            expected_outcome="Logged in"
        )
    ]

    recovery_steps = await PlannerAgent.replan_subgoal(
        task_id="test-task-replan",
        failed_step=failed_step,
        error_context="Element not found: button.submit",
        current_obs=current_obs,
        remaining_steps=remaining
    )

    assert len(recovery_steps) >= 1
    assert any("[RECOVERY]" in s.description for s in recovery_steps)

def test_approval_manager_sensitive_selectors():
    # Sensitive password selector
    req_pwd, reason_pwd = ApprovalManager.evaluate_tool_call("fill_selector", {"selector": "input#password", "text": "mysecret"})
    assert req_pwd is True
    assert "credential" in reason_pwd.lower() or "password" in reason_pwd.lower()

    # Form submit button
    req_sub, reason_sub = ApprovalManager.evaluate_tool_call("click_selector", {"selector": "button[type='submit']"})
    assert req_sub is True
    assert "confirmation" in reason_sub.lower() or "submission" in reason_sub.lower() or "submitting" in reason_sub.lower()

    # Normal harmless navigation or selector
    req_norm, _ = ApprovalManager.evaluate_tool_call("click_selector", {"selector": "a.nav-link"})
    assert req_norm is False

    # Harmless read-only inspection
    req_read, _ = ApprovalManager.evaluate_tool_call("detect_forms", {})
    assert req_read is False

    req_tree, _ = ApprovalManager.evaluate_tool_call("get_accessibility_tree", {})
    assert req_tree is False

def test_browser_tools_schema_registered():
    tool_names = [t["function"]["name"] for t in BROWSER_TOOLS if t.get("type") == "function"]
    assert "click_selector" in tool_names
    assert "fill_selector" in tool_names
    assert "wait_for_selector" in tool_names
    assert "detect_forms" in tool_names
    assert "get_accessibility_tree" in tool_names

def test_browser_agent_matched_element_index():
    from backend.app.agents.browser_agent import BrowserAgent
    elements = [
        {"id": "el-0", "selector": "#header", "tagName": "div"},
        {"id": "el-1", "selector": "[data-testid=\"search-btn\"]", "tagName": "button", "text": "Search"},
        {"id": "el-2", "selector": "text=Submit Order", "tagName": "button", "text": "Submit Order"},
        {"id": "el-3", "selector": "input:nth-of-type(1)", "tagName": "input", "label": "Username"},
    ]
    # Exact match
    assert BrowserAgent._find_matched_element_index("#header", elements) == 0
    # Case insensitive
    assert BrowserAgent._find_matched_element_index("[data-testid=\"SEARCH-BTN\"]", elements) == 1
    # text= match
    assert BrowserAgent._find_matched_element_index("text=Submit Order", elements) == 2
    # Label match
    assert BrowserAgent._find_matched_element_index("Username", elements) == 3
    # Empty elements
    assert BrowserAgent._find_matched_element_index("#header", []) is None
