import json
import logging
import re
import asyncio
from typing import Dict, Any, Optional, List
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.repository import Repository
from backend.app.tools.executor import ToolExecutor
from backend.app.browser.bridge import bridge

logger = logging.getLogger("workflow_engine")

class WorkflowEngine:
    @staticmethod
    def _interpolate(obj: Any, variables: Dict[str, Any]) -> Any:
        if isinstance(obj, str):
            for k, v in variables.items():
                obj = obj.replace(f"{{{{{k}}}}}", str(v))
            return obj
        elif isinstance(obj, dict):
            return {k: WorkflowEngine._interpolate(v, variables) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [WorkflowEngine._interpolate(x, variables) for x in obj]
        return obj

    @classmethod
    async def execute_workflow(cls, workflow_id: str, input_variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        input_vars = input_variables or {}

        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            wf = await repo.get_workflow(workflow_id)
            if not wf:
                return {"status": "error", "error": f"Workflow {workflow_id} not found"}

            exec_record = await repo.create_workflow_execution(workflow_id)
            exec_id = exec_record.id
            steps_data = json.loads(wf.steps_json or "[]")
            default_vars = json.loads(wf.variables_json or "{}")

        merged_vars = {**default_vars, **input_vars}
        step_results: List[Dict[str, Any]] = []

        logger.info(f"Starting workflow '{wf.name}' ({workflow_id}) with {len(steps_data)} steps")

        try:
            for idx, raw_step in enumerate(steps_data):
                step_num = idx + 1
                action = raw_step.get("action")
                raw_params = raw_step.get("parameters", {})
                params = cls._interpolate(raw_params, merged_vars)

                # Update execution record
                async with AsyncSessionLocal() as session:
                    repo = Repository(session)
                    await repo.update_workflow_execution(exec_id, status="running", current_step=step_num)

                try:
                    bridge.notify("workflow.step_updated", {
                        "execution_id": exec_id,
                        "workflow_id": workflow_id,
                        "step": step_num,
                        "action": action,
                        "status": "running"
                    })
                except Exception:
                    pass

                # Execute action via ToolExecutor
                res = await ToolExecutor.execute(action, params)
                step_results.append({
                    "step": step_num,
                    "action": action,
                    "parameters": params,
                    "result": res
                })

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
                    try:
                        bridge.notify("workflow.step_updated", {
                            "execution_id": exec_id,
                            "workflow_id": workflow_id,
                            "status": "failed",
                            "error": err_msg
                        })
                    except Exception:
                        pass
                    return {
                        "status": "failed",
                        "execution_id": exec_id,
                        "failed_step": step_num,
                        "error": err_msg,
                        "results": step_results
                    }

                await asyncio.sleep(0.2)

            # Successfully completed
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.update_workflow_execution(
                    exec_id,
                    status="completed",
                    current_step=len(steps_data),
                    result=json.dumps(step_results)
                )

            try:
                bridge.notify("workflow.step_updated", {
                    "execution_id": exec_id,
                    "workflow_id": workflow_id,
                    "status": "completed",
                    "results_count": len(step_results)
                })
            except Exception:
                pass

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
    async def export_workflow(cls, workflow_id: str) -> Optional[Dict[str, Any]]:
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
        name = data.get("name", "Imported Workflow")
        description = data.get("description", "")
        trigger_type = data.get("trigger_type", "manual")
        steps = data.get("steps", [])
        variables = data.get("variables", {})

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
