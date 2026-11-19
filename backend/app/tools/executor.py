import os
import csv
from typing import Dict, Any
from backend.app.browser.bridge import bridge
from backend.app.security.approval import ApprovalManager

class ToolExecutor:
    @staticmethod
    async def execute(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # Check security policy
        requires_approval, reason = ApprovalManager.evaluate_tool_call(tool_name, params)
        if requires_approval:
            return {
                "status": "approval_required",
                "tool_name": tool_name,
                "reason": reason,
                "params": params
            }

        try:
            if tool_name == "navigate":
                url = params.get("url", "")
                await bridge.call("browser.navigate", {"url": url})
                return {"status": "success", "navigated_to": url}

            elif tool_name == "get_page_content":
                obs = await bridge.call("browser.inspect", {})
                return {
                    "status": "success",
                    "title": obs.get("title"),
                    "url": obs.get("url"),
                    "element_count": len(obs.get("interactiveElements", [])),
                    "visible_text_snippet": obs.get("visibleText", "")[:1200],
                    "interactive_elements": obs.get("interactiveElements", [])[:30]
                }

            elif tool_name == "take_screenshot":
                screenshot = await bridge.call("browser.capture_screenshot", {})
                return {"status": "success", "screenshot_length": len(screenshot)}

            elif tool_name == "click_element":
                x = int(params.get("x", 0))
                y = int(params.get("y", 0))
                await bridge.call("browser.click", {"x": x, "y": y})
                return {"status": "success", "clicked": {"x": x, "y": y}}

            elif tool_name == "fill_input":
                x = int(params.get("x", 0))
                y = int(params.get("y", 0))
                text = str(params.get("text", ""))
                await bridge.call("browser.fill", {"x": x, "y": y, "text": text})
                return {"status": "success", "filled": {"x": x, "y": y, "text_length": len(text)}}

            elif tool_name == "scroll_page":
                delta_y = int(params.get("delta_y", 400))
                await bridge.call("browser.scroll", {"delta_x": 0, "delta_y": delta_y})
                return {"status": "success", "scrolled": delta_y}

            elif tool_name == "open_new_tab":
                url = params.get("url", "https://example.com")
                tab_id = await bridge.call("browser.create_tab", {"url": url})
                return {"status": "success", "tab_id": tab_id, "url": url}

            elif tool_name == "search_web":
                query = params.get("query", "")
                search_url = f"https://www.google.com/search?q={query}"
                await bridge.call("browser.navigate", {"url": search_url})
                return {"status": "success", "search_query": query, "url": search_url}

            elif tool_name == "export_csv":
                filename = params.get("filename", "agent_export.csv")
                headers = params.get("headers", [])
                rows = params.get("rows", [])

                # Save locally to project data directory
                out_dir = os.path.join(os.getcwd(), "data")
                os.makedirs(out_dir, exist_ok=True)
                filepath = os.path.join(out_dir, filename)

                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    if headers:
                        writer.writerow(headers)
                    writer.writerows(rows)

                return {
                    "status": "success",
                    "exported_file": filepath,
                    "row_count": len(rows)
                }

            else:
                return {"status": "error", "message": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"status": "error", "error": str(e)}
