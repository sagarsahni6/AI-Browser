import json
import logging
from typing import List, Dict, Any, Optional
from backend.app.agents.models import TaskPlan, TaskStep, StepStatus
from backend.app.ai.router import ModelRouter

logger = logging.getLogger("planner_agent")

class PlannerAgent:
    """
    Decomposes complex browser tasks into a structured sequence of executable steps.
    Assigns each step to the appropriate specialist agent (browser, researcher, data, verifier).
    """

    @staticmethod
    async def create_plan(task_id: str, prompt: str, current_url: Optional[str] = None) -> TaskPlan:
        provider, model = ModelRouter.route_for_task(task_type="tools")

        planning_prompt = (
            f"You are the Browser Agent Task Planner. The user wants to accomplish:\n"
            f"\"{prompt}\"\n\n"
            f"Current tab URL: {current_url or 'about:blank'}\n\n"
            f"Break this task into 2 to 5 actionable steps.\n"
            f"Available agents: 'browser' (navigate, click, type, scroll), 'researcher' (search_web, compare), 'data' (extract_table, export_csv, export_json), 'verifier' (verify state, screenshot).\n"
            f"Respond with a JSON array of step objects, for example:\n"
            f"[\n"
            f"  {{\"id\": 1, \"agent\": \"browser\", \"action\": \"navigate\", \"description\": \"Navigate to target website\", \"parameters\": {{\"url\": \"https://example.com\"}}, \"expected_outcome\": \"Page loaded\"}},\n"
            f"  {{\"id\": 2, \"agent\": \"data\", \"action\": \"extract_table_data\", \"description\": \"Extract table from page\", \"parameters\": {{}}, \"expected_outcome\": \"Table data extracted\"}},\n"
            f"  {{\"id\": 3, \"agent\": \"data\", \"action\": \"export_csv\", \"description\": \"Export extracted data to CSV\", \"parameters\": {{\"filename\": \"data.csv\"}}, \"expected_outcome\": \"File saved\"}},\n"
            f"  {{\"id\": 4, \"agent\": \"verifier\", \"action\": \"verify_task\", \"description\": \"Verify task completed and file created\", \"parameters\": {{}}, \"expected_outcome\": \"Confirmed complete\"}}\n"
            f"]"
        )

        try:
            plan_res = await provider.chat_completion(
                messages=[{"role": "user", "content": planning_prompt}],
                model=model
            )
            raw_text = plan_res.content

            # Parse JSON array from response
            start_idx = raw_text.find("[")
            end_idx = raw_text.rfind("]")
            if start_idx != -1 and end_idx != -1:
                steps_data = json.loads(raw_text[start_idx:end_idx+1])
                steps = []
                for idx, s in enumerate(steps_data):
                    steps.append(TaskStep(
                        id=idx + 1,
                        agent=s.get("agent", "browser"),
                        action=s.get("action", "navigate"),
                        description=s.get("description", f"Step {idx+1}"),
                        parameters=s.get("parameters", {}),
                        expected_outcome=s.get("expected_outcome", "Step finished")
                    ))
                return TaskPlan(task_id=task_id, description=prompt, steps=steps)
        except Exception as e:
            logger.warning(f"Error generating dynamic plan: {e}")

        # Deterministic fallback plan
        fallback_steps = [
            TaskStep(
                id=1,
                agent="browser",
                action="navigate",
                description=f"Navigate and observe webpage for '{prompt[:40]}'",
                parameters={"url": "https://www.google.com" if "search" in prompt.lower() else "https://example.com"},
                expected_outcome="Target page loaded"
            ),
            TaskStep(
                id=2,
                agent="data",
                action="get_page_content",
                description="Extract visible information from the page",
                parameters={},
                expected_outcome="Content captured"
            ),
            TaskStep(
                id=3,
                agent="verifier",
                action="verify_task",
                description="Verify results and complete task",
                parameters={},
                expected_outcome="Task confirmed completed"
            )
        ]
        return TaskPlan(task_id=task_id, description=prompt, steps=fallback_steps)
