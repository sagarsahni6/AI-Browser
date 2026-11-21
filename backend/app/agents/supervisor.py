import logging
import asyncio
from typing import Dict, Any, Optional, List, Set
from backend.app.agents.models import TaskPlan, TaskStep, StepStatus
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.browser_agent import BrowserAgent
from backend.app.agents.researcher import ResearcherAgent
from backend.app.agents.data_agent import DataAgent
from backend.app.agents.verifier import VerifierAgent
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
    4. Strict security approval gates
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
            plan: TaskPlan = await PlannerAgent.create_plan(task_id, task.prompt, current_url)

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
            step_retries: Dict[int, int] = {}
            step_results = []
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
                            "total_steps": len(plan.steps) if (plan and hasattr(plan, "steps")) else 0
                        })
                    except Exception:
                        pass
                    cls._cleanup_task(task_id)
                    return

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
                            "total_steps": len(plan.steps) if (plan and hasattr(plan, "steps")) else 0
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
                        "total_steps": len(plan.steps) if (plan and hasattr(plan, "steps")) else 0,
                        "status": "running",
                        "description": step.description,
                        "action": step.action,
                        "parameters": step.parameters
                    })
                except Exception:
                    pass

                # D. Dispatch step to specialist agent
                result: Dict[str, Any] = {}
                if step.agent == "browser":
                    result = await BrowserAgent.execute_step(step.action, step.parameters)
                elif step.agent == "researcher":
                    result = await ResearcherAgent.execute_step(step.action, step.parameters)
                elif step.agent == "data":
                    result = await DataAgent.execute_step(step.action, step.parameters)
                elif step.agent == "verifier":
                    result = await VerifierAgent.execute_step(step.action, step.parameters)
                else:
                    result = await BrowserAgent.execute_step(step.action, step.parameters)

                step_results.append(result)
                step_status = result.get("status", "completed")

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

                # F. Handle security approval requirement
                if step_status == "approval_required":
                    logger.warning(f"Step {step.id} requires user approval: {result.get('reason')}")
                    async with AsyncSessionLocal() as session:
                        repo = Repository(session)
                        await repo.update_task_status(task_id, status="approval_required", result=result.get("reason"))
                        import json
                        await repo.create_approval_request(
                            task_id=task_id,
                            tool_name=step.action,
                            action_type="sensitive_operation",
                            description=result.get("reason", "Action requires user confirmation"),
                            parameters_json=json.dumps(step.parameters)
                        )
                    try:
                        bridge.notify("task.step_updated", {
                            "task_id": task_id,
                            "step_id": step.id,
                            "step_number": step.id,
                            "total_steps": len(plan.steps) if (plan and hasattr(plan, "steps")) else 0,
                            "status": "approval_required",
                            "reason": result.get("reason"),
                            "action": step.action,
                            "parameters": step.parameters
                        })
                    except Exception:
                        pass
                    return

                # G. Reactive self-correction & dynamic re-planning on step error
                if step_status == "error":
                    retries = step_retries.get(step.id, 0)
                    if retries < max_retries_per_step:
                        step_retries[step.id] = retries + 1
                        logger.warning(f"Step {step.id} failed ({result.get('error')}). Re-planning corrective steps (attempt {retries + 1}/{max_retries_per_step})...")

                        # Inspect live browser state
                        current_obs: Dict[str, Any] = {}
                        try:
                            current_obs = await bridge.call("browser.inspect", {}) or {}
                        except Exception:
                            pass

                        # Ask PlannerAgent for corrective steps
                        corrective_steps = await PlannerAgent.replan_subgoal(
                            task_id=task_id,
                            failed_step=step,
                            error_context=str(result.get("error", "Action error")),
                            current_obs=current_obs,
                            remaining_steps=remaining_steps
                        )

                        # Insert corrective steps at the head of the queue
                        if corrective_steps:
                            # Save corrective steps to DB
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
                                    "total_steps": len(plan.steps) if (plan and hasattr(plan, "steps")) else 0,
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
                        "total_steps": len(plan.steps) if (plan and hasattr(plan, "steps")) else 0,
                        "status": step_status,
                        "description": step.description,
                        "result": result
                    })
                except Exception:
                    pass

                # Small delay between actions for visual tracking and UI breathing room
                await asyncio.sleep(0.3)

            # 4. Final verification
            verify_res = await VerifierAgent.execute_step("verify_task", {})

            # 5. Mark task completed
            final_report = f"Task completed: {len(step_results)} steps executed successfully. Verified state: {verify_res.get('url', 'done')}."
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.update_task_status(task_id, status="completed", result=final_report)

            logger.info(f"Task {task_id} completed successfully")
            try:
                bridge.notify("task.step_updated", {
                    "task_id": task_id,
                    "status": "completed",
                    "total_steps": len(plan.steps) if (plan and hasattr(plan, "steps")) else 0,
                    "result": final_report
                })
            except Exception:
                pass

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
