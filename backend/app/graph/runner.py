"""
GraphRunner — public API surface consumed by main.py.

Mirrors the SupervisorAgent interface so the existing RPC handlers in
main.py need only minimal changes:
  - GraphRunner.run_task(task_id)
  - GraphRunner.resume_approved_task(task_id, approval_id, decision)
  - GraphRunner.cancel_task(task_id)

Task lifecycle tracking:
  - tasks.graph_thread_id  → LangGraph thread config key
  - tasks.lg_checkpoint_id → last checkpoint ID (updated after each node)
  - tasks.status           → mirrors graph state status
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from backend.app.graph.state import GraphState

logger = logging.getLogger("graph.runner")

# In-memory set for cooperative cancellation (mirrors SupervisorAgent pattern)
_cancelled_tasks: set = set()


class GraphRunner:

    # ── Lifecycle control (class-level, same pattern as SupervisorAgent) ──────

    @classmethod
    def cancel_task(cls, task_id: str) -> None:
        logger.info(f"[GraphRunner] Cancellation requested for task {task_id}")
        _cancelled_tasks.add(task_id)

    @classmethod
    def _cleanup(cls, task_id: str) -> None:
        _cancelled_tasks.discard(task_id)

    # ── Main entry points ─────────────────────────────────────────────────────

    @classmethod
    async def run_task(cls, task_id: str) -> None:
        """
        Start a new graph-driven task.
        Called via asyncio.create_task() from handle_tasks_create.
        """
        from backend.app.graph.graph import get_graph
        from backend.app.database.engine import AsyncSessionLocal
        from backend.app.database.repository import Repository
        from backend.app.browser.bridge import bridge

        cls._cleanup(task_id)
        graph = get_graph()
        thread_id = f"lg-{task_id}"

        # Fetch task from DB
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            task = await repo.get_task(task_id)
            if not task:
                logger.error(f"[GraphRunner] Task {task_id} not found in DB")
                return
            await repo.update_task_status(task_id, status="running")
            await repo.update_task_graph_ids(task_id, graph_thread_id=thread_id)

        # Read current browser URL
        current_url = "about:blank"
        try:
            obs = await bridge.call("browser.inspect", {})
            if obs:
                current_url = obs.get("url", "about:blank")
        except Exception:
            pass

        initial_state: GraphState = {
            "task_id": task_id,
            "graph_thread_id": thread_id,
            "prompt": task.prompt,
            "current_url": current_url,
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

        config = {"configurable": {"thread_id": thread_id}}

        try:
            logger.info(f"[GraphRunner] Starting graph for task {task_id} (thread={thread_id})")
            async for event in graph.astream(initial_state, config=config, stream_mode="values"):
                if task_id in _cancelled_tasks:
                    logger.info(f"[GraphRunner] Task {task_id} cancelled mid-stream")
                    break
                _handle_stream_event(task_id, event)

        except Exception as e:
            logger.error(f"[GraphRunner] Graph execution error for task {task_id}: {e}", exc_info=True)
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.update_task_status(task_id, status="failed", error=str(e))
            try:
                bridge.notify("task.step_updated", {
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(e),
                })
            except Exception:
                pass
        finally:
            cls._cleanup(task_id)

    @classmethod
    async def resume_approved_task(
        cls,
        task_id: str,
        approval_id: Optional[str] = None,
        decision: bool = True,
    ) -> Dict[str, Any]:
        """
        Resume a graph paused at interrupt() after user approval/rejection.
        Called from handle_tasks_approve / handle_tasks_reject in main.py.
        """
        from langgraph.types import Command
        from backend.app.graph.graph import get_graph
        from backend.app.database.engine import AsyncSessionLocal
        from backend.app.database.repository import Repository
        from backend.app.browser.bridge import bridge

        graph = get_graph()

        # Fetch task + thread ID
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            task = await repo.get_task(task_id)
            if not task:
                return {"status": "error", "error": "Task not found", "id": task_id}
            if not task.graph_thread_id:
                # Not a LangGraph task — caller should fall back to SupervisorAgent
                return {"status": "not_langgraph"}

            # Validate approval record
            appr = None
            if approval_id:
                appr = await repo.get_approval_request(approval_id)
            if not appr:
                appr = await repo.get_pending_approval_for_task(task_id)

            if not appr or appr.status != "pending":
                return {
                    "status": "error",
                    "error": f"No pending approval found for task {task_id}",
                    "id": task_id,
                }

            # Update approval record
            await repo.update_approval_status(
                appr.id,
                status="approved" if decision else "rejected",
            )
            if decision:
                await repo.update_task_status(task_id, status="running")
            else:
                await repo.update_task_status(task_id, status="cancelled", error="Rejected by user")

        thread_id = task.graph_thread_id
        config = {"configurable": {"thread_id": thread_id}}

        if not decision:
            bridge_msg = {
                "task_id": task_id,
                "approval_id": appr.id,
                "status": "cancelled",
                "message": "Action rejected by user",
            }
            try:
                bridge.notify("task.step_updated", bridge_msg)
            except Exception:
                pass
            # Resume graph with False so security_approval_node routes to END
            asyncio.create_task(
                _resume_graph_async(task_id, graph, config, Command(resume=False))
            )
            return {"status": "rejected", "id": task_id, "approval_id": appr.id}

        # Approved — resume graph asynchronously
        logger.info(f"[GraphRunner] Resuming task {task_id} with approval_id={appr.id}")
        asyncio.create_task(
            _resume_graph_async(task_id, graph, config, Command(resume=True))
        )
        return {
            "status": "approved",
            "id": task_id,
            "approval_id": appr.id,
        }


async def _resume_graph_async(task_id: str, graph, config: dict, command) -> None:
    """
    Asynchronously resume a paused graph.  Runs in a background asyncio task
    so the approval HTTP response is not blocked.
    """
    from backend.app.database.engine import AsyncSessionLocal
    from backend.app.database.repository import Repository
    from backend.app.browser.bridge import bridge

    try:
        async for event in graph.astream(command, config=config, stream_mode="values"):
            _handle_stream_event(task_id, event)
    except Exception as e:
        logger.error(f"[GraphRunner] Resume error for task {task_id}: {e}", exc_info=True)
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            await repo.update_task_status(task_id, status="failed", error=str(e))
        try:
            bridge.notify("task.step_updated", {
                "task_id": task_id,
                "status": "failed",
                "error": str(e),
            })
        except Exception:
            pass


def _handle_stream_event(task_id: str, event: Any) -> None:
    """
    Process a streaming event emitted by graph.astream(stream_mode="values").
    In "values" mode, each event is the full current GraphState dict.
    """
    if not isinstance(event, dict):
        return

    status = event.get("status", "running")
    idx = event.get("current_step_index", 0)
    total = event.get("total_steps", 0)

    # Only notify on meaningful state changes (avoid spamming the UI)
    if status in ("completed", "failed", "cancelled", "approval_required"):
        try:
            from backend.app.browser.bridge import bridge
            bridge.notify("task.step_updated", {
                "task_id": task_id,
                "status": status,
                "step_index": idx,
                "total_steps": total,
                "result": event.get("final_report"),
                "error": event.get("last_error"),
            })
        except Exception:
            pass
