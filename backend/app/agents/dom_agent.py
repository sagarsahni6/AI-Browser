import logging
from typing import Dict, Any, Optional, List
from backend.app.browser.bridge import bridge
from backend.app.tools.executor import _normalize_response

logger = logging.getLogger("dom_agent")

class DOMAgent:
    """
    Specialist agent for DOM inspection, selector waterfall resolution,
    form structure extraction, and accessibility tree parsing.
    """

    @classmethod
    async def execute_step(cls, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        tab_id = parameters.get("tab_id")

        if action == "click_selector":
            selector = str(parameters.get("selector", ""))
            payload = {"selector": selector}
            if tab_id:
                payload["tab_id"] = tab_id
            res = await bridge.call("browser.click_selector", payload)
            return _normalize_response({"status": "success", "selector": selector, "result": res}, action)

        elif action == "fill_selector":
            selector = str(parameters.get("selector", ""))
            text = str(parameters.get("text", ""))
            payload = {"selector": selector, "text": text}
            if tab_id:
                payload["tab_id"] = tab_id
            res = await bridge.call("browser.fill_selector", payload)
            return _normalize_response({"status": "success", "selector": selector, "text_length": len(text), "result": res}, action)

        elif action == "wait_for_selector":
            selector = str(parameters.get("selector", ""))
            timeout_ms = int(parameters.get("timeout_ms", 5000))
            payload = {"selector": selector, "timeout_ms": timeout_ms}
            if tab_id:
                payload["tab_id"] = tab_id
            res = await bridge.call("browser.wait_for_selector", payload)
            return _normalize_response({"status": "success", "selector": selector, "result": res}, action)

        elif action in ("detect_forms", "detect_form_fields"):
            payload = {}
            if tab_id:
                payload["tab_id"] = tab_id
            forms = await bridge.call("browser.detect_forms", payload)
            return _normalize_response({"status": "success", "forms": forms or [], "form_count": len(forms or [])}, action)

        elif action == "get_accessibility_tree":
            payload = {}
            if tab_id:
                payload["tab_id"] = tab_id
            tree = await bridge.call("browser.get_accessibility_tree", payload)
            return _normalize_response({"status": "success", "nodes": tree or []}, action)

        elif action == "resolve_selector":
            description = str(parameters.get("description", ""))
            resolved = await cls.resolve_selector(description, tab_id)
            return _normalize_response({"status": "success", "resolved_selector": resolved}, action)

        elif action == "inspect_structure":
            selector = str(parameters.get("selector", "body"))
            payload = {"script": f"document.querySelector('{selector}') ? document.querySelector('{selector}').outerHTML.substring(0, 2000) : null"}
            if tab_id:
                payload["tab_id"] = tab_id
            html = await bridge.call("browser.evaluate_js", payload)
            return _normalize_response({"status": "success", "html_snippet": html}, action)

        else:
            from backend.app.tools.executor import ToolExecutor
            return await ToolExecutor.execute(action, parameters)

    @classmethod
    async def resolve_selector(cls, description: str, tab_id: Optional[str] = None) -> str:
        """
        Selector Priority Waterfall:
        1. #id exact match
        2. [data-testid] or [data-test-id]
        3. [name] attribute
        4. [aria-label] or [placeholder]
        5. text=... text content
        6. Centroid or fallback tag
        """
        desc_lower = description.lower().strip()
        if desc_lower.startswith("#") or desc_lower.startswith(".") or "[" in desc_lower:
            return description

        # Check interactive elements
        payload = {}
        if tab_id:
            payload["tab_id"] = tab_id
        try:
            obs = await bridge.call("browser.inspect", payload)
            elements = obs.get("interactiveElements", []) if obs else []
            for el in elements:
                tag = (el.get("tag") or "").lower()
                text = (el.get("text") or "").lower()
                aria = (el.get("ariaLabel") or "").lower()
                name = (el.get("name") or "").lower()

                if desc_lower in text:
                    return f"{tag}:has-text('{el.get('text')}')"
                if desc_lower in aria:
                    return f"[aria-label*='{el.get('ariaLabel')}']"
                if desc_lower in name:
                    return f"[name='{el.get('name')}']"
        except Exception as e:
            logger.debug(f"Selector resolution inspection error: {e}")

        return f"text={description}"
