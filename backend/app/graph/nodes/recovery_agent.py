"""
Recovery Agent node.

Wraps PlannerAgent.replan_subgoal() to generate corrective steps when a
specialist node fails.  Respects max_retries to prevent infinite loops.

If retries are exhausted, routes to END with status="failed".
"""
from __future__ import annotations

import logging
from typing import Dict, Any

from backend.app.graph.state import GraphState
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.models import TaskStep

logger = logging.getLogger("graph.nodes.recovery")


async def recovery_agent_node(state: GraphState) -> GraphState:
    """
    Input:  last_error, current_step, current_step_index, retry_count, plan_steps
    Output: updated plan_steps with corrective steps prepended, retry_count+1
    """
    task_id = state.get("task_id", "")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if retry_count >= max_retries:
        logger.error(f"[Recovery] Task {task_id}: max retries ({max_retries}) exhausted → failed")
        try:
            from backend.app.browser.bridge import bridge
            bridge.notify("task.step_updated", {
                "task_id": task_id,
                "status": "failed",
                "error": f"Max retries ({max_retries}) exhausted",
            })
        except Exception:
            pass
        return {
            **state,
            "status": "failed",
            "next_agent": "END",
        }

    failed_step_dict: Dict[str, Any] = state.get("current_step") or {}
    error_context = state.get("last_error", "Unknown error")
    idx = state.get("current_step_index", 0)
    remaining_dicts = state.get("plan_steps", [])[idx:]

    logger.warning(
        f"[Recovery] Task {task_id}: retry {retry_count + 1}/{max_retries} "
        f"for step action='{failed_step_dict.get('action')}', error='{error_context}'"
    )

    # Reconstruct TaskStep objects for PlannerAgent API
    try:
        failed_step = TaskStep(**{
            k: v for k, v in failed_step_dict.items()
            if k in TaskStep.model_fields
        }) if failed_step_dict else None
    except Exception:
        failed_step = None

    try:
        current_obs: Dict[str, Any] = {}
        try:
            from backend.app.browser.bridge import bridge
            current_obs = await bridge.call("browser.inspect", {}) or {}
        except Exception:
            pass

        remaining_steps_objs = []
        for s in remaining_dicts:
            try:
                remaining_steps_objs.append(TaskStep(**{
                    k: v for k, v in s.items() if k in TaskStep.model_fields
                }))
            except Exception:
                pass

        corrective_steps = await PlannerAgent.replan_subgoal(
            task_id=task_id,
            failed_step=failed_step,
            error_context=error_context,
            current_obs=current_obs,
            remaining_steps=remaining_steps_objs,
        )

        corrective_dicts = [s.model_dump() for s in corrective_steps]

        # Persist corrective steps to DB for UI visibility
        try:
            from backend.app.database.engine import AsyncSessionLocal
            from backend.app.database.repository import Repository
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                for cs in corrective_steps:
                    await repo.add_task_step(
                        task_id=task_id,
                        step_number=cs.id,
                        description=f"[{cs.agent.upper()}] {cs.description}",
                        tool_name=cs.action,
                        parameters=cs.parameters,
                    )
        except Exception as db_err:
            logger.warning(f"[Recovery] DB persistence error: {db_err}")

        # Prepend corrective steps, keep remaining originals
        new_plan = corrective_dicts + remaining_dicts
        return {
            **state,
            "plan_steps": new_plan,
            "current_step_index": 0,
            "retry_count": retry_count + 1,
            "last_error": None,
            "next_agent": "supervisor",
        }

    except Exception as e:
        logger.error(f"[Recovery] Replan failed: {e}")
        return {
            **state,
            "status": "failed",
            "last_error": f"Recovery replan failed: {e}",
            "next_agent": "END",
        }
