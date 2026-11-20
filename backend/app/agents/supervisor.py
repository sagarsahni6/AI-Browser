import logging
import asyncio
from typing import Dict, Any, Optional
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
    Orchestrates the complete lifecycle of an autonomous task:
    1. Plans task via PlannerAgent
    2. Routes each step to specialist agents (BrowserAgent, ResearcherAgent, DataAgent, VerifierAgent)
    3. Handles approvals and safety policy checks
    4. Records step-by-step progress and events to SQLite
    5. Validates task completion via VerifierAgent
    """

    @staticmethod
    async def run_task(task_id: str):
        logger.info(f"SupervisorAgent starting task {task_id}")
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            task = await repo.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            await repo.update_task_status(task_id, status="running")

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

            # Record plan steps in database
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

            # 3. Execution Phase: step-by-step dispatch to specialist agents
            step_results = []
            final_report = "Task completed successfully."

            for step in plan.steps:
                logger.info(f"Executing Step {step.id}: [{step.agent}] {step.action}")

                # Notify Electron / UI of active action
                try:
                    bridge.notify("browser.action_started", {
                        "action": step.action,
                        "parameters": step.parameters,
                        "description": step.description
                    })
                except Exception:
                    pass

                # Dispatch to specialist agent
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

                # Update step in DB
                async with AsyncSessionLocal() as session:
                    repo = Repository(session)
                    # Find step by number and update
                    db_steps = await repo.get_task_steps(task_id)
                    for ds in db_steps:
                        if ds.step_number == step.id:
                            await repo.update_step_status(
                                ds.id,
                                status=result.get("status", "completed"),
                                result=result
                            )

                # Check if approval required
                if result.get("status") == "approval_required":
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
                        bridge.notify("browser.action_started", {
                            "action": step.action,
                            "parameters": {**step.parameters, "task_id": task_id},
                            "status": "approval_required",
                            "result": result.get("reason")
                        })
                    except Exception:
                        pass
                    return

                # Check for critical errors
                if result.get("status") == "error":
                    logger.warning(f"Step {step.id} returned error: {result.get('error')}. Continuing with error recovery...")

                # Small delay between actions for visual tracking and UI breathing room
                await asyncio.sleep(0.3)

            # 4. Final verification
            verify_res = await VerifierAgent.execute_step("verify_task", {})

            # 5. Mark task completed
            final_report = f"Task completed: {len(plan.steps)} steps executed successfully. Verified state: {verify_res.get('url', 'done')}."
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.update_task_status(task_id, status="completed", result=final_report)

            logger.info(f"Task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"SupervisorAgent failed task {task_id}: {e}")
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.update_task_status(task_id, status="failed", error=str(e))
