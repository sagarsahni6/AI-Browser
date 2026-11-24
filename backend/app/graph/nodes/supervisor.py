"""
Supervisor node.

The main dispatcher.  Reads the current step index, identifies which specialist
to route to, and decides whether to fan-out independent steps in parallel via
LangGraph Send() semantics.

Parallelism rule:
  Steps are considered parallelisable if:
    1. They are GREEN-tier (read-only, no side effects)
    2. They have no dependency on the step being dispatched simultaneously
    3. They are research_agent or data_agent actions
  All other steps are dispatched sequentially.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Union

from langgraph.types import Send

from backend.app.graph.state import GraphState
from backend.app.security.policy import SecurityPolicy, RiskTier

logger = logging.getLogger("graph.nodes.supervisor")

# Maps agent names from PlannerAgent output → LangGraph node names
_AGENT_NODE_MAP: Dict[str, str] = {
    "browser": "browser_agent",
    "browser_agent": "browser_agent",
    "dom": "dom_agent",
    "vision": "vision_agent",
    "researcher": "research_agent",
    "research": "research_agent",
    "data": "data_agent",
    "data_agent": "data_agent",
    "desktop": "desktop_agent",
    "file": "file_agent",
    "memory": "memory_agent",
    "recovery": "recovery_agent",
    "verifier": "verification_agent",
    "verification": "verification_agent",
}

# Agents that may execute in parallel (read-only, no approval needed)
_PARALLEL_SAFE_AGENTS = {"researcher", "research", "data", "data_agent", "file"}


def _is_parallel_safe(step: Dict[str, Any]) -> bool:
    agent = step.get("agent", "browser").lower()
    action = step.get("action", "")
    if agent not in _PARALLEL_SAFE_AGENTS:
        return False
    policy = SecurityPolicy.evaluate(action, step.get("parameters", {}))
    return policy.tier == RiskTier.GREEN


def _find_parallel_window(steps: List[Dict[str, Any]], start_idx: int) -> List[Dict[str, Any]]:
    """
    Look ahead from start_idx and collect a window of parallel-safe steps
    with no mutual dependency conflicts.  Returns 1 step if none qualify.
    """
    if start_idx >= len(steps):
        return []

    candidates = []
    for i in range(start_idx, min(start_idx + 4, len(steps))):  # max 4-way parallel
        step = steps[i]
        # Dependency check: step must not depend on any step in candidates
        deps = set(step.get("dependencies", []))
        candidate_ids = {c.get("id") for c in candidates}
        if deps & candidate_ids:
            break
        if _is_parallel_safe(step):
            candidates.append(step)
        else:
            break  # First non-safe step stops the window

    return candidates if len(candidates) > 1 else []


async def supervisor_node(state: GraphState) -> Union[GraphState, List[Send]]:
    """
    Input:  plan_steps, current_step_index, step_results, status
    Output: GraphState with next_agent set, OR list of Send() for parallel dispatch
    """
    steps = state.get("plan_steps", [])
    task_id = state.get("task_id", "")
    step_results = state.get("step_results") or []
    # Derive progress directly from executed results to maintain consistency across parallel fan-in
    idx = len(step_results)

    # Check if most recent step resulted in an error
    if step_results:
        last_res = step_results[-1]
        if isinstance(last_res, dict) and last_res.get("status") in ("error", "failed"):
            return {
                **state,
                "current_step_index": idx,
                "last_error": last_res.get("error", "Step failed"),
                "next_agent": "recovery_agent",
            }

    # All steps done → go to verification
    if idx >= len(steps):
        logger.info(f"[Supervisor] Task {task_id}: all {idx} steps complete → verification")
        return {**state, "current_step_index": idx, "next_agent": "verification_agent"}

    # Check for parallel window
    parallel_steps = _find_parallel_window(steps, idx)
    if parallel_steps:
        logger.info(
            f"[Supervisor] Task {task_id}: dispatching {len(parallel_steps)} steps in parallel "
            f"(indices {idx}..{idx + len(parallel_steps) - 1})"
        )
        return {
            **state,
            "next_agent": "parallel_dispatch",
            "parallel_sends": parallel_steps,
            "current_step_index": idx + len(parallel_steps),
        }

    # Sequential dispatch
    step = steps[idx]
    agent = step.get("agent", "browser").lower()
    target_node = _AGENT_NODE_MAP.get(agent, "browser_agent")

    logger.info(
        f"[Supervisor] Task {task_id}: step {idx+1}/{len(steps)} → "
        f"[{agent}] {step.get('action')} → {target_node}"
    )

    # Notify UI
    try:
        from backend.app.browser.bridge import bridge
        bridge.notify("task.step_updated", {
            "task_id": task_id,
            "step_id": step.get("id"),
            "step_number": step.get("id"),
            "total_steps": len(steps),
            "status": "running",
            "description": step.get("description", ""),
            "action": step.get("action", ""),
            "parameters": step.get("parameters", {}),
        })
    except Exception:
        pass

    return {**state, "next_agent": target_node, "current_step": step}
