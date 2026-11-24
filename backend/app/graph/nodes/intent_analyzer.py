"""
Intent Analyzer node.

Classifies the user's prompt into a task_type that informs model selection.
Pure NLP — no tool calls, no side effects, no LLM call needed (keyword matching
is fast and deterministic; can be upgraded to LLM-based later).
"""
from __future__ import annotations
from backend.app.graph.state import GraphState


async def intent_analyzer_node(state: GraphState) -> GraphState:
    """
    Input:  prompt, current_url
    Output: task_type, next_agent="planner"
    """
    prompt = (state.get("prompt") or "").lower()

    if any(k in prompt for k in ["chart", "candlestick", "tradingview", "visual", "look at", "see the", "screenshot"]):
        task_type = "vision"
    elif any(k in prompt for k in ["option chain", "finance", "calculate", "greeks", "strike", "iv ", "open interest"]):
        task_type = "finance"
    elif any(k in prompt for k in ["research", "summarize", "summary", "find papers", "search and report"]):
        task_type = "research"
    else:
        task_type = "tools"

    return {
        **state,
        "task_type": task_type,
        "next_agent": "planner",
        "status": "running",
        "retry_count": state.get("retry_count", 0),
        "max_retries": state.get("max_retries", 3),
        "step_results": state.get("step_results") or [],
        "plan_steps": state.get("plan_steps") or [],
        "current_step_index": 0,
        "approval_decision": None,
        "approval_id": None,
        "last_error": None,
        "last_tool_result": None,
    }
