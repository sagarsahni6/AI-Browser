import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from backend.app.database.engine import AsyncSessionLocal, init_db
from backend.app.database.repository import Repository
from backend.app.graph.state import GraphState
from backend.app.graph.graph import build_graph
from backend.app.graph.checkpointer import init_checkpointer, close_checkpointer, get_checkpointer
from backend.app.graph.nodes.specialist_agents import (
    dom_agent_node,
    vision_agent_node,
    research_agent_node,
    data_agent_node,
    desktop_agent_node,
    file_agent_node,
    memory_agent_node,
)
from backend.app.graph.nodes.recovery_agent import recovery_agent_node
from backend.app.browser.bridge import bridge


@pytest.fixture(autouse=True)
async def setup_db_and_checkpointer():
    await init_db()
    await init_checkpointer("sqlite+aiosqlite:///:memory:")
    yield
    await close_checkpointer()


@pytest.mark.asyncio
async def test_specialist_nodes_execution():
    """Verify that each specialist agent node executes its action and returns correct state contract."""
    # 1. DOM Agent
    with patch("backend.app.agents.dom_agent.DOMAgent.execute_step", new_callable=AsyncMock) as mock_dom:
        mock_dom.return_value = {"status": "success", "result": "clicked #submit"}
        state: GraphState = {
            "current_step": {"action": "click_selector", "parameters": {"selector": "#submit"}},
            "current_step_index": 0,
            "step_results": []
        }
        res = await dom_agent_node(state)
        assert len(res["step_results"]) == 1
        assert res["step_results"][0]["status"] == "success"

    # 2. Vision Agent
    with patch("backend.app.agents.vision_agent.VisionAgent.execute_step", new_callable=AsyncMock) as mock_vis:
        mock_vis.return_value = {"status": "success", "analysis": "Bullish pin bar"}
        state["current_step"] = {"action": "inspect_visual_chart", "parameters": {}}
        res = await vision_agent_node(state)
        assert len(res["step_results"]) == 1
        assert res["step_results"][0]["analysis"] == "Bullish pin bar"

    # 3. Data Agent
    with patch("backend.app.agents.data_agent.DataAgent.execute_step", new_callable=AsyncMock) as mock_data:
        mock_data.return_value = {"status": "success", "rows": 10}
        state["current_step"] = {"action": "extract_table_data", "parameters": {}}
        res = await data_agent_node(state)
        assert len(res["step_results"]) == 1
        assert res["step_results"][0]["rows"] == 10

    # 4. Research Agent
    with patch("backend.app.agents.researcher.ResearcherAgent.execute_step", new_callable=AsyncMock) as mock_res:
        mock_res.return_value = {"status": "success", "results": ["Paper 1", "Paper 2"]}
        state["current_step"] = {"action": "search_web", "parameters": {"query": "test"}}
        res = await research_agent_node(state)
        assert len(res["step_results"]) == 1
        assert len(res["step_results"][0]["results"]) == 2

    # 5. File Agent
    with patch("backend.app.agents.file_agent.FileAgent.execute_step", new_callable=AsyncMock) as mock_file:
        mock_file.return_value = {"status": "success", "text": "PDF content"}
        state["current_step"] = {"action": "read_pdf", "parameters": {"path_or_url": "doc.pdf"}}
        res = await file_agent_node(state)
        assert len(res["step_results"]) == 1
        assert res["step_results"][0]["text"] == "PDF content"

    # 6. Memory Agent
    with patch("backend.app.agents.memory_agent.MemoryAgent.execute_step", new_callable=AsyncMock) as mock_mem:
        mock_mem.return_value = {"status": "success", "recalled": "user preference"}
        state["current_step"] = {"action": "retrieve_memory", "parameters": {"query": "pref"}}
        res = await memory_agent_node(state)
        assert len(res["step_results"]) == 1
        assert res["step_results"][0]["recalled"] == "user preference"


@pytest.mark.asyncio
async def test_recovery_agent_replan_and_exhaustion():
    """Verify recovery agent prepends corrective steps, and halts when max retries are exceeded."""
    state: GraphState = {
        "task_id": "test-recovery-task",
        "last_error": "Element not found: #button",
        "current_step": {"id": 1, "agent": "browser", "action": "click_selector", "parameters": {"selector": "#button"}},
        "current_step_index": 0,
        "retry_count": 0,
        "max_retries": 2,
        "plan_steps": [{"id": 1, "agent": "browser", "action": "click_selector", "parameters": {"selector": "#button"}}]
    }

    # Attempt 1: Replanning provides a corrective step
    with patch("backend.app.agents.planner.PlannerAgent.replan_subgoal", new_callable=AsyncMock) as mock_replan:
        from backend.app.agents.models import TaskStep
        mock_replan.return_value = [
            TaskStep(id=1, agent="browser", action="scroll_page", description="Scroll down to find button", parameters={"delta_y": 300})
        ]
        res1 = await recovery_agent_node(state)
        assert res1["retry_count"] == 1
        assert res1["next_agent"] == "supervisor"
        assert len(res1["plan_steps"]) == 2  # corrective step prepended

    # Attempt 2: Exhaustion
    state["retry_count"] = 2
    res2 = await recovery_agent_node(state)
    assert res2["status"] == "failed"
    assert res2["next_agent"] == "END"


@pytest.mark.asyncio
async def test_parallel_research_fan_out():
    """
    Verify Supervisor detects parallel-safe steps and dispatches them in parallel.
    """
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title="Parallel Test Task", prompt="Gather research data")
        task_id = task.id

    checkpointer = get_checkpointer()
    compiled_graph = build_graph(checkpointer=checkpointer)
    thread_id = f"test-parallel-{task_id}"
    config = {"configurable": {"thread_id": thread_id}}

    # Two parallel-safe research steps with no mutual dependency
    parallel_steps = [
        {"id": 1, "agent": "researcher", "action": "search_web", "parameters": {"query": "Agentic AI"}, "dependencies": []},
        {"id": 2, "agent": "researcher", "action": "search_web", "parameters": {"query": "LangGraph multi-agent"}, "dependencies": []},
    ]

    initial_state: GraphState = {
        "task_id": task_id,
        "graph_thread_id": thread_id,
        "prompt": "Gather research data",
        "current_url": "about:blank",
        "task_type": "research",
        "plan_steps": parallel_steps,
        "current_step_index": 0,
        "total_steps": 2,
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

    with patch("backend.app.tools.executor.ToolExecutor.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"status": "success", "results": [{"title": "Test Result", "url": "https://example.com"}]}
        with patch.object(bridge, "call", new_callable=AsyncMock) as mock_bridge:
            mock_bridge.return_value = {"url": "about:blank", "title": "Research"}

            async for _ in compiled_graph.astream(initial_state, config=config, stream_mode="values"):
                pass

    final_snapshot = await compiled_graph.aget_state(config)
    assert final_snapshot.values.get("status") == "completed"
    # Both parallel results should have been accumulated in step_results via reducer
    assert len(final_snapshot.values.get("step_results", [])) >= 2
