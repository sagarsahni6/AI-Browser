import asyncio
import json
import logging
import sys
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.repository import Repository
from backend.app.tools.definitions import BROWSER_TOOLS
from backend.app.tools.executor import ToolExecutor
from backend.app.ai.router import ModelRouter

logger = logging.getLogger("orchestrator")

class TaskOrchestrator:
    @staticmethod
    async def run_task(task_id: str):
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            task = await repo.get_task(task_id)
            if not task:
                return

            await repo.update_task_status(task_id, status="running")

        try:
            # 1. Planning Phase
            provider, model = ModelRouter.route_for_task(task_type="tools")

            planning_prompt = (
                f"You are the Browser Agent Planner. The user wants to accomplish the following task in the browser:\n"
                f"\"{task.prompt}\"\n\n"
                f"Break this task into 2 to 5 clear, actionable steps. "
                f"Available tools: navigate, get_page_content, click_element, fill_input, scroll_page, open_new_tab, search_web, export_csv.\n"
                f"Respond with a JSON array of step descriptions, for example: [\"Navigate to target site\", \"Inspect page content\", \"Export findings to CSV\"]."
            )

            plan_result = await provider.chat_completion(
                messages=[{"role": "user", "content": planning_prompt}],
                model=model
            )

            # Extract steps from plan
            raw_text = plan_result.content
            steps_list = []
            try:
                start_idx = raw_text.find("[")
                end_idx = raw_text.rfind("]")
                if start_idx != -1 and end_idx != -1:
                    steps_list = json.loads(raw_text[start_idx:end_idx+1])
            except Exception:
                pass

            if not steps_list or not isinstance(steps_list, list):
                steps_list = [
                    f"Navigate and observe for '{task.prompt[:40]}'",
                    "Extract target information from the page",
                    "Verify result and complete task"
                ]

            # Record steps in DB
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                for idx, step_desc in enumerate(steps_list):
                    await repo.add_task_step(task_id, step_number=idx+1, description=str(step_desc))

            # 2. Execution Loop
            messages: List[Dict[str, Any]] = [
                {
                    "role": "system",
                    "content": (
                        "You are an autonomous Browser Agent. "
                        "You execute browser actions step by step to fulfill the user's task. "
                        "Use the provided tools to navigate, inspect, interact, and export data. "
                        "Always verify the state after performing actions."
                    )
                },
                {"role": "user", "content": task.prompt}
            ]

            max_turns = 6
            final_report = "Task completed successfully."

            for turn in range(max_turns):
                completion = await provider.chat_completion(
                    messages=messages,
                    model=model,
                    tools=BROWSER_TOOLS
                )

                if completion.tool_calls:
                    for tool_call in completion.tool_calls:
                        func_name = tool_call.get("function", {}).get("name")
                        raw_args = tool_call.get("function", {}).get("arguments", "{}")
                        try:
                            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                        except Exception:
                            args = {}

                        # Execute tool
                        tool_res = await ToolExecutor.execute(func_name, args)

                        # Record tool step in DB
                        async with AsyncSessionLocal() as session:
                            repo = Repository(session)
                            step = await repo.add_task_step(
                                task_id=task_id,
                                step_number=turn + 1,
                                description=f"Execute {func_name}",
                                tool_name=func_name,
                                parameters=args
                            )
                            await repo.update_step_status(step.id, status=tool_res.get("status", "completed"), result=tool_res)

                        # Feed tool result back to model
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tool_call]
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.get("id", f"call-{turn}"),
                            "name": func_name,
                            "content": json.dumps(tool_res)
                        })
                else:
                    final_report = completion.content
                    break

            # 3. Mark completed in DB
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.update_task_status(task_id, status="completed", result=final_report)

        except Exception as e:
            sys.stderr.write(f"[Orchestrator Error] Task {task_id} failed: {e}\n")
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.update_task_status(task_id, status="failed", error=str(e))
