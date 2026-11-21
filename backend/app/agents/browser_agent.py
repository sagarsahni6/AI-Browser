import logging
from typing import Dict, Any, Optional, List
from backend.app.tools.executor import ToolExecutor

logger = logging.getLogger("browser_agent")

class BrowserAgent:
    """
    Specialist agent for DOM and visual browser interactions:
    navigating, clicking elements, typing into inputs, scrolling, and keypresses.
    """
    _last_observation: Optional[Dict[str, Any]] = None

    @classmethod
    def set_last_observation(cls, obs: Dict[str, Any]):
        cls._last_observation = obs

    @classmethod
    def _find_matched_element_index(cls, selector: str, elements: List[Dict[str, Any]]) -> Optional[int]:
        if not elements:
            return None

        clean_sel = (selector or "").strip()
        if not clean_sel:
            return None

        lower_sel = clean_sel.lower()

        # 1. Exact selector equality
        for idx, el in enumerate(elements):
            if el.get("selector") == clean_sel:
                return idx

        # 2. Case-insensitive selector match
        for idx, el in enumerate(elements):
            if el.get("selector", "").lower() == lower_sel:
                return idx

        # 3. ID selector match (#id or id attr)
        target_id = clean_sel[1:] if clean_sel.startswith("#") else clean_sel
        for idx, el in enumerate(elements):
            el_id = el.get("id") or ""
            if el_id and el_id == target_id:
                return idx
            if target_id in el.get("selector", ""):
                return idx

        # 4. Text selector matching (text=...)
        if lower_sel.startswith("text="):
            target_text = clean_sel[5:].strip().lower()
            for idx, el in enumerate(elements):
                el_text = (el.get("text") or el.get("label") or "").strip().lower()
                if target_text and (target_text == el_text or target_text in el_text):
                    return idx

        # 5. Substring selector match
        for idx, el in enumerate(elements):
            el_sel = el.get("selector", "")
            if el_sel and (clean_sel in el_sel or el_sel in clean_sel):
                return idx

        # 6. Text / label matching if selector appears to be text
        for idx, el in enumerate(elements):
            el_text = (el.get("text") or el.get("label") or "").strip().lower()
            if el_text and lower_sel in el_text:
                return idx

        return None

    @classmethod
    async def execute_step(cls, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"BrowserAgent executing action '{action}' with params: {parameters}")
        try:
            result = await ToolExecutor.execute(action, parameters)

            if action in ("inspect", "get_page_content") and isinstance(result, dict):
                cls._last_observation = result

            # Self-healing: overlay dismissal on click/fill failures
            if (
                action in ("click_selector", "fill_selector")
                and isinstance(result, dict)
                and result.get("status") == "error"
            ):
                logger.warning(
                    f"BrowserAgent: '{action}' failed — attempting overlay dismissal and retry."
                )
                try:
                    dismiss_result = await ToolExecutor.execute("dismiss_overlay", {})
                    logger.info(f"BrowserAgent: dismiss_overlay result: {dismiss_result}")
                except Exception as dismiss_err:
                    logger.warning(f"BrowserAgent: dismiss_overlay raised: {dismiss_err}")

                # Retry the original action once after dismissal
                retry_result = await ToolExecutor.execute(action, parameters)
                logger.info(f"BrowserAgent: retry '{action}' result: {retry_result}")

                # Third fallback for click_selector: centroid fallback click if retry still errors
                if (
                    action == "click_selector"
                    and isinstance(retry_result, dict)
                    and retry_result.get("status") == "error"
                ):
                    logger.warning(
                        "BrowserAgent: overlay-dismiss retry failed for 'click_selector' — attempting centroid fallback click."
                    )
                    obs = cls._last_observation
                    if not obs or not obs.get("interactiveElements"):
                        try:
                            from backend.app.browser.bridge import bridge
                            obs = await bridge.call("browser.inspect", {})
                            if obs:
                                cls._last_observation = obs
                        except Exception as inspect_err:
                            logger.warning(f"BrowserAgent: inspect failed: {inspect_err}")
                            obs = {}

                    elements = obs.get("interactiveElements", []) if isinstance(obs, dict) else []
                    selector = parameters.get("selector", "")
                    matched_idx = cls._find_matched_element_index(selector, elements)

                    if matched_idx is None and parameters.get("element_index") is not None:
                        try:
                            matched_idx = int(parameters["element_index"])
                        except (ValueError, TypeError):
                            pass

                    if matched_idx is None and elements:
                        matched_idx = 0

                    if matched_idx is not None and elements:
                        logger.info(f"BrowserAgent: executing centroid_fallback_click with element_index={matched_idx}")
                        centroid_result = await ToolExecutor.execute(
                            "centroid_fallback_click",
                            {"element_index": matched_idx}
                        )
                        logger.info(f"BrowserAgent: centroid_fallback_click result: {centroid_result}")
                        return centroid_result

                return retry_result

            return result
        except Exception as e:
            logger.error(f"BrowserAgent failed action '{action}': {e}")
            return {"status": "error", "error": str(e)}
