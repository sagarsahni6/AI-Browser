import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from langgraph.types import Command
from backend.app.database.engine import AsyncSessionLocal, init_db
from backend.app.database.repository import Repository
from backend.app.graph.state import GraphState
from backend.app.graph.graph import build_graph
from backend.app.graph.checkpointer import init_checkpointer, close_checkpointer, get_checkpointer
from backend.app.browser.bridge import bridge


@pytest.fixture(autouse=True)
async def setup_db_and_checkpointer():
    await init_db()
    await init_checkpointer("sqlite+aiosqlite:///:memory:")
    yield
    await close_checkpointer()


@pytest.mark.asyncio
async def test_security_approval_interrupt_and_resume():
    """
    Tests that a tool requiring approval (desktop_launch_app) triggers
    LangGraph interrupt(), halts execution, creates DB approval record,
    and resumes exactly once when Command(resume=True) is delivered.
    """
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title="Approval Test Task", prompt="Launch calculator app")
        task_id = task.id

    checkpointer = get_checkpointer()
    compiled_graph = build_graph(checkpointer=checkpointer)
    thread_id = f"test-approval-thread-{task_id}"
    config = {"configurable": {"thread_id": thread_id}}

    # Custom plan step with an approval-required tool
    plan_steps = [
        {
            "id": 1,
            "agent": "desktop",
            "action": "desktop_launch_app",
            "description": "Launch calculator app",
            "parameters": {"app_name": "calc.exe"},
            "verification_strategy": "none",
        }
    ]

    initial_state: GraphState = {
        "task_id": task_id,
        "graph_thread_id": thread_id,
        "prompt": "Launch calculator app",
        "current_url": "about:blank",
        "task_type": "tools",
        "plan_steps": plan_steps,
        "current_step_index": 0,
        "total_steps": 1,
        "step_results": [],
        "current_step": {},
        "next_agent": "supervisor",
        "approval_decision": None,
        "approval_id": None,
        "last_error": None,
        "last_tool_result": None,
        "retry_count": 0,
        "max_retries": 3,
        "final_report": None,
        "status": "running",
    }

    # Step 1: Run graph until interrupt
    events = []
    async for event in compiled_graph.astream(initial_state, config=config, stream_mode="values"):
        events.append(event)

    # Check graph paused at interrupt
    current_snapshot = await compiled_graph.aget_state(config)
    assert len(current_snapshot.tasks) > 0
    # There should be an active interrupt in the snapshot
    task_interrupts = current_snapshot.tasks[0].interrupts
    assert len(task_interrupts) > 0
    interrupt_val = task_interrupts[0].value
    assert interrupt_val.get("type") == "approval_required"
    assert interrupt_val.get("tool_name") == "desktop_launch_app"

    # Verify DB recorded the pending approval
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        pending_appr = await repo.get_pending_approval_for_task(task_id)
        assert pending_appr is not None
        assert pending_appr.tool_name == "desktop_launch_app"
        assert pending_appr.status == "pending"

    # Step 2: Resume with approved decision Command(resume=True)
    with patch("backend.app.tools.executor.ToolExecutor.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"status": "success", "result": "launched calc.exe"}
        with patch.object(bridge, "call", new_callable=AsyncMock) as mock_bridge:
            mock_bridge.return_value = {"url": "about:blank", "title": "Desktop"}

            resume_events = []
            async for event in compiled_graph.astream(Command(resume=True), config=config, stream_mode="values"):
                resume_events.append(event)

            # ToolExecutor must have executed desktop_launch_app exactly once with bypass_approval=True
            calc_calls = [c for c in mock_exec.call_args_list if len(c[0]) > 0 and c[0][0] == "desktop_launch_app"]
            assert len(calc_calls) == 1
            assert calc_calls[0] == (("desktop_launch_app", {"app_name": "calc.exe"}), {"bypass_approval": True})

    # Check final state after resumption
    final_snapshot = await compiled_graph.aget_state(config)
    assert final_snapshot.values.get("status") == "completed"
    assert len(final_snapshot.values.get("step_results", [])) == 1


@pytest.mark.asyncio
async def test_security_approval_rejection():
    """
    Tests that rejecting an approval request cancels the task cleanly.
    """
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title="Reject Test Task", prompt="Launch notepad")
        task_id = task.id

    checkpointer = get_checkpointer()
    compiled_graph = build_graph(checkpointer=checkpointer)
    thread_id = f"test-reject-thread-{task_id}"
    config = {"configurable": {"thread_id": thread_id}}

    plan_steps = [
        {
            "id": 1,
            "agent": "desktop",
            "action": "desktop_launch_app",
            "description": "Launch notepad",
            "parameters": {"app_name": "notepad.exe"},
        }
    ]

    initial_state: GraphState = {
        "task_id": task_id,
        "graph_thread_id": thread_id,
        "prompt": "Launch notepad",
        "current_url": "about:blank",
        "task_type": "tools",
        "plan_steps": plan_steps,
        "current_step_index": 0,
        "total_steps": 1,
        "step_results": [],
        "current_step": {},
        "next_agent": "supervisor",
        "approval_decision": None,
        "approval_id": None,
        "last_error": None,
        "last_tool_result": None,
        "retry_count": 0,
        "max_retries": 3,
        "final_report": None,
        "status": "running",
    }

    # Run to interrupt
    async for _ in compiled_graph.astream(initial_state, config=config, stream_mode="values"):
        pass

    # Resume with rejection
    async for _ in compiled_graph.astream(Command(resume=False), config=config, stream_mode="values"):
        pass

    final_snapshot = await compiled_graph.aget_state(config)
    assert final_snapshot.values.get("status") == "cancelled"
