from typing import Dict, Any, Tuple

class ApprovalManager:
    @staticmethod
    def evaluate_tool_call(tool_name: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Returns (requires_approval, reason)
        """
        # 1. Export CSV
        if tool_name == "export_csv":
            return False, "Exporting structured local CSV is auto-authorized."

        # 2. Form filling: check for sensitive values
        if tool_name == "fill_input":
            text = str(params.get("text", "")).lower()
            if any(k in text for k in ["password", "secret", "cvv", "creditcard", "pin"]):
                return True, "Form input contains potentially sensitive credential or financial information."
            return False, "Standard text input auto-authorized."

        # 3. Read only tools
        if tool_name in ["get_page_content", "take_screenshot", "scroll_page", "get_current_tab", "get_open_tabs"]:
            return False, "Read-only inspection action."

        # 4. Navigation
        if tool_name in ["navigate", "open_new_tab", "switch_tab", "search_web"]:
            url = str(params.get("url", "")).lower()
            if url.startswith("javascript:") or url.startswith("file:"):
                return True, "Navigation to privileged or internal protocol requires explicit user confirmation."
            return False, "Standard web navigation auto-authorized."

        return False, "Action permitted under default security policy."
