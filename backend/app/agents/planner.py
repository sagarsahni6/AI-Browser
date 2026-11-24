import json
import logging
from typing import List, Dict, Any, Optional
from backend.app.agents.models import TaskPlan, TaskStep, PlanStep, StepStatus
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

        active_skills_info = ""
        try:
            from backend.app.skills.registry import skill_registry
            active_skills_info = skill_registry.get_active_system_prompts(prompt)
        except Exception:
            pass

        planning_prompt = (
            f"You are the Multi-Agent Execution Planner. The user wants to accomplish:\n"
            f"\"{prompt}\"\n\n"
            f"Current tab URL: {current_url or 'about:blank'}\n\n"
            f"Break this task into the optimal number of actionable steps according to complexity (no artificial step ceiling).\n"
            f"Available specialist agents & actions:\n"
            f"- 'browser': navigate, click_element, fill_input, scroll_page, open_new_tab, press_hotkey\n"
            f"- 'dom': click_selector, fill_selector, wait_for_selector, detect_form_fields, get_accessibility_tree\n"
            f"- 'vision': inspect_visual_chart, locate_element_visually, verify_visual_state\n"
            f"- 'desktop': desktop_click, desktop_type, desktop_hotkey, desktop_capture_screen, desktop_launch_app\n"
            f"- 'file': read_file, write_file, read_pdf, summarize_pdf\n"
            f"- 'memory': store_memory, retrieve_memory, get_context\n"
            f"- 'recovery': diagnose_failure, dismiss_overlays, suggest_recovery_steps\n"
            f"- 'data': detect_forms, extract_table_data, get_page_content, export_csv, export_data\n"
            f"- 'researcher': search_web, synthesize_research\n"
            f"- 'verifier': verify_task, verify_dom_assertion, verify_url_match, verify_data_validation, verify_file_validation, verify_form_submission\n"
            f"{active_skills_info}\n"
            f"Verification strategies: dom_assertion, url_match, data_validation, file_validation, form_submission, or none.\n"
            f"Respond with a JSON array of step objects, for example:\n"
            f"[\n"
            f"  {{\"id\": 1, \"agent\": \"browser\", \"action\": \"navigate\", \"description\": \"Navigate to target website\", \"parameters\": {{\"url\": \"https://example.com\"}}, \"dependencies\": [], \"verification_strategy\": \"url_match\", \"verification_params\": {{\"expected_url_pattern\": \"example.com\"}}, \"expected_outcome\": \"Page loaded\"}},\n"
            f"  {{\"id\": 2, \"agent\": \"dom\", \"action\": \"wait_for_selector\", \"description\": \"Wait for content container\", \"parameters\": {{\"selector\": \"main, #content, body\"}}, \"dependencies\": [1], \"verification_strategy\": \"dom_assertion\", \"verification_params\": {{\"selector\": \"main, #content, body\"}}, \"expected_outcome\": \"Content visible\"}},\n"
            f"  {{\"id\": 3, \"agent\": \"data\", \"action\": \"get_page_content\", \"description\": \"Extract visible information\", \"parameters\": {{}}, \"dependencies\": [2], \"verification_strategy\": \"data_validation\", \"verification_params\": {{\"min_length\": 10}}, \"expected_outcome\": \"Information captured\"}},\n"
            f"  {{\"id\": 4, \"agent\": \"verifier\", \"action\": \"verify_task\", \"description\": \"Verify task completed\", \"parameters\": {{}}, \"dependencies\": [3], \"verification_strategy\": \"none\", \"verification_params\": {{}}, \"expected_outcome\": \"Confirmed complete\"}}\n"
            f"]"
        )

        try:
            plan_res = await provider.chat_completion(
                messages=[{"role": "user", "content": planning_prompt}],
                model=model
            )
            raw_text = plan_res.content or ""

            # Parse JSON array from response containing step objects
            import re
            json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_text, re.DOTALL)
            if json_match:
                steps_data = json.loads(json_match.group(0))
                steps = []
                for idx, s in enumerate(steps_data):
                    steps.append(TaskStep(
                        id=s.get("id") or (idx + 1),
                        agent=s.get("agent", "browser"),
                        action=s.get("action", "navigate"),
                        description=s.get("description", f"Step {idx+1}"),
                        parameters=s.get("parameters", {}),
                        dependencies=s.get("dependencies", []),
                        verification_strategy=s.get("verification_strategy", "none"),
                        verification_params=s.get("verification_params", {}),
                        expected_outcome=s.get("expected_outcome", "Step finished")
                    ))
                if steps:
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
