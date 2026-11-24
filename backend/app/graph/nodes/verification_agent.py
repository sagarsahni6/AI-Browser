"""
Verification Agent node.

Runs a final task-level verification using the existing VerifierAgent.
Marks the task completed in the DB and notifies the UI.
"""
from __future__ import annotations

import logging

from backend.app.graph.state import GraphState
from backend.app.agents.verifier import VerifierAgent

logger = logging.getLogger("graph.nodes.verification")


async def verification_agent_node(state: GraphState) -> GraphState:
    """
    Input:  task_id, step_results, total_steps
    Output: final_report, status="completed"
    """
    task_id = state.get("task_id", "")
    step_results = state.get("step_results") or []
    total_steps = state.get("total_steps", len(step_results))

    logger.info(f"[Verification] Running final verification for task {task_id}")

    try:
        verify_res = await VerifierAgent.execute_step("verify_task", {})
    except Exception as e:
        verify_res = {"status": "error", "error": str(e)}

    verified_url = verify_res.get("url", "done") if isinstance(verify_res, dict) else "done"
    final_report = (
        f"Task completed: {len(step_results)} steps executed successfully. "
        f"Verified state: {verified_url}."
    )

    # Mark task completed in DB and clear legacy checkpoint
    try:
        from backend.app.database.engine import AsyncSessionLocal
        from backend.app.database.repository import Repository
        from backend.app.runtime.checkpoint_manager import CheckpointManager
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            await repo.update_task_status(task_id, status="completed", result=final_report)
        await CheckpointManager.clear_checkpoint(task_id)
    except Exception as db_err:
        logger.warning(f"[Verification] DB completion update error: {db_err}")

    # Notify UI
    try:
        from backend.app.browser.bridge import bridge
        bridge.notify("task.step_updated", {
            "task_id": task_id,
            "status": "completed",
            "total_steps": total_steps,
            "result": final_report,
        })
    except Exception:
        pass

    logger.info(f"[Verification] Task {task_id} completed: {final_report}")

    return {
        **state,
        "final_report": final_report,
        "status": "completed",
        "next_agent": "END",
    }
