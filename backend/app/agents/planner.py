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
            f"Available agents & actions:\n"
            f"- 'browser': click_selector (target 'input[name=q]', 'button.submit', 'text=Submit'), fill_selector (target selector + text), wait_for_selector, navigate, click_element (x,y), fill_input (x,y,text), scroll_page, press_hotkey\n"
            f"- 'researcher': search_web, compare_tabs\n"
            f"- 'data': detect_forms, extract_table_data, get_page_content, export_csv, export_json\n"
            f"- 'verifier': verify_task, inspect_visual_chart, take_screenshot\n"
            f"Prefer selector-based DOM actions ('click_selector', 'fill_selector', 'wait_for_selector') over raw coordinates.\n"
            f"Respond with a JSON array of step objects, for example:\n"
            f"[\n"
            f"  {{\"id\": 1, \"agent\": \"browser\", \"action\": \"navigate\", \"description\": \"Navigate to target website\", \"parameters\": {{\"url\": \"https://example.com\"}}, \"expected_outcome\": \"Page loaded\"}},\n"
            f"  {{\"id\": 2, \"agent\": \"browser\", \"action\": \"wait_for_selector\", \"description\": \"Wait for content container\", \"parameters\": {{\"selector\": \"main, #content, body\"}}, \"expected_outcome\": \"Content visible\"}},\n"
            f"  {{\"id\": 3, \"agent\": \"data\", \"action\": \"get_page_content\", \"description\": \"Extract visible information\", \"parameters\": {{}}, \"expected_outcome\": \"Information captured\"}},\n"
            f"  {{\"id\": 4, \"agent\": \"verifier\", \"action\": \"verify_task\", \"description\": \"Verify task completed\", \"parameters\": {{}}, \"expected_outcome\": \"Confirmed complete\"}}\n"
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

    @staticmethod
    async def replan_subgoal(
        task_id: str,
        failed_step: TaskStep,
        error_context: str,
        current_obs: Dict[str, Any],
        remaining_steps: List[TaskStep]
    ) -> List[TaskStep]:
        """
        Dynamically adapts remaining steps when an execution step fails or state does not match expected outcome.
        Returns replacement steps that self-correct and continue towards the goal.
        """
        provider, model = ModelRouter.route_for_task(task_type="tools")

        visible_snippet = (current_obs.get("visibleText") or "")[:500]
        elements_snippet = str(current_obs.get("interactiveElements", []))[:400]

        replan_prompt = (
            f"An autonomous browser agent step failed.\n"
            f"Failed step: [{failed_step.agent}] {failed_step.action} with params: {failed_step.parameters}\n"
            f"Error: {error_context}\n"
            f"Current URL: {current_obs.get('url', 'unknown')}\n"
            f"Visible text snippet: {visible_snippet}\n"
            f"Interactive elements snippet: {elements_snippet}\n"
            f"Remaining planned steps: {[s.description for s in remaining_steps]}\n\n"
            f"Provide 1 to 3 corrective replacement steps in a JSON array. "
            f"For example, if an element was not found, scroll to reveal it, wait for selector, or use a broader selector ('text=...' or alternative tag).\n"
            f"JSON format: [ {{\"agent\": \"browser\", \"action\": \"scroll_page\", \"description\": \"Scroll down to find element\", \"parameters\": {{\"delta_y\": 300}}, \"expected_outcome\": \"Element revealed\"}} ]"
        )

        try:
            res = await provider.chat_completion(
                messages=[{"role": "user", "content": replan_prompt}],
                model=model
            )
            raw = res.content
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1:
                items = json.loads(raw[start:end+1])
                new_steps = []
                base_id = failed_step.id
                for idx, item in enumerate(items):
                    new_steps.append(TaskStep(
                        id=base_id + idx,
                        agent=item.get("agent", "browser"),
                        action=item.get("action", "scroll_page"),
                        description=f"[RECOVERY] {item.get('description', 'Corrective step')}",
                        parameters=item.get("parameters", {}),
                        expected_outcome=item.get("expected_outcome", "State adjusted")
                    ))
                if new_steps:
                    return new_steps
        except Exception as e:
            logger.warning(f"Dynamic replan failed: {e}")

        # Deterministic self-correction fallback: scroll page or wait and retry with alternative selector
        fallback_recovery = [
            TaskStep(
                id=failed_step.id,
                agent="browser",
                action="scroll_page",
                description=f"[RECOVERY] Scroll page to bring elements into view",
                parameters={"delta_y": 300},
                expected_outcome="Viewport scrolled"
            )
        ]
        return fallback_recovery
