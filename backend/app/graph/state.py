"""
GraphState — the single TypedDict that flows through the LangGraph StateGraph.

Design rules:
  - All fields must be JSON-serialisable (LangGraph checkpoints them to SQLite).
  - Lists that accumulate across nodes use Annotated[List, reducer] so LangGraph
    merges parallel branch outputs correctly via add() semantics.
  - Approval-related fields are reset to None after each approval cycle so the
    same state shape handles multiple sequential approvals cleanly.
"""
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict


def _append_list(a: List[Any], b: List[Any]) -> List[Any]:
    """Smart reducer: avoids duplicating lists when nodes spread full state (**state)."""
    if not b:
        return a or []
    if not a:
        return b or []
    if a == b:
        return a
    if len(b) > len(a) and b[:len(a)] == a:
        return b
    return a + b


class GraphState(TypedDict, total=False):
    # ── Task identity ────────────────────────────────────────────────────────
    task_id: str
    graph_thread_id: str
    prompt: str
    current_url: str
    task_type: str  # vision | finance | tools | research

    # ── Plan ─────────────────────────────────────────────────────────────────
    plan_steps: List[Dict[str, Any]]           # List of TaskStep.model_dump()
    current_step_index: int
    total_steps: int
    # Annotated with reducer so parallel Send branches don't overwrite each other
    step_results: Annotated[List[Dict[str, Any]], _append_list]

    # ── Current step being executed ───────────────────────────────────────────
    current_step: Dict[str, Any]               # The TaskStep dict being processed

    # ── Routing ──────────────────────────────────────────────────────────────
    next_agent: str                            # target node name for routing
    parallel_sends: List[Dict[str, Any]]       # steps queued for parallel dispatch

    # ── Approval / HITL ──────────────────────────────────────────────────────
    approval_decision: Optional[bool]          # None=not set, True=approved, False=rejected
    approval_id: Optional[str]                 # DB approval_request.id

    # ── Error / Recovery ─────────────────────────────────────────────────────
    last_error: Optional[str]
    last_tool_result: Optional[Dict[str, Any]]
    retry_count: int
    max_retries: int

    # ── Final output ─────────────────────────────────────────────────────────
    final_report: Optional[str]
    status: str  # running | approval_required | completed | failed | cancelled
