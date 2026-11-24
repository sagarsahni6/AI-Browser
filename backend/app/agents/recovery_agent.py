import logging
from typing import Dict, Any, Optional, List
from backend.app.browser.bridge import bridge
from backend.app.tools.executor import _normalize_response

logger = logging.getLogger("recovery_agent")

class RecoveryAgent:
    """
    Specialist agent for error diagnosis, overlay dismissal (cookie banners,
    modal backdrops), and autonomous self-healing recovery actions.
    """

    OVERLAY_SELECTORS = [
        "button[aria-label*='close' i]",
        "button[aria-label*='dismiss' i]",
        "[id*='cookie' i] button",
        "[class*='cookie' i] button",
        "button:has-text('Accept all')",
        "button:has-text('Accept All')",
        "button:has-text('I agree')",
        "button:has-text('Got it')",
        "button:has-text('Close')",
        ".modal-backdrop",
        "[role='dialog'] button.close"
    ]

    @classmethod
    async def execute_step(cls, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        tab_id = parameters.get("tab_id")

        if action == "dismiss_overlays":
            res = await cls.dismiss_overlays(tab_id)
            return _normalize_response(res, action)

        elif action == "diagnose_failure":
            failed_action = parameters.get("action", "")
            error = parameters.get("error", "")
            obs = parameters.get("observation", {})
            res = cls.diagnose_failure(failed_action, parameters.get("parameters", {}), error, obs)
            return _normalize_response(res, action)

        elif action == "suggest_recovery_steps":
            failed_step = parameters.get("failed_step", {})
            error = parameters.get("error", "")
            obs = parameters.get("observation", {})
            res = cls.suggest_recovery_steps(failed_step, error, obs)
            return _normalize_response(res, action)

        else:
            from backend.app.tools.executor import ToolExecutor
            return await ToolExecutor.execute(action, parameters)

    @classmethod
    async def dismiss_overlays(cls, tab_id: Optional[str] = None) -> Dict[str, Any]:
        """Attempts to click dismiss buttons or clear overlays across the active view."""
        dismissed_count = 0
        for sel in cls.OVERLAY_SELECTORS:
            try:
                payload = {"selector": sel}
                if tab_id:
                    payload["tab_id"] = tab_id
                res = await bridge.call("browser.click_selector", payload)
                if res and res.get("status") in ("success", "ok"):
                    dismissed_count += 1
            except Exception:
                pass

        # Try JavaScript escape key or backdrop removal
        try:
            js_payload = {
                "script": (
                    "const backdrops = document.querySelectorAll('.modal-backdrop, [class*=\"backdrop\"]');"
                    "backdrops.forEach(b => b.remove());"
                    "return backdrops.length;"
                )
            }
            if tab_id:
                js_payload["tab_id"] = tab_id
            removed = await bridge.call("browser.evaluate_js", js_payload)
            if removed and isinstance(removed, int) and removed > 0:
                dismissed_count += removed
        except Exception:
            pass

        return {
            "status": "success",
            "dismissed_overlays": dismissed_count > 0,
            "count": dismissed_count
        }

    @classmethod
    def diagnose_failure(cls, action: str, params: Dict[str, Any], error: str, obs: Dict[str, Any]) -> Dict[str, Any]:
        err_lower = error.lower()
        diagnosis = "unknown_failure"
        suggestion = "retry"

        if "not found" in err_lower or "no element" in err_lower:
            diagnosis = "element_not_found"
            suggestion = "try scrolling or broader selector"
        elif "timeout" in err_lower:
            diagnosis = "operation_timeout"
            suggestion = "wait for page load or increase timeout"
        elif "intercepted" in err_lower or "obscured" in err_lower or "overlay" in err_lower:
            diagnosis = "element_obscured_by_overlay"
            suggestion = "dismiss overlays and retry"
        elif "origin mismatch" in err_lower:
            diagnosis = "origin_barrier_violation"
            suggestion = "security boundary violation: abort"

        return {
            "status": "success",
            "diagnosis": diagnosis,
            "suggestion": suggestion,
            "original_error": error
        }

    @classmethod
    def suggest_recovery_steps(cls, failed_step: Dict[str, Any], error: str, obs: Dict[str, Any]) -> Dict[str, Any]:
        diag = cls.diagnose_failure(
            failed_step.get("action", ""),
            failed_step.get("parameters", {}),
            error,
            obs
        )
        steps = []
        if diag["diagnosis"] == "element_obscured_by_overlay":
            steps.append({"agent": "recovery", "action": "dismiss_overlays", "parameters": {}})
            steps.append(failed_step)
        elif diag["diagnosis"] == "element_not_found":
            steps.append({"agent": "browser", "action": "scroll_page", "parameters": {"delta_y": 300}})
            steps.append(failed_step)
        else:
            steps.append({"agent": "recovery", "action": "dismiss_overlays", "parameters": {}})
            steps.append(failed_step)

        return {
            "status": "success",
            "suggested_steps": steps,
            "diagnosis": diag["diagnosis"]
        }
