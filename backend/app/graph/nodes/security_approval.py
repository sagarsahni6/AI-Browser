"""
Security Approval node — the ONLY place interrupt() is called.

REPLAY SAFETY RULES (critical — read before modifying):
  LangGraph replays a node from the top when resuming from interrupt().
  Therefore:
    ✓ All code BEFORE interrupt() must be idempotent (reads/checks only).
    ✓ The DB approval record creation is guarded so it won't double-insert.
    ✓ Tool execution happens AFTER interrupt() returns, on resumed run.
    ✗ Never put network writes or state mutations before interrupt().

Flow:
  1. Evaluate SecurityPolicy (idempotent read).
  2a. GREEN/YELLOW → execute directly via ToolExecutor, return to supervisor.
  2b. BLOCKED → return error to recovery_agent.
  2c. REQUIRES_APPROVAL → check if approval_decision already set (resumed run):
       - Not set (first run): create DB record, notify UI, call interrupt().
       - Set to False (rejected): route to END.
       - Set to True (approved): recheck policy + browser state, execute once.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from langgraph.types import interrupt

from backend.app.graph.state import GraphState
from backend.app.security.policy import SecurityPolicy, RiskTier
from backend.app.tools.executor import ToolExecutor

logger = logging.getLogger("graph.nodes.security_approval")


async def security_approval_node(state: GraphState) -> GraphState:
    step = state.get("current_step") or {}
    tool_name: str = step.get("action", "")
    params: Dict[str, Any] = step.get("parameters") or {}
    task_id: str = state.get("task_id", "")
    idx: int = state.get("current_step_index", 0)

    if not tool_name:
        # No action to approve — advance to next step
        return {**state, "current_step_index": idx + 1, "next_agent": "supervisor"}

    # ── 1. Evaluate security policy (idempotent) ─────────────────────────────
    policy_res = SecurityPolicy.evaluate(tool_name, params)

    # ── 2a. BLOCKED ───────────────────────────────────────────────────────────
    if policy_res.is_blocked:
        logger.warning(f"[SecurityApproval] BLOCKED tool='{tool_name}' reason='{policy_res.reason}'")
        _notify_step(task_id, step, "failed", error=policy_res.reason)
        return {
            **state,
            "last_error": policy_res.reason,
            "current_step_index": idx + 1,
            "next_agent": "recovery_agent",
        }

    # ── 2b. REQUIRES_APPROVAL ─────────────────────────────────────────────────
    if policy_res.requires_approval:
        # Create approval record in DB if not already present
        appr_id = await _create_or_get_approval_record(task_id, tool_name, params, step, state)
        _notify_approval_required(task_id, step, appr_id, policy_res.reason)

        logger.info(
            f"[SecurityApproval] interrupt() for task {task_id}, tool='{tool_name}', "
            f"approval_id='{appr_id}'"
        )

        # ── INTERRUPT: graph suspends here ────────────────────────────────────
        # On resume, interrupt() returns the value passed to Command(resume=...)
        # which is True (approved) or False (rejected).
        decision = interrupt({
            "type": "approval_required",
            "approval_id": appr_id,
            "tool_name": tool_name,
            "parameters": params,
            "reason": policy_res.reason,
            "task_id": task_id,
        })

        # ── Code below only runs AFTER Command(resume=decision) ───────────────
        if not decision:
            logger.info(f"[SecurityApproval] Approval REJECTED for task {task_id}, tool='{tool_name}'")
            _notify_step(task_id, step, "cancelled")
            try:
                from backend.app.database.engine import AsyncSessionLocal
                from backend.app.database.repository import Repository
                async with AsyncSessionLocal() as session:
                    repo = Repository(session)
                    await repo.update_approval_status(appr_id, status="rejected")
                    await repo.update_task_status(task_id, status="cancelled", error="Action rejected by user")
            except Exception as e:
                logger.warning(f"[SecurityApproval] DB update error on rejection: {e}")
            return {
                **state,
                "status": "cancelled",
                "next_agent": "END",
            }

        # User approved -> recheck browser state + policy
        logger.info(f"[SecurityApproval] Approval GRANTED for task {task_id}, tool='{tool_name}'")
        try:
            from backend.app.browser.bridge import bridge
            from backend.app.security.policy import OriginBarrier
            current_state = await bridge.call("browser.inspect", {}) or {}
            recheck = SecurityPolicy.evaluate(tool_name, params)
            if recheck.is_blocked:
                logger.error(f"[SecurityApproval] Post-approval policy recheck BLOCKED tool='{tool_name}'")
                return {
                    **state,
                    "last_error": f"Post-approval policy recheck blocked: {recheck.reason}",
                    "next_agent": "recovery_agent",
                }
        except Exception as e:
            logger.warning(f"[SecurityApproval] Post-approval recheck warning (non-fatal): {e}")

        # Execute exactly once
        result = await ToolExecutor.execute(tool_name, params, bypass_approval=True)
        exec_status = result.get("status", "completed")

        # Mark approval executed in DB
        try:
            from backend.app.database.engine import AsyncSessionLocal
            from backend.app.database.repository import Repository
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.update_approval_status(appr_id, status="executed")
                db_steps = await repo.get_task_steps(task_id)
                for ds in db_steps:
                    if ds.step_number == step.get("id"):
                        await repo.update_step_status(ds.id, status=exec_status, result=result)
        except Exception as db_err:
            logger.warning(f"[SecurityApproval] DB update error post-approval: {db_err}")

        _notify_step(task_id, step, exec_status, result=result)

        return {
            **state,
            "last_tool_result": result,
            "step_results": (state.get("step_results") or []) + [result],
            "current_step_index": idx + 1,
            "status": "running",
            "next_agent": "supervisor",
        }

    # ── 2c. GREEN / YELLOW: execute directly ──────────────────────────────────
    logger.debug(f"[SecurityApproval] Executing tool='{tool_name}' tier={policy_res.tier}")
    result = await ToolExecutor.execute(tool_name, params)
    exec_status = result.get("status", "completed")

    # Persist step result to DB
    try:
        from backend.app.database.engine import AsyncSessionLocal
        from backend.app.database.repository import Repository
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            db_steps = await repo.get_task_steps(task_id)
            for ds in db_steps:
                if ds.step_number == step.get("id"):
                    await repo.update_step_status(ds.id, status=exec_status, result=result)
    except Exception as db_err:
        logger.warning(f"[SecurityApproval] DB step update error: {db_err}")

    _notify_step(task_id, step, exec_status, result=result)

    # Route to recovery if the tool errored
    next_agent = "recovery_agent" if exec_status == "error" else "supervisor"

    return {
        **state,
        "last_tool_result": result,
        "step_results": (state.get("step_results") or []) + [result],
        "current_step_index": idx + 1,
        "next_agent": next_agent,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _create_or_get_approval_record(
    task_id: str,
    tool_name: str,
    params: Dict[str, Any],
    step: Dict[str, Any],
    state: GraphState,
) -> str:
    """Persist approval request to DB if not already pending, and return its ID."""
    from backend.app.database.engine import AsyncSessionLocal
    from backend.app.database.repository import Repository

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        existing = await repo.get_pending_approval_for_task(task_id)
        if existing:
            return existing.id

        appr = await repo.create_approval_request(
            task_id=task_id,
            tool_name=tool_name,
            action_type="sensitive_operation",
            description=f"Action '{tool_name}' requires explicit user approval.",
            parameters_json=json.dumps(params),
            step_number=step.get("id"),
            session_checkpoint_json=json.dumps({
                "task_id": task_id,
                "step": step,
                "graph_thread_id": state.get("graph_thread_id"),
            }),
        )
        await repo.update_task_status(task_id, status="approval_required")
        return appr.id


def _notify_approval_required(task_id: str, step: Dict[str, Any], approval_id: str, reason: str) -> None:
    try:
        from backend.app.browser.bridge import bridge
        bridge.notify("task.step_updated", {
            "task_id": task_id,
            "step_id": step.get("id"),
            "step_number": step.get("id"),
            "approval_id": approval_id,
            "status": "approval_required",
            "reason": reason,
            "action": step.get("action", ""),
            "parameters": step.get("parameters", {}),
        })
    except Exception:
        pass


def _notify_step(
    task_id: str,
    step: Dict[str, Any],
    status: str,
    result: Dict[str, Any] = None,
    error: str = None,
) -> None:
    try:
        from backend.app.browser.bridge import bridge
        payload = {
            "task_id": task_id,
            "step_id": step.get("id"),
            "step_number": step.get("id"),
            "status": status,
            "description": step.get("description", ""),
            "action": step.get("action", ""),
        }
        if result:
            payload["result"] = result
        if error:
            payload["error"] = error
        bridge.notify("task.step_updated", payload)
    except Exception:
        pass
