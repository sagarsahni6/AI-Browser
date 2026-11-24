import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from backend.app.runtime.budget import ExecutionBudget
from backend.app.runtime.checkpoint_manager import CheckpointManager
from backend.app.agents.models import TaskPlan, TaskStep, PlanStep, StepStatus
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.browser_agent import BrowserAgent
from backend.app.agents.dom_agent import DOMAgent
from backend.app.agents.vision_agent import VisionAgent
from backend.app.agents.desktop_agent import DesktopAgent
from backend.app.agents.file_agent import FileAgent
from backend.app.agents.memory_agent import MemoryAgent
from backend.app.agents.recovery_agent import RecoveryAgent
from backend.app.agents.researcher import ResearcherAgent
from backend.app.agents.data_agent import DataAgent
from backend.app.agents.verifier import VerifierAgent
from backend.app.security.policy import SecurityPolicy, OriginBarrier
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.repository import Repository
from backend.app.browser.bridge import bridge

logger = logging.getLogger("execution_loop")

class ReActExecutionLoop:
    """
    Unified ReAct Cognitive Execution Loop:
    Sequences Intent Analysis -> Dynamic Planning -> Policy Evaluation -> Action Execution ->
    Observation -> Objective Verification -> Budget Tracking -> Autonomous Recovery.
    """

    def __init__(
        self,
        task_id: str,
        prompt: str,
        budget: Optional[ExecutionBudget] = None,
        initial_checkpoint: Optional[Dict[str, Any]] = None
    ):
        self.task_id = task_id
        self.prompt = prompt
        self.budget = budget or ExecutionBudget()
        self.initial_checkpoint = initial_checkpoint
        self.step_results: List[Dict[str, Any]] = []

    async def run(self) -> Dict[str, Any]:
        from backend.app.agents.supervisor import SupervisorAgent
        logger.info(f"ReActExecutionLoop starting task {self.task_id}")
        remaining_steps: List[TaskStep] = []
        total_steps = 0

        # 1. State / Checkpoint Restoration or Dynamic Planning
        if self.initial_checkpoint:
            raw_remaining = self.initial_checkpoint.get("remaining_steps", [])
            remaining_steps = [TaskStep(**s) if isinstance(s, dict) else s for s in raw_remaining]
            self.step_results = self.initial_checkpoint.get("step_results", [])
            total_steps = self.initial_checkpoint.get("total_steps", len(remaining_steps))
            logger.info(f"Restored {len(remaining_steps)} remaining steps from checkpoint")
        else:
            # Observe current browser state
            current_url = "about:blank"
            try:
                obs = await bridge.call("browser.inspect", {})
                if obs:
                    current_url = obs.get("url", "about:blank")
            except Exception:
                pass

            plan = await PlannerAgent.create_plan(self.task_id, self.prompt, current_url)
            remaining_steps = list(plan.steps)
            total_steps = len(remaining_steps)

            # Record initial steps in database
            try:
                async with AsyncSessionLocal() as session:
                    repo = Repository(session)
                    for step in plan.steps:
                        await repo.add_task_step(
                            task_id=self.task_id,
                            step_number=step.id,
                            description=f"[{step.agent.upper()}] {step.description}",
                            tool_name=step.action,
                            parameters=step.parameters
                        )
            except Exception as e:
                logger.debug(f"DB step logging notice: {e}")

        # 2. Main Execution Loop
        step_retries: Dict[int, int] = {}

        while remaining_steps:
            # Check budget exhaustion
            if self.budget.is_exhausted():
                reason = self.budget.exhaustion_reason()
                logger.warning(f"Task {self.task_id} halted: {reason}")
                return {
                    "status": "budget_exhausted",
                    "task_id": self.task_id,
                    "error": reason,
                    "budget": self.budget.remaining_summary(),
                    "results": self.step_results
                }

            # Check cooperative cancellation
            if SupervisorAgent.is_cancelled(self.task_id):
                logger.info(f"Task {self.task_id} cancelled cooperatively")
                return {"status": "cancelled", "task_id": self.task_id, "results": self.step_results}

            # Check cooperative pause
            while SupervisorAgent.is_paused(self.task_id):
                if SupervisorAgent.is_cancelled(self.task_id):
                    return {"status": "cancelled", "task_id": self.task_id, "results": self.step_results}
                await asyncio.sleep(0.5)

            step = remaining_steps.pop(0)
            self.budget.record_step(1)
            self.budget.record_tool_call(1)

            # Security Policy Evaluation
            policy_res = SecurityPolicy.evaluate(step.action, step.parameters)
            if policy_res.is_blocked:
                logger.error(f"Step {step.id} permanently blocked: {policy_res.reason}")
                return {
                    "status": "blocked",
                    "task_id": self.task_id,
                    "error": f"Security Policy Violation: {policy_res.reason}",
                    "blocked_step": step.action
                }

            if policy_res.requires_approval:
                logger.warning(f"Step {step.id} requires user approval: {policy_res.reason}")
                current_origin_url = None
                try:
                    obs = await bridge.call("browser.inspect", {})
                    if obs:
                        current_origin_url = obs.get("url")
                except Exception:
                    pass

                checkpoint_payload = {
                    "task_id": self.task_id,
                    "step_number": step.id,
                    "step": step.model_dump() if hasattr(step, "model_dump") else step.dict(),
                    "remaining_steps": [s.model_dump() if hasattr(s, "model_dump") else s.dict() for s in remaining_steps],
                    "step_results": self.step_results,
                    "total_steps": total_steps,
                    "origin_url": current_origin_url,
                    "budget": self.budget.model_dump()
                }
                checkpoint_id = await CheckpointManager.save_checkpoint(self.task_id, step.id, checkpoint_payload)

                appr_id = None
                async with AsyncSessionLocal() as session:
                    repo = Repository(session)
                    await repo.update_task_status(self.task_id, status="approval_required", result=policy_res.reason)
                    appr = await repo.create_approval_request(
                        task_id=self.task_id,
                        tool_name=step.action,
                        action_type="sensitive_operation",
                        description=policy_res.reason,
                        parameters_json=json.dumps(step.parameters),
                        step_number=step.id,
                        session_checkpoint_json=json.dumps(checkpoint_payload)
                    )
                    appr_id = appr.id

                try:
                    bridge.notify("task.step_updated", {
                        "task_id": self.task_id,
                        "step_id": step.id,
                        "approval_id": appr_id,
                        "status": "approval_required",
                        "reason": policy_res.reason
                    })
                except Exception:
                    pass

                return {
                    "status": "approval_required",
                    "task_id": self.task_id,
                    "approval_id": appr_id,
                    "checkpoint_id": checkpoint_id,
                    "step": step.id,
                    "reason": policy_res.reason
                }

            # Dispatch Step to Specialist Agent
            agent_name = (step.agent or "browser").lower()
            result: Dict[str, Any] = {}
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

            self.step_results.append(result)
            step_status = result.get("status", "completed")

            # Check Objective Verification Strategy
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
                    step_status = "failed"
                    result["status"] = "failed"
                    result["error"] = f"Objective verification failed: {v_res.get('reason')}"

            # Self-healing recovery if failed
            if step_status == "failed":
                retries = step_retries.get(step.id, 0)
                if self.budget.can_retry_step(retries):
                    step_retries[step.id] = retries + 1
                    logger.info(f"Attempting self-healing recovery for step {step.id} (attempt {retries + 1})")
                    current_obs = {}
                    try:
                        current_obs = await bridge.call("browser.inspect", {}) or {}
                    except Exception:
                        pass
                    rec_diag = RecoveryAgent.suggest_recovery_steps(
                        step.model_dump() if hasattr(step, "model_dump") else step.dict(),
                        str(result.get("error", "Error")),
                        current_obs
                    )
                    suggested = rec_diag.get("suggested_steps", [])
                    new_steps = [TaskStep(id=step.id, **s) for s in suggested] if suggested else [step]
                    remaining_steps = new_steps + remaining_steps
                    continue
                else:
                    logger.error(f"Step {step.id} failed and retry budget exhausted.")
                    return {
                        "status": "failed",
                        "task_id": self.task_id,
                        "error": result.get("error", "Step failed"),
                        "failed_step": step.id,
                        "results": self.step_results
                    }

        # 3. Final Verification
        verify_res = await VerifierAgent.execute_step("verify_task", {})
        await CheckpointManager.clear_checkpoint(self.task_id)

        report = f"Task completed: {len(self.step_results)} actions executed successfully."
        return {
            "status": "completed",
            "task_id": self.task_id,
            "results": self.step_results,
            "verification": verify_res,
            "budget": self.budget.remaining_summary(),
            "report": report
        }
