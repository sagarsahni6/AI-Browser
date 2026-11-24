import json
import logging
from typing import Dict, Any, Optional
from backend.app.runtime.budget import ExecutionBudget
from backend.app.runtime.checkpoint_manager import CheckpointManager
from backend.app.runtime.execution_loop import ReActExecutionLoop
from backend.app.ai.router import ModelRouter, TaskType
from backend.app.ai.registry import provider_registry
from backend.app.browser.bridge import bridge
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.repository import Repository
from backend.app.tools.registry import tool_registry

logger = logging.getLogger("runtime_orchestrator")

class RuntimeOrchestrator:
    """
    Unified entrypoint for both conversational assistant interactions and
    autonomous multi-step background tasks, coordinating with ReActExecutionLoop.
    """

    @classmethod
    async def run_task(cls, task_id: str, budget: Optional[ExecutionBudget] = None) -> Dict[str, Any]:
        """Runs an autonomous multi-step task using ReActExecutionLoop."""
        prompt = ""
        initial_checkpoint = None

        # Check for prior checkpoint
        try:
            initial_checkpoint = await CheckpointManager.load_checkpoint(task_id)
        except Exception as e:
            logger.debug(f"No checkpoint loaded for task {task_id}: {e}")

        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            task = await repo.get_task(task_id)
            if not task:
                return {"status": "error", "error": f"Task {task_id} not found"}
            prompt = task.prompt
            await repo.update_task_status(task_id, status="running")

        loop = ReActExecutionLoop(
            task_id=task_id,
            prompt=prompt,
            budget=budget or ExecutionBudget(),
            initial_checkpoint=initial_checkpoint
        )
        result = await loop.run()

        # Update database task status based on result
        status = result.get("status", "completed")
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            if status == "completed":
                await repo.update_task_status(task_id, status="completed", result=result.get("report"))
            elif status == "failed":
                await repo.update_task_status(task_id, status="failed", error=result.get("error"))
            elif status == "budget_exhausted":
                await repo.update_task_status(task_id, status="failed", error=result.get("error"))

        return result

    @classmethod
    async def resume_task(cls, task_id: str, approval_id: Optional[str] = None, decision: bool = True) -> Dict[str, Any]:
        """Resumes an approval-paused task, enforcing Origin Barrier check."""
        from backend.app.agents.supervisor import SupervisorAgent
        return await SupervisorAgent.resume_approved_task(task_id, approval_id=approval_id, decision=decision)

    @classmethod
    def pause_task(cls, task_id: str) -> None:
        from backend.app.agents.supervisor import SupervisorAgent
        SupervisorAgent.pause_task(task_id)

    @classmethod
    def cancel_task(cls, task_id: str) -> None:
        from backend.app.agents.supervisor import SupervisorAgent
        SupervisorAgent.cancel_task(task_id)

    @classmethod
    async def run_chat(
        cls,
        conversation_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executes an interactive conversational turn with tool calling and budget limits."""
        budget = ExecutionBudget(max_steps=6, max_tool_calls=15, max_duration_seconds=120.0)

        # Route provider and model
        provider_key, selected_model = ModelRouter.route_for_task(
            task_type=TaskType.TOOL_CALLING,
            preferred_provider=provider_name,
            preferred_model=model_name
        )
        provider = provider_registry.get(provider_key)
        tools = tool_registry.get_openai_tools()

        messages = [
            {"role": "system", "content": "You are AI Browser, an intelligent web browsing assistant capable of inspecting pages, searching the web, extracting data, and controlling the browser safely."},
            {"role": "user", "content": message}
        ]

        turns = 0
        actions_taken = []

        while turns < budget.max_steps and not budget.is_exhausted():
            turns += 1
            budget.record_step(1)

            resp = await provider.chat_completion(messages=messages, model=selected_model, tools=tools)
            budget.record_tokens(resp.tokens_used or 0)

            if not resp.tool_calls:
                # Direct answer
                return {
                    "status": "success",
                    "conversation_id": conversation_id,
                    "reply": resp.content,
                    "actions_taken": actions_taken,
                    "budget": budget.remaining_summary()
                }

            # Handle tool calls
            for tc in resp.tool_calls:
                fn_name = tc["name"]
                fn_args = tc.get("arguments", {})
                budget.record_tool_call(1)

                try:
                    bridge.notify("chat:action", {"action": fn_name, "params": fn_args})
                except Exception:
                    pass

                tool_res = await tool_registry.execute(fn_name, fn_args)
                actions_taken.append({"tool": fn_name, "args": fn_args, "result": tool_res})

                # Append tool exchange to message history
                messages.append({
                    "role": "assistant",
                    "content": resp.content or "",
                    "tool_calls": [tc]
                })
                messages.append({
                    "role": "tool",
                    "name": fn_name,
                    "content": json.dumps(tool_res)
                })

        # Synthesis turn if finished after tool calls
        synth_resp = await provider.chat_completion(messages=messages, model=selected_model)
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "reply": synth_resp.content,
            "actions_taken": actions_taken,
            "budget": budget.remaining_summary()
        }
