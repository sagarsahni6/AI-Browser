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
                from backend.app.search.registry import search_registry
                search_prov = search_registry.get("duckduckgo")
                search_items = await search_prov.search(query, limit=5)
                first_url = search_items[0].url if search_items else f"https://duckduckgo.com/?q={query}"
                await bridge.call("browser.navigate", {"url": first_url})
                return {
                    "status": "success",
                    "search_query": query,
                    "navigated_to": first_url,
                    "results": [
                        {"title": item.title, "url": item.url, "snippet": item.snippet}
                        for item in search_items
                    ]
                }

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

            elif tool_name == "evaluate_javascript":
                script = params.get("script", "")
                res = await bridge.call("browser.evaluate_js", {"script": script})
                return {"status": "success", "result": res}

            elif tool_name == "extract_table_data":
                selector = params.get("selector")
                extract_script = f"""
                (() => {{
                    const table = {f'document.querySelector("{selector}")' if selector else 'document.querySelector("table")'};
                    if (!table) return {{ found: false }};
                    const headers = Array.from(table.querySelectorAll('th')).map(th => th.innerText.trim());
                    const rows = Array.from(table.querySelectorAll('tbody tr')).map(tr => 
                        Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim())
                    ).filter(r => r.length > 0);
                    return {{ found: true, headers, rows: rows.slice(0, 50) }};
                }})()
                """
                res = await bridge.call("browser.evaluate_js", {"script": extract_script})
                return {"status": "success", "data": res}

            elif tool_name == "press_hotkey":
                key = params.get("key", "Enter")
                await bridge.call("browser.press_key", {"key": key})
                return {"status": "success", "key": key}

            elif tool_name == "inspect_visual_chart":
                question = params.get("question", "Describe what is shown in this chart.")
                b64_img = await bridge.call("browser.capture_screenshot", {})
                from backend.app.ai.router import ModelRouter
                v_provider, v_model = ModelRouter.route_for_task(task_type="vision")
                raw_b64 = b64_img.split(",", 1)[-1] if "," in b64_img else b64_img
                vision_messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Examine this browser chart/canvas view. {question}"},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{raw_b64}"}}
                        ]
                    }
                ]
                v_res = await v_provider.chat_completion(messages=vision_messages, model=v_model)
                return {
                    "status": "success",
                    "visual_analysis": v_res.content,
                    "model": v_model
                }

            elif tool_name == "get_open_tabs":
                tabs = await bridge.call("browser.get_tabs", {})
                return {"status": "success", "tabs": tabs}

            elif tool_name == "switch_tab":
                tab_id = params.get("tab_id", "")
                await bridge.call("browser.switch_tab", {"tabId": tab_id})
                return {"status": "success", "switched_to": tab_id}

            elif tool_name == "close_tab":
                tab_id = params.get("tab_id", "")
                await bridge.call("browser.close_tab", {"tabId": tab_id})
                return {"status": "success", "closed_tab": tab_id}

            elif tool_name == "extract_links":
                link_script = """
                (() => {
                    return Array.from(document.querySelectorAll('a[href]'))
                        .map(a => ({ text: a.innerText.trim(), href: a.href }))
                        .filter(a => a.text && (a.href.startsWith('http://') || a.href.startsWith('https://')))
                        .slice(0, 30);
                })()
                """
                links = await bridge.call("browser.evaluate_js", {"script": link_script})
                return {"status": "success", "links": links}

            elif tool_name == "export_json":
                filename = params.get("filename", "agent_export.json")
                data_obj = params.get("data", {})
                out_dir = os.path.join(os.getcwd(), "data")
                os.makedirs(out_dir, exist_ok=True)
                filepath = os.path.join(out_dir, filename)
                import json as py_json
                with open(filepath, "w", encoding="utf-8") as f:
                    py_json.dump(data_obj, f, indent=2, ensure_ascii=False)
                return {"status": "success", "exported_file": filepath}

            elif tool_name == "compare_tabs":
                question = params.get("question", "Compare the content across open tabs.")
                tabs_obs = await bridge.call("browser.inspect_all_tabs", {})
                from backend.app.ai.router import ModelRouter
                p, m = ModelRouter.route_for_task(task_type="reasoning")
                prompt = f"Goal: {question}\n\nTabs Content:\n{tabs_obs}\n\nProvide a structured comparison:"
                res = await p.chat_completion(messages=[{"role": "user", "content": prompt}], model=m)
                return {"status": "success", "comparison": res.content}

            elif tool_name == "click_selector":
                selector = params.get("selector", "")
                res = await bridge.call("browser.click_selector", {"selector": selector})
                if not res or (isinstance(res, dict) and res.get("error")):
                    err_msg = res.get("error") if isinstance(res, dict) else "Failed to click selector"
                    return {"status": "error", "error": err_msg, "selector": selector}
                return {"status": "success", "clicked_selector": selector, "details": res}

            elif tool_name == "dismiss_overlay":
                dismiss_script = """
(() => {
  const selectors = [
    '#onetrust-accept-btn-handler',
    'button[aria-label="Close"]',
    'button[aria-label="Dismiss"]',
    '[class*="cookie"] button',
    '[id*="cookie"] button',
    '[class*="consent"] button',
    '[class*="modal"] button[class*="close"]',
    'button:is([class*="accept"],[class*="agree"],[class*="dismiss"],[class*="close"])'
  ];
  for (const sel of selectors) {
    try {
      const el = document.querySelector(sel);
      if (el && el.offsetParent !== null) { el.click(); return { dismissed: true, selector: sel }; }
    } catch(e) {}
  }
  // Try text match
  const textTargets = ['Accept All', 'Accept Cookies', 'Agree', 'I Accept', 'Got it', 'OK', 'Close'];
  const buttons = Array.from(document.querySelectorAll('button, a[role="button"]'));
  for (const btn of buttons) {
    if (textTargets.some(t => btn.innerText?.trim() === t)) {
      btn.click();
      return { dismissed: true, text: btn.innerText.trim() };
    }
  }
  return { dismissed: false };
})()
"""
                res = await bridge.call("browser.evaluate_js", {"script": dismiss_script})
                return {"status": "success", "dismiss_result": res}

            elif tool_name == "centroid_fallback_click":
                obs = await bridge.call("browser.inspect", {})
                elements = obs.get("interactiveElements", [])
                idx = int(params.get("element_index", 0))
                if idx < len(elements):
                    el = elements[idx]
                    bbox = el.get("bounds") or el.get("boundingBox") or {}
                    x = int(bbox.get("x", 0) + bbox.get("width", 0) / 2)
                    y = int(bbox.get("y", 0) + bbox.get("height", 0) / 2)
                    await bridge.call("browser.click", {"x": x, "y": y})
                    return {
                        "status": "success",
                        "centroid_clicked": {"x": x, "y": y, "element_index": idx}
                    }
                return {
                    "status": "error",
                    "error": f"element_index {idx} out of range (total elements: {len(elements)})"
                }

            elif tool_name == "fill_selector":
                selector = params.get("selector", "")
                text = str(params.get("text", ""))
                res = await bridge.call("browser.fill_selector", {"selector": selector, "text": text})
                if not res or (isinstance(res, dict) and res.get("error")):
                    err_msg = res.get("error") if isinstance(res, dict) else "Failed to fill selector"
                    return {"status": "error", "error": err_msg, "selector": selector}
                return {"status": "success", "filled_selector": selector, "text_length": len(text)}

            elif tool_name == "wait_for_selector":
                selector = params.get("selector", "")
                timeout_ms = int(params.get("timeout_ms", 5000))
                res = await bridge.call("browser.wait_for_selector", {"selector": selector, "timeout_ms": timeout_ms})
                found = res.get("found", False) if isinstance(res, dict) else False
                return {
                    "status": "success" if found else "error",
                    "found": found,
                    "selector": selector,
                    "error": None if found else f"Timeout waiting for selector: {selector}"
                }

            elif tool_name == "detect_forms":
                forms = await bridge.call("browser.detect_forms", {})
                return {"status": "success", "forms": forms or [], "form_count": len(forms or [])}

            elif tool_name == "get_accessibility_tree":
                tree = await bridge.call("browser.get_accessibility_tree", {})
                return {"status": "success", "nodes": tree or []}

            elif tool_name == "read_pdf":
                from backend.app.documents.pdf_service import PDFService
                path_or_url = params.get("path_or_url", "")
                max_pages = int(params.get("max_pages", 50))
                return await PDFService.read_pdf(path_or_url, max_pages)

            elif tool_name == "summarize_pdf":
                from backend.app.documents.pdf_service import PDFService
                path_or_url = params.get("path_or_url", "")
                query = params.get("query")
                return await PDFService.summarize_pdf(path_or_url, query)

            elif tool_name == "extract_table_data":
                from backend.app.agents.data_agent import DataAgent
                return await DataAgent.extract_table_data(
                    selector=params.get("selector"),
                    pagination_next_selector=params.get("pagination_next_selector"),
                    max_pages=int(params.get("max_pages", 1))
                )

            elif tool_name == "export_data":
                from backend.app.agents.data_agent import DataAgent
                return DataAgent.export_data(
                    data=params.get("data", []),
                    format=params.get("format", "json"),
                    filename=params.get("filename")
                )

            elif tool_name == "synthesize_research":
                from backend.app.research.service import ResearchService
                return await ResearchService.synthesize(
                    topic=params.get("topic", ""),
                    sources=params.get("sources"),
                    depth=params.get("depth", "quick")
                )

            elif tool_name == "desktop_click":
                from backend.app.automation.desktop.service import DesktopService
                return await DesktopService.mouse_click(
                    x=int(params.get("x", 0)),
                    y=int(params.get("y", 0)),
                    button=str(params.get("button", "left"))
                )

            elif tool_name == "desktop_type":
                from backend.app.automation.desktop.service import DesktopService
                return await DesktopService.type_text(str(params.get("text", "")))

            elif tool_name == "desktop_hotkey":
                from backend.app.automation.desktop.service import DesktopService
                return await DesktopService.send_hotkey(params.get("keys", []))

            elif tool_name == "desktop_capture_screen":
                from backend.app.automation.desktop.service import DesktopService
                return await DesktopService.capture_screen()

            elif tool_name == "desktop_launch_app":
                from backend.app.automation.desktop.service import DesktopService
                return await DesktopService.launch_app(
                    app_name=str(params.get("app_name", "")),
                    args=params.get("args")
                )

            else:
                return {"status": "error", "message": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"status": "error", "error": str(e)}
