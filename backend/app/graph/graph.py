"""
LangGraph StateGraph assembly.

Builds and compiles the full AI Browser agent graph with:
  - 14 nodes (intent_analyzer, planner, supervisor, security_approval,
    8 specialist agents, recovery_agent, verification_agent)
  - Conditional routing from supervisor and security_approval
  - Parallel Send()-based fan-out for independent safe steps
  - Persistent checkpointing via AsyncSqliteSaver

The compiled graph singleton is created lazily on first access.
Call rebuild_graph() after checkpointer is initialised.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Union

from langgraph.graph import StateGraph, END, START
from langgraph.types import Send

from backend.app.graph.state import GraphState
from backend.app.graph.nodes.intent_analyzer import intent_analyzer_node
from backend.app.graph.nodes.planner import planner_node
from backend.app.graph.nodes.supervisor import supervisor_node
from backend.app.graph.nodes.security_approval import security_approval_node
from backend.app.graph.nodes.specialist_agents import (
    browser_agent_node,
    dom_agent_node,
    vision_agent_node,
    research_agent_node,
    data_agent_node,
    desktop_agent_node,
    file_agent_node,
    memory_agent_node,
)
from backend.app.graph.nodes.recovery_agent import recovery_agent_node
from backend.app.graph.nodes.verification_agent import verification_agent_node

logger = logging.getLogger("graph.graph")

_compiled_graph = None  # module-level singleton


def _route_from_supervisor(state: GraphState) -> Union[str, List[Send]]:
    """
    Conditional edge from supervisor.
    Returns node name or list of Send() objects for parallel dispatch.
    """
    if state.get("status") in ("cancelled", "failed"):
        return END

    next_agent = state.get("next_agent", "END")

    if next_agent == "END":
        return END
    if next_agent == "verification_agent":
        return "verification_agent"
    if next_agent == "recovery_agent":
        return "recovery_agent"

    if next_agent == "parallel_dispatch":
        parallel_steps = state.get("parallel_sends") or []
        _PARALLEL_NODE_MAP = {
            "researcher": "research_agent",
            "research": "research_agent",
            "data": "data_agent",
            "data_agent": "data_agent",
            "file": "file_agent",
        }
        return [
            Send(
                _PARALLEL_NODE_MAP.get(s.get("agent", "researcher").lower(), "research_agent"),
                {**state, "current_step": s}
            )
            for s in parallel_steps
        ]

    # All specialist agents go through security_approval first
    _SPECIALIST_NODES = {
        "browser_agent", "dom_agent", "vision_agent", "research_agent",
        "data_agent", "desktop_agent", "file_agent", "memory_agent",
    }
    if next_agent in _SPECIALIST_NODES:
        return "security_approval"

    # Fallback
    return "security_approval"


def _route_from_approval(state: GraphState) -> str:
    """
    Conditional edge from security_approval.
    After execution (or approval grant), routes to the target specialist or back
    to supervisor.
    """
    if state.get("status") in ("cancelled", "failed"):
        return END

    next_agent = state.get("next_agent", "supervisor")
    if next_agent == "END":
        return END

    routing = {
        "browser_agent": "browser_agent",
        "dom_agent": "dom_agent",
        "vision_agent": "vision_agent",
        "research_agent": "research_agent",
        "data_agent": "data_agent",
        "desktop_agent": "desktop_agent",
        "file_agent": "file_agent",
        "memory_agent": "memory_agent",
        "supervisor": "supervisor",
        "recovery_agent": "recovery_agent",
        "END": END,
    }
    return routing.get(next_agent, "supervisor")


def _route_from_specialist(state: GraphState) -> str:
    """After a specialist node completes, always return to supervisor."""
    return "supervisor"


def _route_recovery(state: GraphState) -> str:
    """Recovery routes to supervisor to retry, or END on exhaustion."""
    if state.get("status") in ("failed", "cancelled"):
        return END
    return "supervisor"


def build_graph(checkpointer=None):
    """
    Build and compile the StateGraph.

    Args:
        checkpointer: AsyncSqliteSaver instance (required for persistence).
                      If None, compiles without persistence (for unit tests).
    """
    g = StateGraph(GraphState)

    # ── Register nodes ────────────────────────────────────────────────────────
    g.add_node("intent_analyzer", intent_analyzer_node)
    g.add_node("planner", planner_node)
    g.add_node("supervisor", supervisor_node)
    g.add_node("security_approval", security_approval_node)
    g.add_node("browser_agent", browser_agent_node)
    g.add_node("dom_agent", dom_agent_node)
    g.add_node("vision_agent", vision_agent_node)
    g.add_node("research_agent", research_agent_node)
    g.add_node("data_agent", data_agent_node)
    g.add_node("desktop_agent", desktop_agent_node)
    g.add_node("file_agent", file_agent_node)
    g.add_node("memory_agent", memory_agent_node)
    g.add_node("recovery_agent", recovery_agent_node)
    g.add_node("verification_agent", verification_agent_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    g.add_edge(START, "intent_analyzer")
    g.add_edge("intent_analyzer", "planner")
    g.add_edge("planner", "supervisor")

    # ── Supervisor → specialist (via security) or terminal ────────────────────
    g.add_conditional_edges(
        "supervisor",
        _route_from_supervisor,
        {
            "security_approval": "security_approval",
            "recovery_agent": "recovery_agent",
            "verification_agent": "verification_agent",
            "research_agent": "research_agent",
            "data_agent": "data_agent",
            "file_agent": "file_agent",
            END: END,
        },
    )

    # ── Security approval → specialist or back to supervisor ──────────────────
    g.add_conditional_edges(
        "security_approval",
        _route_from_approval,
        {
            "browser_agent": "browser_agent",
            "dom_agent": "dom_agent",
            "vision_agent": "vision_agent",
            "research_agent": "research_agent",
            "data_agent": "data_agent",
            "desktop_agent": "desktop_agent",
            "file_agent": "file_agent",
            "memory_agent": "memory_agent",
            "supervisor": "supervisor",
            "recovery_agent": "recovery_agent",
            END: END,
        },
    )

    # ── Specialist agents → supervisor ────────────────────────────────────────
    for specialist in [
        "browser_agent", "dom_agent", "vision_agent", "research_agent",
        "data_agent", "desktop_agent", "file_agent", "memory_agent",
    ]:
        g.add_edge(specialist, "supervisor")

    # ── Recovery → supervisor or END ──────────────────────────────────────────
    g.add_conditional_edges(
        "recovery_agent",
        _route_recovery,
        {"supervisor": "supervisor", END: END},
    )

    # ── Verification → END ────────────────────────────────────────────────────
    g.add_edge("verification_agent", END)

    logger.info("Compiling LangGraph StateGraph...")
    compiled = g.compile(checkpointer=checkpointer, interrupt_before=[])
    logger.info("LangGraph StateGraph compiled successfully.")
    return compiled


def rebuild_graph() -> None:
    """Rebuild the compiled graph using the current checkpointer (call after init)."""
    global _compiled_graph
    from backend.app.graph.checkpointer import get_checkpointer
    _compiled_graph = build_graph(checkpointer=get_checkpointer())
    logger.info("LangGraph compiled graph (re)built with checkpointer.")


def get_graph():
    """Return the compiled graph singleton. Must have called rebuild_graph() first."""
    if _compiled_graph is None:
        raise RuntimeError(
            "LangGraph graph not compiled. Call rebuild_graph() during FastAPI lifespan startup."
        )
    return _compiled_graph
