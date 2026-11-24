import logging
import asyncio
import json
from typing import Dict, Any, Optional, List, Set
from backend.app.agents.models import TaskPlan, TaskStep, StepStatus
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.browser_agent import BrowserAgent
from backend.app.agents.researcher import ResearcherAgent
from backend.app.agents.data_agent import DataAgent
from backend.app.agents.verifier import VerifierAgent
from backend.app.agents.dom_agent import DOMAgent
from backend.app.agents.vision_agent import VisionAgent
from backend.app.agents.desktop_agent import DesktopAgent
from backend.app.agents.file_agent import FileAgent
from backend.app.agents.memory_agent import MemoryAgent
from backend.app.agents.recovery_agent import RecoveryAgent
from backend.app.runtime.checkpoint_manager import CheckpointManager
from backend.app.security.policy import OriginBarrier
from backend.app.tools.executor import ToolExecutor
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.repository import Repository
from backend.app.browser.bridge import bridge

logger = logging.getLogger("supervisor_agent")

class SupervisorAgent:
    """
    Central Coordinator of the Multi-Agent System.
    Orchestrates the complete lifecycle of an autonomous task with:
    1. Reactive step execution and dynamic re-planning on unexpected page states
    2. Cooperative cancellation and pause/resume checkpoints
    3. Live progress streaming via the JSON-RPC bridge
    4. Strict security approval gates with persistent checkpoint resumption
    5. Final post-action verification via VerifierAgent
    """
    _cancelled_tasks: Set[str] = set()
    _paused_tasks: Set[str] = set()

    @classmethod
    def cancel_task(cls, task_id: str):
        logger.info(f"Cancellation requested for task {task_id}")
        cls._cancelled_tasks.add(task_id)
        cls._paused_tasks.discard(task_id)

    @classmethod
    def pause_task(cls, task_id: str):
        logger.info(f"Pause requested for task {task_id}")
        cls._paused_tasks.add(task_id)

    @classmethod
    def resume_task(cls, task_id: str):
        logger.info(f"Resume requested for task {task_id}")
        cls._paused_tasks.discard(task_id)

    @classmethod
    def is_cancelled(cls, task_id: str) -> bool:
        return task_id in cls._cancelled_tasks

    @classmethod
    def is_paused(cls, task_id: str) -> bool:
        return task_id in cls._paused_tasks

    @classmethod
    def _cleanup_task(cls, task_id: str):
        cls._cancelled_tasks.discard(task_id)
        cls._paused_tasks.discard(task_id)

    @classmethod
    async def run_task(cls, task_id: str):
        logger.info(f"SupervisorAgent starting task {task_id}")
        cls._cleanup_task(task_id)

        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            task = await repo.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            await repo.update_task_status(task_id, status="running")

        plan: Optional[TaskPlan] = None
        try:
            # 1. Observe current browser state
            current_url = "about:blank"
            try:
                obs = await bridge.call("browser.inspect", {})
                if obs:
                    current_url = obs.get("url", "about:blank")
            except Exception:
                pass

            # 2. Planning Phase
            plan = await PlannerAgent.create_plan(task_id, task.prompt, current_url)

            # Record initial plan steps in database
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                for step in plan.steps:
                    await repo.add_task_step(
                        task_id=task_id,
                        step_number=step.id,
                        description=f"[{step.agent.upper()}] {step.description}",
                        tool_name=step.action,
                        parameters=step.parameters
                    )

            # 3. Execution Phase: dynamic reactive step queue
            remaining_steps: List[TaskStep] = list(plan.steps)
            total_steps = len(plan.steps) if plan else 0
            await cls._execute_steps_loop(task_id, remaining_steps, step_results=[], total_steps=total_steps)

        except Exception as e:
            logger.error(f"SupervisorAgent failed task {task_id}: {e}")
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.update_task_status(task_id, status="failed", error=str(e))
            try:
                bridge.notify("task.step_updated", {
                    "task_id": task_id,
                    "status": "failed",
                    "total_steps": len(plan.steps) if (plan and hasattr(plan, "steps")) else 0,
                    "error": str(e)
                })
            except Exception:
                pass
        finally:
            cls._cleanup_task(task_id)

    @classmethod
    async def _execute_steps_loop(
        cls,
        task_id: str,
        remaining_steps: List[TaskStep],
        step_results: List[Any],
        total_steps: int
    ) -> Dict[str, Any]:
        """
        Executes queued steps sequentially, handling pause/cancellation,
        security approval pauses with checkpoint serialization, self-healing retries,
        and final verification upon completion.
        """
        step_retries: Dict[int, int] = {}
        max_retries_per_step = 3

        while remaining_steps:
            # A. Check cooperative cancellation
            if cls.is_cancelled(task_id):
                logger.info(f"Task {task_id} aborted by user cancellation")
                async with AsyncSessionLocal() as session:
                    repo = Repository(session)
                    await repo.update_task_status(task_id, status="cancelled", error="Cancelled by user")
                try:
                    bridge.notify("task.step_updated", {
                        "task_id": task_id,
                        "status": "cancelled",
                        "message": "Task cancelled by user",
                        "total_steps": total_steps
                    })
                except Exception:
                    pass
                cls._cleanup_task(task_id)
                return {"status": "cancelled", "task_id": task_id}

            # B. Check cooperative pause
            if cls.is_paused(task_id):
                logger.info(f"Task {task_id} is paused; waiting for resume...")
                async with AsyncSessionLocal() as session:
                    repo = Repository(session)
                    await repo.update_task_status(task_id, status="paused")
                try:
                    bridge.notify("task.step_updated", {
                        "task_id": task_id,
                        "status": "paused",
                        "message": "Task paused",
                        "total_steps": total_steps
                    })
                except Exception:
                    pass

                while cls.is_paused(task_id):
                    if cls.is_cancelled(task_id):
                        break
                    await asyncio.sleep(0.4)

                if cls.is_cancelled(task_id):
                    continue

                # Resumed
                async with AsyncSessionLocal() as session:
                    repo = Repository(session)
                    await repo.update_task_status(task_id, status="running")

            # C. Pop next step from queue
            step = remaining_steps.pop(0)
            logger.info(f"Executing Step {step.id}: [{step.agent}] {step.action}")

            # Notify UI of step start
            try:
                bridge.notify("task.step_updated", {
                    "task_id": task_id,
                    "step_id": step.id,
                    "step_number": step.id,
                    "total_steps": total_steps,
                    "status": "running",
                    "description": step.description,
                    "action": step.action,
                    "parameters": step.parameters
                })
            except Exception:
                pass

            # D. Dispatch step to specialist agent
            result: Dict[str, Any] = {}
            agent_name = (step.agent or "browser").lower()
            if agent_name == "browser":
                result = await BrowserAgent.execute_step(step.action, step.parameters)
            elif agent_name == "dom":
                result = await DOMAgent.execute_step(step.action, step.parameters)
            elif agent_name == "vision":
                result = await VisionAgent.execute_step(step.action, step.parameters)
            elif agent_name == "desktop":
                result = await DesktopAgent.execute_step(step.action, step.parameters)
            elif agent_name == "file":
                result = await FileAgent.execute_step(step.action, step.parameters)
            elif agent_name == "memory":
                result = await MemoryAgent.execute_step(step.action, step.parameters)
            elif agent_name == "recovery":
                result = await RecoveryAgent.execute_step(step.action, step.parameters)
            elif agent_name == "researcher":
                result = await ResearcherAgent.execute_step(step.action, step.parameters)
            elif agent_name == "data":
                result = await DataAgent.execute_step(step.action, step.parameters)
            elif agent_name == "verifier":
                result = await VerifierAgent.execute_step(step.action, step.parameters)
            else:
                result = await BrowserAgent.execute_step(step.action, step.parameters)

            step_results.append(result)
            step_status = result.get("status", "completed")

            # Execute objective verification strategy if defined and step succeeded
            v_strat = getattr(step, "verification_strategy", "none")
            if v_strat and v_strat != "none" and step_status in ("completed", "success"):
                v_params = dict(getattr(step, "verification_params", {}) or {})
                if "expected_url_pattern" in v_params and "pattern" not in v_params:
                    v_params["pattern"] = v_params["expected_url_pattern"]
                if "records" not in v_params and "data" not in v_params:
                    v_params["records"] = result.get("result") or result.get("data") or []

                if v_strat == "dom_assertion":
                    v_res = await VerifierAgent.verify_dom_assertion(v_params)
                elif v_strat == "url_match":
                    v_res = await VerifierAgent.verify_url_match(v_params)
                elif v_strat == "data_validation":
                    v_res = VerifierAgent.verify_data_validation(v_params)
                elif v_strat == "file_validation":
                    v_res = VerifierAgent.verify_file_validation(v_params)
                elif v_strat == "form_submission":
                    v_res = await VerifierAgent.verify_form_submission(v_params)
                else:
                    v_res = {"verified": True}

                if not v_res.get("verified", True):
                    logger.warning(f"Step {step.id} objective verification failed: {v_res.get('reason')}")
                    step_status = "failed"
                    result["status"] = "failed"
                    result["error"] = f"Objective verification failed: {v_res.get('reason')}"

            # E. Update step in DB
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                db_steps = await repo.get_task_steps(task_id)
                for ds in db_steps:
                    if ds.step_number == step.id:
                        await repo.update_step_status(
                            ds.id,
                            status=step_status,
                            result=result
                        )

            # F. Handle security approval requirement: persist checkpoint and pause
            if step_status == "approval_required":
                logger.warning(f"Step {step.id} requires user approval: {result.get('reason')}")
                current_origin_url = None
                try:
                    obs_url = await bridge.call("browser.inspect", {})
                    if obs_url:
                        current_origin_url = obs_url.get("url")
                except Exception:
                    pass

                checkpoint_payload = {
                    "task_id": task_id,
                    "step_number": step.id,
                    "step": step.model_dump() if hasattr(step, "model_dump") else step.dict(),
                    "remaining_steps": [s.model_dump() if hasattr(s, "model_dump") else s.dict() for s in remaining_steps],
                    "step_results": step_results,
                    "total_steps": total_steps,
                    "origin_url": current_origin_url
                }
                checkpoint_json = json.dumps(checkpoint_payload)
                await CheckpointManager.save_checkpoint(task_id, step.id, checkpoint_payload)

                appr_id = None
                async with AsyncSessionLocal() as session:
                    repo = Repository(session)
                    await repo.update_task_status(task_id, status="approval_required", result=result.get("reason"))
                    appr = await repo.create_approval_request(
                        task_id=task_id,
                        tool_name=step.action,
                        action_type="sensitive_operation",
                        description=result.get("reason", "Action requires user confirmation"),
                        parameters_json=json.dumps(step.parameters),
                        step_number=step.id,
                        session_checkpoint_json=checkpoint_json
                    )
                    appr_id = appr.id

                try:
                    bridge.notify("task.step_updated", {
                        "task_id": task_id,
                        "step_id": step.id,
                        "step_number": step.id,
                        "approval_id": appr_id,
                        "total_steps": total_steps,
                        "status": "approval_required",
                        "reason": result.get("reason"),
                        "action": step.action,
                        "parameters": step.parameters
                    })
                except Exception:
                    pass
                return {
                    "status": "approval_required",
                    "task_id": task_id,
                    "approval_id": appr_id,
                    "step_number": step.id,
                    "reason": result.get("reason")
                }

            # G. Reactive self-correction & dynamic re-planning on step error
            if step_status == "error":
                retries = step_retries.get(step.id, 0)
                if retries < max_retries_per_step:
                    step_retries[step.id] = retries + 1
                    logger.warning(f"Step {step.id} failed ({result.get('error')}). Re-planning corrective steps (attempt {retries + 1}/{max_retries_per_step})...")

                    current_obs: Dict[str, Any] = {}
                    try:
                        current_obs = await bridge.call("browser.inspect", {}) or {}
                    except Exception:
                        pass

                    corrective_steps = await PlannerAgent.replan_subgoal(
                        task_id=task_id,
                        failed_step=step,
                        error_context=str(result.get("error", "Action error")),
                        current_obs=current_obs,
                        remaining_steps=remaining_steps
                    )

                    if corrective_steps:
                        async with AsyncSessionLocal() as session:
                            repo = Repository(session)
                            for cs in corrective_steps:
                                await repo.add_task_step(
                                    task_id=task_id,
                                    step_number=cs.id,
                                    description=f"[{cs.agent.upper()}] {cs.description}",
                                    tool_name=cs.action,
                                    parameters=cs.parameters
                                )
                        remaining_steps = corrective_steps + remaining_steps
                        try:
                            bridge.notify("task.step_updated", {
                                "task_id": task_id,
                                "step_id": step.id,
                                "total_steps": total_steps,
                                "status": "recovering",
                                "message": f"Self-correcting step failure (attempt {retries + 1})",
                                "error": result.get("error")
                            })
                        except Exception:
                            pass
                        continue

            # Notify UI of completed step
            try:
                bridge.notify("task.step_updated", {
                    "task_id": task_id,
                    "step_id": step.id,
                    "step_number": step.id,
                    "total_steps": total_steps,
                    "status": step_status,
                    "description": step.description,
                    "result": result
                })
            except Exception:
                pass

            await asyncio.sleep(0.3)

        # 4. Final verification
        verify_res = await VerifierAgent.execute_step("verify_task", {})

        # 5. Mark task completed
        await CheckpointManager.clear_checkpoint(task_id)
        final_report = f"Task completed: {len(step_results)} steps executed successfully. Verified state: {verify_res.get('url', 'done')}."
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            await repo.update_task_status(task_id, status="completed", result=final_report)

        logger.info(f"Task {task_id} completed successfully")
        try:
            bridge.notify("task.step_updated", {
                "task_id": task_id,
                "status": "completed",
                "total_steps": total_steps,
                "result": final_report
            })
        except Exception:
            pass

        return {
            "status": "completed",
            "task_id": task_id,
            "results": step_results,
            "final_report": final_report
        }

    @classmethod
    async def resume_approved_task(
        cls,
        task_id: str,
        approval_id: Optional[str] = None,
        decision: bool = True
    ) -> Dict[str, Any]:
        """
        Resumes a paused task upon user approval or rejection.
        - Validates pending approval in database.
        - If decision is False: marks approval rejected, updates task status to cancelled.
        - If decision is True: marks approval approved, revalidates browser state via bridge browser.inspect,
          executes the approved tool action exactly once via ToolExecutor, marks approval executed,
          restores checkpoint from session_checkpoint_json, and resumes the task execution loop from step_number + 1.
        """
        logger.info(f"SupervisorAgent resuming approved task {task_id} (approval_id={approval_id}, decision={decision})")
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            appr = None
            if approval_id:
                appr = await repo.get_approval_request(approval_id)
            if not appr:
                appr = await repo.get_pending_approval_for_task(task_id)

            if not appr or appr.status != "pending":
                logger.warning(f"No pending approval request found for task {task_id} (approval_id={approval_id})")
                return {
                    "status": "error",
                    "id": task_id,
                    "error": f"No pending approval request found for task {task_id}"
                }

            if not decision:
                await repo.update_approval_status(appr.id, status="rejected")
                await repo.update_task_status(task_id, status="cancelled", error="Action rejected by user")
                try:
                    bridge.notify("task.step_updated", {
                        "task_id": task_id,
                        "approval_id": appr.id,
                        "status": "cancelled",
                        "message": "Action rejected by user"
                    })
                except Exception:
                    pass
                cls._cleanup_task(task_id)
                return {"status": "rejected", "id": task_id, "approval_id": appr.id}

            # Decision is True: Mark approved
            await repo.update_approval_status(appr.id, status="approved")
            await repo.update_task_status(task_id, status="running")

        # 1. Revalidate browser state via bridge browser.inspect
        try:
            inspect_state = await bridge.call("browser.inspect", {}) or {}
            logger.info(f"Revalidated browser state: title='{inspect_state.get('title')}', url='{inspect_state.get('url')}'")
        except Exception as e:
            logger.warning(f"Browser state revalidation warning: {e}")
            inspect_state = {}

        # 1b. Enforce Origin Barrier check if origin_url was captured during approval pause
        checkpoint = json.loads(appr.session_checkpoint_json) if appr.session_checkpoint_json else {}
        expected_origin = checkpoint.get("origin_url")
        if expected_origin:
            current_url = inspect_state.get("url")
            is_valid, err_msg = OriginBarrier.validate_origin(expected_origin, current_url)
            if not is_valid:
                logger.error(f"Origin Barrier rejection for task {task_id}: {err_msg}")
                async with AsyncSessionLocal() as session:
                    repo = Repository(session)
                    await repo.update_approval_status(appr.id, status="rejected")
                    await repo.update_task_status(task_id, status="failed", error=err_msg)
                try:
                    bridge.notify("task.step_updated", {
                        "task_id": task_id,
                        "approval_id": appr.id,
                        "status": "failed",
                        "error": err_msg
                    })
                except Exception:
                    pass
                cls._cleanup_task(task_id)
                return {
                    "status": "error",
                    "error": err_msg,
                    "id": task_id,
                    "approval_id": appr.id
                }

        # 2. Execute the approved tool action exactly once via ToolExecutor
        tool_params = json.loads(appr.parameters_json) if appr.parameters_json else {}
        action_res = await ToolExecutor.execute(appr.tool_name, tool_params, bypass_approval=True)

        # 3. Mark approval executed and update step status in DB
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            await repo.update_approval_status(appr.id, status="executed")
            step_status = action_res.get("status", "completed")
            db_steps = await repo.get_task_steps(task_id)
            for ds in db_steps:
                if ds.step_number == appr.step_number:
                    await repo.update_step_status(ds.id, status=step_status, result=action_res)

        # 4. Restore checkpoint from session_checkpoint_json
        checkpoint = json.loads(appr.session_checkpoint_json) if appr.session_checkpoint_json else {}
        raw_remaining = checkpoint.get("remaining_steps", [])
        step_results = checkpoint.get("step_results", [])
        step_results.append(action_res)
        total_steps = checkpoint.get("total_steps", len(raw_remaining) + (appr.step_number or 1))

        remaining_steps = [TaskStep(**s) if isinstance(s, dict) else s for s in raw_remaining]

        # 5. Resume execution loop from step_number + 1
        loop_res = await cls._execute_steps_loop(task_id, remaining_steps, step_results, total_steps)

        return {
            "status": "approved",
            "id": task_id,
            "approval_id": appr.id,
            "executed_action": appr.tool_name,
            "action_result": action_res,
            "loop_result": loop_res
        }
