from typing import Dict, Any, Tuple

class ApprovalManager:

    # --- COMET HITL Tier Constants ---
    GREEN_TIER_TOOLS = frozenset([
        "get_page_content", "take_screenshot", "scroll_page", "get_open_tabs",
        "extract_links", "extract_table_data", "wait_for_selector",
        "inspect_visual_chart", "search_web",
    ])

    YELLOW_TIER_TOOLS = frozenset([
        "fill_selector", "fill_input", "open_new_tab", "export_csv", "export_json",
    ])

    RED_TIER_CLICK_KEYWORDS = frozenset([
        "checkout", "purchase", "pay", "place-order", "confirm",
        "delete", "password", "credit", "oauth",
    ])

    RED_TIER_JS_PATTERNS = (
        "fetch(", "XMLHttpRequest", "localStorage.clear",
        "document.cookie", "window.location =",
    )

    @staticmethod
    def evaluate_tool_call(tool_name: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Returns (requires_approval, reason).
        Implements COMET 3-tier HITL security model (GREEN / YELLOW / RED).
        """
        # ---- SKILL TOOLS: Evaluate registered skill risk tiers ----
        try:
            from backend.app.skills.registry import skill_registry
            if skill_registry.is_skill_tool(tool_name):
                tier = skill_registry.get_tool_risk_tier(tool_name)
                if tier == "red":
                    return True, f"RED TIER: Sensitive skill action '{tool_name}' requires explicit user approval."
                elif tier == "yellow":
                    return False, f"YELLOW TIER: Notify - executing skill action '{tool_name}' with user visibility."
                elif tier == "green":
                    return False, f"GREEN TIER: Autonomous execution permitted for '{tool_name}'."
        except Exception:
            pass

        # ---- GREEN TIER: fully autonomous read-only tools ----
        if tool_name in ApprovalManager.GREEN_TIER_TOOLS:
            return False, "GREEN TIER: Autonomous execution permitted."

        # ---- YELLOW TIER: notify-and-execute tools ----
        if tool_name in ApprovalManager.YELLOW_TIER_TOOLS:
            # Still check for sensitive credential content in fill operations
            if tool_name in ("fill_selector", "fill_input"):
                text = str(params.get("text", "")).lower()
                selector = str(params.get("selector", "")).lower()
                if any(k in text for k in ["password", "secret", "cvv", "creditcard", "pin"]):
                    return True, "RED TIER: Sensitive action requires explicit user approval. (Credential in fill value)"
                if any(k in selector for k in ["password", "pwd", "cvv", "creditcard", "pin"]):
                    return True, "RED TIER: Sensitive action requires explicit user approval. (Sensitive selector targeted)"
            return False, "YELLOW TIER: Notify - executing with user visibility."

        # ---- RED TIER: evaluate_javascript script pattern check ----
        if tool_name == "evaluate_javascript":
            script = params.get("script", "")
            for pattern in ApprovalManager.RED_TIER_JS_PATTERNS:
                if pattern in script:
                    return True, (
                        f"RED TIER: Sensitive action requires explicit user approval. "
                        f"(JavaScript contains restricted pattern: '{pattern}')"
                    )
            return False, "GREEN TIER: Autonomous execution permitted."

        # ---- RED TIER: click on sensitive selectors ----
        if tool_name in ("click_element", "click_selector"):
            selector = str(params.get("selector", "")).lower()
            for keyword in ApprovalManager.RED_TIER_CLICK_KEYWORDS:
                if keyword in selector:
                    return True, "RED TIER: Sensitive action requires explicit user approval."
            # Legacy patterns
            if any(k in selector for k in ["submit", "buy-now"]):
                return True, "RED TIER: Sensitive action requires explicit user approval. (Form submission / purchase)"
            return False, "GREEN TIER: Autonomous execution permitted."

        # ---- Legacy: Export CSV (now covered by YELLOW, kept for safety) ----
        if tool_name == "export_csv":
            return False, "YELLOW TIER: Notify - executing with user visibility."

        # ---- Navigation ----
        if tool_name in ["navigate", "switch_tab", "search_web"]:
            url = str(params.get("url", "")).lower()
            if url.startswith("javascript:") or url.startswith("file:"):
                return True, "RED TIER: Sensitive action requires explicit user approval. (Privileged protocol)"
            return False, "GREEN TIER: Autonomous execution permitted."

        # ---- Desktop Automation ----
        if tool_name == "desktop_launch_app":
            app = params.get("app_name", "unknown")
            return True, f"RED TIER: Sensitive action requires explicit user approval. (Launching desktop app '{app}')"

        if tool_name == "desktop_hotkey":
            keys = [k.lower() for k in params.get("keys", [])]
            if any(k in ["f4", "del", "delete"] for k in keys):
                return True, "RED TIER: Sensitive action requires explicit user approval. (System-level termination hotkey)"
            return False, "YELLOW TIER: Notify - executing with user visibility."

        return False, "Action permitted under default security policy."
