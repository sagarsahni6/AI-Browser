import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.app.database.engine import AsyncSessionLocal, init_db
from backend.app.database.repository import Repository
from backend.app.graph.state import GraphState
from backend.app.graph.adapter import NimChatModel
from backend.app.graph.nodes.intent_analyzer import intent_analyzer_node
from backend.app.graph.nodes.planner import planner_node
from backend.app.graph.nodes.supervisor import supervisor_node
from backend.app.graph.nodes.specialist_agents import browser_agent_node
from backend.app.graph.nodes.verification_agent import verification_agent_node
from backend.app.graph.graph import build_graph
from backend.app.graph.checkpointer import init_checkpointer, close_checkpointer, get_checkpointer
from backend.app.browser.bridge import bridge


@pytest.fixture(autouse=True)
async def setup_db_and_checkpointer():
    await init_db()
    # Use in-memory or temp sqlite checkpointer for tests
    await init_checkpointer("sqlite+aiosqlite:///:memory:")
    yield
    await close_checkpointer()


@pytest.mark.asyncio
async def test_intent_analyzer_node():
    # 1. Vision intent
    state_vision: GraphState = {"prompt": "Look at the candlestick chart and analyze patterns"}
    res_vision = await intent_analyzer_node(state_vision)
    assert res_vision["task_type"] == "vision"
    assert res_vision["next_agent"] == "planner"

    # 2. Finance intent
    state_finance: GraphState = {"prompt": "Calculate option chain greeks for Nifty 24000 strike"}
    res_finance = await intent_analyzer_node(state_finance)
    assert res_finance["task_type"] == "finance"

    # 3. Research intent
    state_research: GraphState = {"prompt": "Research and summarize recent multimodal browser agents"}
    res_research = await intent_analyzer_node(state_research)
    assert res_research["task_type"] == "research"

    # 4. Standard tools intent
    state_tools: GraphState = {"prompt": "Navigate to google.com and search for weather"}
    res_tools = await intent_analyzer_node(state_tools)
    assert res_tools["task_type"] == "tools"
    assert res_tools["status"] == "running"


@pytest.mark.asyncio
async def test_nim_chat_model_adapter():
    from langchain_core.messages import HumanMessage, SystemMessage

    adapter = NimChatModel(task_type="tools")
    assert adapter._llm_type == "nim_chat_model"

    # Test tool binding
    dummy_tools = [{"type": "function", "function": {"name": "test_tool", "parameters": {}}}]
    bound = adapter.bind_tools(dummy_tools)
    assert len(bound._bound_tools) == 1
    assert bound._bound_tools[0]["function"]["name"] == "test_tool"

    # Test message generation with mocked provider
    with patch("backend.app.ai.router.ModelRouter.route_for_task") as mock_route:
        mock_provider = AsyncMock()
        mock_result = MagicMock()
        mock_result.content = "LangGraph NimChatModel test output"
        mock_result.tool_calls = None
        mock_result.finish_reason = "stop"
        mock_result.usage = {"total_tokens": 42}
        mock_provider.chat_completion.return_value = mock_result
        mock_route.return_value = (mock_provider, "mock-model")

        messages = [
            SystemMessage(content="You are a test assistant"),
            HumanMessage(content="Hello via LangGraph adapter"),
        ]

        chat_result = await adapter._agenerate(messages)
        assert len(chat_result.generations) == 1
        gen = chat_result.generations[0]
        assert gen.message.content == "LangGraph NimChatModel test output"


@pytest.mark.asyncio
async def test_langgraph_core_pipeline_execution():
    """
    Tests full pipeline from start to completion:
    IntentAnalyzer -> Planner -> Supervisor -> BrowserAgent -> VerificationAgent -> END
    """
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title="Core Test Task", prompt="Navigate to https://example.com and inspect")
        task_id = task.id

    checkpointer = get_checkpointer()
    compiled_graph = build_graph(checkpointer=checkpointer)

    thread_id = f"test-thread-{task_id}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: GraphState = {
        "task_id": task_id,
        "graph_thread_id": thread_id,
        "prompt": "Navigate to https://example.com and inspect",
        "current_url": "about:blank",
        "task_type": "tools",
        "plan_steps": [],
        "current_step_index": 0,
        "total_steps": 0,
        "step_results": [],
        "current_step": {},
        "next_agent": "intent_analyzer",
        "approval_decision": None,
        "approval_id": None,
        "last_error": None,
        "last_tool_result": None,
        "retry_count": 0,
        "max_retries": 3,
        "final_report": None,
        "status": "running",
    }

    # Mock browser bridge calls
    with patch.object(bridge, "call", new_callable=AsyncMock) as mock_bridge_call:
        mock_bridge_call.return_value = {"url": "https://example.com", "title": "Example Domain"}

        # Stream graph execution to completion
        final_state = None
        async for event in compiled_graph.astream(initial_state, config=config, stream_mode="values"):
            final_state = event

        assert final_state is not None
        assert final_state.get("status") == "completed"
        assert final_state.get("final_report") is not None
        assert len(final_state.get("step_results", [])) > 0

        # Verify state was checkpointed in sqlite
        saved_state = await compiled_graph.aget_state(config)
        assert saved_state is not None
        assert saved_state.values.get("status") == "completed"
