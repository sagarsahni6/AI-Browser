import json
import logging
import re
import time
import asyncio
from typing import Dict, Any, Optional, List
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.models import WorkflowExecution
from backend.app.database.repository import Repository
from backend.app.tools.executor import ToolExecutor
from backend.app.browser.bridge import bridge
from backend.app.workflows.models import WorkflowDefinition

logger = logging.getLogger("workflow_engine")

RECOVERABLE_ERRORS = (
    "not interactable", "timeout", "target element not found",
    "waiting for selector", "stale element", "connection reset",
    "target closed", "rate limit"
)

class WorkflowEngine:
    """
    Advanced Autonomous Workflow Engine:
    - Directed Acyclic Graph (DAG) topological resolution and cycle detection
    - Deep dynamic parameter and prior-step output interpolation
    - Autonomous transient error recovery and fallback action execution
    - Structured SQLite checkpoint serialization and pause/resume lifecycle
    - Portable JSON workflow import/export with version 1.0 schema compliance
    """

    @classmethod
    def _notify_step_update(cls, payload: Dict[str, Any]) -> None:
        """Emit step progress updates across both dot and colon bridge notification topics."""
        try:
            bridge.notify("workflow.step_updated", payload)
        except Exception:
            pass
        try:
            bridge.notify("workflow:step_updated", payload)
        except Exception:
            pass

    @classmethod
    def resolve_dag_order(cls, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Topological sort using Kahn's algorithm with cycle detection.
        If no step specifies 'depends_on', preserves original sequential order.
        Raises ValueError on cyclic dependency or invalid dependency references.
        """
        if not steps:
            return []

        # If no step specifies dependencies, keep sequential sequence without mutating dictionaries
        if not any(s.get("depends_on") for s in steps):
            return list(steps)

        step_map: Dict[str, Dict[str, Any]] = {}
        in_degree: Dict[str, int] = {}
        adj: Dict[str, List[str]] = {}

        for idx, s in enumerate(steps):
            sid = s.get("id") or f"step_{idx + 1}"
            step_map[sid] = s
            in_degree[sid] = 0
            adj[sid] = []

        for idx, s in enumerate(steps):
            sid = s.get("id") or f"step_{idx + 1}"
            deps = s.get("depends_on", [])
            if isinstance(deps, str):
                deps = [deps]
            for dep in deps:
                if dep not in in_degree:
                    raise ValueError(f"Step '{sid}' depends on non-existent step '{dep}'")
                adj[dep].append(sid)
                in_degree[sid] += 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        ordered = []

        while queue:
            curr = queue.pop(0)
            ordered.append(step_map[curr])
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered) < len(steps):
            raise ValueError("Cyclic dependency detected in workflow DAG")

        return ordered

    @classmethod
    def _resolve_path(cls, path: str, context: Dict[str, Any]) -> Any:
        """Resolve a dot-separated variable or prior step path from execution context."""
        if path in context:
            return context[path]
        if "variables" in context and isinstance(context["variables"], dict) and path in context["variables"]:
            return context["variables"][path]
        if "step_outputs" in context and isinstance(context["step_outputs"], dict) and path in context["step_outputs"]:
            return context["step_outputs"][path]

        parts = path.split(".")
        curr: Any = context
        if isinstance(curr, dict) and parts[0] not in curr:
            if "step_outputs" in curr and isinstance(curr["step_outputs"], dict) and parts[0] in curr["step_outputs"]:
                curr = curr["step_outputs"]
            elif "variables" in curr and isinstance(curr["variables"], dict) and parts[0] in curr["variables"]:
                curr = curr["variables"]

        for part in parts:
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            elif isinstance(curr, list) and part.isdigit() and int(part) < len(curr):
                curr = curr[int(part)]
            elif hasattr(curr, part):
                curr = getattr(curr, part)
            else:
                return None
        return curr

    @classmethod
    def _interpolate(cls, obj: Any, context: Dict[str, Any]) -> Any:
        """
        Deep variable and step output interpolation.
        Supports:
        - Exact match: '{{step_1.result}}' preserves native object types (dicts, lists, primitives).
        - Substring match: 'https://{{domain}}/search' substitutes string representation.
        - Unresolved variables remain untouched as '{{unresolved}}' without crashing.
        """
        if isinstance(obj, str):
            # 1. Exact match: preserve underlying type
            exact = re.fullmatch(r"\{\{([a-zA-Z0-9_\.]+)\}\}", obj.strip())
            if exact:
                resolved = cls._resolve_path(exact.group(1), context)
                return resolved if resolved is not None else obj

            # 2. Substring substitution: format into string
            def _repl(match: re.Match) -> str:
                val = cls._resolve_path(match.group(1), context)
                return str(val) if val is not None else match.group(0)

            return re.sub(r"\{\{([a-zA-Z0-9_\.]+)\}\}", _repl, obj)
        elif isinstance(obj, dict):
            return {k: cls._interpolate(v, context) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [cls._interpolate(x, context) for x in obj]
        return obj

    @classmethod
    async def _execute_with_recovery(
        cls,
        action: str,
        params: Dict[str, Any],
        step_cfg: Dict[str, Any],
        exec_id: str,
        step_num: int,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute an action with autonomous retry on transient recoverable failures,
        and fallback action execution if retries are exhausted.
        """
        max_retries = step_cfg.get("max_retries", 2)
        retry_delay = step_cfg.get("retry_delay", 0.5)
        fallback_action = step_cfg.get("fallback_action")
        fallback_params = step_cfg.get("fallback_parameters", {})

        last_res: Dict[str, Any] = {}
        for attempt in range(max_retries + 1):
            res = await ToolExecutor.execute(action, params)
            last_res = res
            if res.get("status") in ("success", "ok", "approval_required"):
                return res

            err = str(res.get("error", "")).lower()
            is_recoverable = any(sig in err for sig in RECOVERABLE_ERRORS)
            if not is_recoverable or attempt == max_retries:
                break

            logger.warning(f"Recoverable tool failure on {action} (attempt {attempt+1}/{max_retries}): {err}")
            cls._notify_step_update({
                "execution_id": exec_id,
                "step": step_num,
                "status": "recovering",
                "retry": attempt + 1,
                "error": res.get("error")
            })
            await asyncio.sleep(retry_delay * (attempt + 1))

        # If retries exhausted and fallback action defined
        if fallback_action:
            logger.info(f"Executing fallback action '{fallback_action}' for step {step_num}")
            cls._notify_step_update({
                "execution_id": exec_id,
                "step": step_num,
                "status": "recovering",
                "fallback": fallback_action
            })
            interpolated_fallback = cls._interpolate(fallback_params, context)
            return await ToolExecutor.execute(fallback_action, interpolated_fallback)

        return last_res

    @classmethod
    async def execute_workflow(
        cls,
        workflow_id: str,
        input_variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow from start to completion or pause on user approval.
        """
        input_vars = input_variables or {}

        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            wf = await repo.get_workflow(workflow_id)
            if not wf:
                return {"status": "error", "error": f"Workflow {workflow_id} not found"}

            exec_record = await repo.create_workflow_execution(workflow_id)
            exec_id = exec_record.id
            raw_steps_data = json.loads(wf.steps_json or "[]")
            default_vars = json.loads(wf.variables_json or "{}")

        # Resolve DAG ordering and cycle check
        try:
            steps_data = cls.resolve_dag_order(raw_steps_data)
        except ValueError as ve:
            logger.error(f"Workflow DAG validation error: {ve}")
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.update_workflow_execution(exec_id, status="failed", error=str(ve))
            return {"status": "failed", "execution_id": exec_id, "error": str(ve)}

        merged_vars = {**default_vars, **input_vars}
        context: Dict[str, Any] = {
            "variables": merged_vars,
            "step_outputs": {}
        }
        step_results: List[Dict[str, Any]] = []

        logger.info(f"Starting workflow '{wf.name}' ({workflow_id}) with {len(steps_data)} steps")

        try:
            for idx, raw_step in enumerate(steps_data):
                step_num = idx + 1
                action = raw_step.get("action")
                raw_params = raw_step.get("parameters", {})
                params = cls._interpolate(raw_params, context)

                # Update execution record
                async with AsyncSessionLocal() as session:
                    repo = Repository(session)
                    await repo.update_workflow_execution(exec_id, status="running", current_step=step_num)

                cls._notify_step_update({
                    "execution_id": exec_id,
                    "workflow_id": workflow_id,
                    "step": step_num,
                    "action": action,
                    "status": "running"
                })

                # Execute action via ToolExecutor with recovery
                res = await cls._execute_with_recovery(action, params, raw_step, exec_id, step_num, context)
                step_results.append({
                    "step": step_num,
                    "action": action,
                    "parameters": params,
                    "result": res
                })

                # Register outputs in context
                context["step_outputs"][f"step_{step_num}"] = res
                if raw_step.get("id"):
                    context["step_outputs"][raw_step["id"]] = res

                # Check if approval required
                if res.get("status") == "approval_required":
                    reason = res.get("reason", "Step requires user approval")
                    logger.warning(f"Workflow '{wf.name}' step {step_num} requires approval: {reason}")
                    
                    checkpoint = {
                        "execution_id": exec_id,
                        "workflow_id": workflow_id,
                        "paused_step": step_num,
                        "total_steps": len(steps_data),
                        "completed_results": step_results[:-1],
                        "variables": merged_vars,
                        "step_outputs": context["step_outputs"],
                        "pending_step": {
                            "step": step_num,
                            "id": raw_step.get("id", f"step_{step_num}"),
                            "action": action,
                            "parameters": params,
                            "step_cfg": raw_step
                        },
                        "remaining_steps": steps_data[idx + 1:],
                        "approval_id": res.get("approval_id"),
                        "reason": reason,
                        "paused_at": time.time()
                    }

                    async with AsyncSessionLocal() as session:
                        repo = Repository(session)
                        await repo.update_workflow_execution(
                            exec_id,
                            status="approval_required",
                            current_step=step_num,
                            result=json.dumps({"checkpoint": checkpoint, "results": step_results}),
                            error=reason
                        )

                    cls._notify_step_update({
                        "execution_id": exec_id,
                        "workflow_id": workflow_id,
                        "step": step_num,
                        "status": "approval_required",
                        "reason": reason,
                        "action": action,
                        "parameters": params
                    })

                    return {
                        "status": "approval_required",
                        "execution_id": exec_id,
                        "paused_step": step_num,
                        "reason": reason,
                        "results": step_results,
                        "checkpoint": checkpoint
                    }

                # Check if unrecoverable error
                if res.get("status") == "error":
                    err_msg = res.get("error", "Step failed")
                    logger.warning(f"Workflow '{wf.name}' step {step_num} failed: {err_msg}")
                    async with AsyncSessionLocal() as session:
                        repo = Repository(session)
                        await repo.update_workflow_execution(
                            exec_id,
                            status="failed",
                            current_step=step_num,
                            result=json.dumps(step_results),
                            error=err_msg
                        )

                    cls._notify_step_update({
                        "execution_id": exec_id,
                        "workflow_id": workflow_id,
                        "status": "failed",
                        "error": err_msg
                    })

                    return {
                        "status": "failed",
                        "execution_id": exec_id,
                        "failed_step": step_num,
                        "error": err_msg,
                        "results": step_results
                    }

                await asyncio.sleep(0.1)

            # Successfully completed all steps
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.update_workflow_execution(
                    exec_id,
                    status="completed",
                    current_step=len(steps_data),
                    result=json.dumps(step_results)
                )

            cls._notify_step_update({
                "execution_id": exec_id,
                "workflow_id": workflow_id,
                "status": "completed",
                "results_count": len(step_results)
            })

            return {
                "status": "completed",
                "execution_id": exec_id,
                "workflow_id": workflow_id,
                "steps_executed": len(step_results),
                "results": step_results
            }

        except Exception as e:
            logger.error(f"Workflow execution exception: {e}")
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.update_workflow_execution(
                    exec_id,
                    status="failed",
                    error=str(e)
                )
            return {"status": "error", "error": str(e), "execution_id": exec_id}

    @classmethod
    async def resume_workflow(
        cls,
        execution_id: str,
        decision: bool = True,
        approval_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resume a paused workflow execution from its SQLite checkpoint.
        If decision is True, executes the pending action with bypass_approval=True
        and continues remaining steps to completion.
        If decision is False, marks execution cancelled.
        """
        async with AsyncSessionLocal() as session:
            exec_rec = await session.get(WorkflowExecution, execution_id)
            if not exec_rec or exec_rec.status != "approval_required":
                return {"status": "error", "error": f"Execution {execution_id} not paused on approval"}

            saved_data = json.loads(exec_rec.result_json or "{}")
            checkpoint = saved_data.get("checkpoint", {})
            workflow_id = exec_rec.workflow_id

        if not checkpoint:
            return {"status": "error", "error": f"Execution {execution_id} missing checkpoint"}

        if not decision:
            # Rejection
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.update_workflow_execution(
                    execution_id,
                    status="cancelled",
                    error="Rejected by user"
                )
            cls._notify_step_update({
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "status": "cancelled",
                "error": "Rejected by user"
            })
            return {
                "status": "cancelled",
                "execution_id": execution_id,
                "reason": "rejected"
            }

        # User approved: execute pending action with bypass_approval=True
        pending = checkpoint["pending_step"]
        action = pending["action"]
        params = pending["parameters"]
        step_num = pending["step"]

        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            await repo.update_workflow_execution(
                execution_id,
                status="running",
                current_step=step_num
            )

        cls._notify_step_update({
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "step": step_num,
            "action": action,
            "status": "running"
        })

        action_res = await ToolExecutor.execute(action, params, bypass_approval=True)

        step_results = list(checkpoint.get("completed_results", []))
        step_results.append({
            "step": step_num,
            "action": action,
            "parameters": params,
            "result": action_res
        })

        context: Dict[str, Any] = {
            "variables": checkpoint.get("variables", {}),
            "step_outputs": checkpoint.get("step_outputs", {})
        }
        context["step_outputs"][f"step_{step_num}"] = action_res
        if pending.get("id"):
            context["step_outputs"][pending["id"]] = action_res

        if action_res.get("status") == "error":
            err_msg = action_res.get("error", "Approved action failed")
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.update_workflow_execution(
                    execution_id,
                    status="failed",
                    current_step=step_num,
                    result=json.dumps(step_results),
                    error=err_msg
                )
            cls._notify_step_update({
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "status": "failed",
                "error": err_msg
            })
            return {
                "status": "failed",
                "execution_id": execution_id,
                "failed_step": step_num,
                "error": err_msg,
                "results": step_results
            }

        # Continue executing remaining steps
        remaining_steps = checkpoint.get("remaining_steps", [])
        total_steps = checkpoint.get("total_steps", step_num + len(remaining_steps))

        for rem_idx, raw_step in enumerate(remaining_steps):
            curr_step_num = step_num + 1 + rem_idx
            rem_action = raw_step.get("action")
            rem_raw_params = raw_step.get("parameters", {})
            rem_params = cls._interpolate(rem_raw_params, context)

            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.update_workflow_execution(
                    execution_id,
                    status="running",
                    current_step=curr_step_num
                )

            cls._notify_step_update({
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "step": curr_step_num,
                "action": rem_action,
                "status": "running"
            })

            res = await cls._execute_with_recovery(
                rem_action, rem_params, raw_step, execution_id, curr_step_num, context
            )

            step_results.append({
                "step": curr_step_num,
                "action": rem_action,
                "parameters": rem_params,
                "result": res
            })

            context["step_outputs"][f"step_{curr_step_num}"] = res
            if raw_step.get("id"):
                context["step_outputs"][raw_step["id"]] = res

            if res.get("status") == "approval_required":
                new_reason = res.get("reason", "Step requires user approval")
                new_checkpoint = {
                    "execution_id": execution_id,
                    "workflow_id": workflow_id,
                    "paused_step": curr_step_num,
                    "total_steps": total_steps,
                    "completed_results": step_results[:-1],
                    "variables": context["variables"],
                    "step_outputs": context["step_outputs"],
                    "pending_step": {
                        "step": curr_step_num,
                        "id": raw_step.get("id", f"step_{curr_step_num}"),
                        "action": rem_action,
                        "parameters": rem_params,
                        "step_cfg": raw_step
                    },
                    "remaining_steps": remaining_steps[rem_idx + 1:],
                    "approval_id": res.get("approval_id"),
                    "reason": new_reason,
                    "paused_at": time.time()
                }
                async with AsyncSessionLocal() as session:
                    repo = Repository(session)
                    await repo.update_workflow_execution(
                        execution_id,
                        status="approval_required",
                        current_step=curr_step_num,
                        result=json.dumps({"checkpoint": new_checkpoint, "results": step_results}),
                        error=new_reason
                    )
                cls._notify_step_update({
                    "execution_id": execution_id,
                    "workflow_id": workflow_id,
                    "step": curr_step_num,
                    "status": "approval_required",
                    "reason": new_reason,
                    "action": rem_action,
                    "parameters": rem_params
                })
                return {
                    "status": "approval_required",
                    "execution_id": execution_id,
                    "paused_step": curr_step_num,
                    "reason": new_reason,
                    "results": step_results,
                    "checkpoint": new_checkpoint
                }

            if res.get("status") == "error":
                err_msg = res.get("error", "Step failed")
                async with AsyncSessionLocal() as session:
                    repo = Repository(session)
                    await repo.update_workflow_execution(
                        execution_id,
                        status="failed",
                        current_step=curr_step_num,
                        result=json.dumps(step_results),
                        error=err_msg
                    )
                cls._notify_step_update({
                    "execution_id": execution_id,
                    "workflow_id": workflow_id,
                    "status": "failed",
                    "error": err_msg
                })
                return {
                    "status": "failed",
                    "execution_id": execution_id,
                    "failed_step": curr_step_num,
                    "error": err_msg,
                    "results": step_results
                }

            await asyncio.sleep(0.1)

        # All completed
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            await repo.update_workflow_execution(
                execution_id,
                status="completed",
                current_step=total_steps,
                result=json.dumps(step_results)
            )

        cls._notify_step_update({
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "status": "completed",
            "results_count": len(step_results)
        })

        return {
            "status": "completed",
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "steps_executed": len(step_results),
            "results": step_results
        }

    @classmethod
    async def export_workflow(cls, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Export workflow to portable JSON dictionary format with version 1.0 schema."""
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            wf = await repo.get_workflow(workflow_id)
            if not wf:
                return None
            return {
                "version": "1.0",
                "name": wf.name,
                "description": wf.description,
                "trigger_type": wf.trigger_type,
                "steps": json.loads(wf.steps_json or "[]"),
                "variables": json.loads(wf.variables_json or "{}")
            }

    @classmethod
    async def import_workflow(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and import workflow JSON definition into database.
        Validates DAG topological constraints and creates persistent workflow record.
        """
        name = data.get("name", "Imported Workflow")
        description = data.get("description", "")
        trigger_type = data.get("trigger_type", "manual")
        steps = data.get("steps", [])
        variables = data.get("variables", {})

        # Validate DAG
        cls.resolve_dag_order(steps)

        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            wf = await repo.create_workflow(
                name=name,
                description=description,
                trigger_type=trigger_type,
                steps=steps,
                variables=variables
            )
            return {
                "id": wf.id,
                "name": wf.name,
                "description": wf.description,
                "step_count": len(steps)
            }
