"""
Planner node.

Delegates to the existing PlannerAgent.create_plan() — no logic duplication.
Converts TaskPlan into serialisable dicts stored in GraphState.plan_steps.
"""
from __future__ import annotations

import logging
from backend.app.graph.state import GraphState
from backend.app.agents.planner import PlannerAgent

logger = logging.getLogger("graph.nodes.planner")


async def planner_node(state: GraphState) -> GraphState:
    """
    Input:  prompt, current_url, task_id
    Output: plan_steps (list of TaskStep dicts), total_steps, current_step_index=0, next_agent="supervisor"
    """
    task_id = state["task_id"]
    prompt = state.get("prompt", "")
    current_url = state.get("current_url", "about:blank")

    # If steps are already pre-planned (e.g. injected by workflow or test), preserve them
    existing_steps = state.get("plan_steps")
    if existing_steps and len(existing_steps) > 0:
        logger.info(f"[Planner] Using pre-existing {len(existing_steps)} plan steps for task {task_id}")
        return {
            **state,
            "total_steps": len(existing_steps),
            "current_step_index": 0,
            "next_agent": "supervisor",
        }

    logger.info(f"[Planner] Creating plan for task {task_id}: {prompt[:60]}")

    try:
        plan = await PlannerAgent.create_plan(
            task_id=task_id,
            prompt=prompt,
            current_url=current_url,
        )
        steps = [s.model_dump() for s in plan.steps]
        logger.info(f"[Planner] Created {len(steps)}-step plan for task {task_id}")

        # Persist steps to DB for UI visibility (same as legacy supervisor)
        try:
            from backend.app.database.engine import AsyncSessionLocal
            from backend.app.database.repository import Repository
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                for step in plan.steps:
                    await repo.add_task_step(
                        task_id=task_id,
                        step_number=step.id,
                        description=f"[{step.agent.upper()}] {step.description}",
                        tool_name=step.action,
                        parameters=step.parameters,
                    )
        except Exception as db_err:
            logger.warning(f"[Planner] DB step persistence error (non-fatal): {db_err}")

        return {
            **state,
            "plan_steps": steps,
            "total_steps": len(steps),
            "current_step_index": 0,
            "next_agent": "supervisor",
        }

    except Exception as e:
        logger.error(f"[Planner] Planning failed for task {task_id}: {e}")
        return {
            **state,
            "last_error": f"Planning failed: {e}",
            "status": "failed",
            "next_agent": "END",
        }
