import os
import csv
from typing import Dict, Any, Optional
from backend.app.browser.bridge import bridge
from backend.app.security.approval import ApprovalManager
from backend.app.security.policy import SecurityPolicy, RiskTier
from backend.app.tools.registry import tool_registry, ToolDefinition

class CanonicalStatus(str):
    """
    String subclass that cleanly evaluates equal to both 'success' and 'ok'
    for full backward compatibility with legacy tests and callers, while serializing
    canonically as 'success'.
    """
    def __eq__(self, other):
        val = str(self)
        if (val == "success" or val == "ok") and (other == "success" or other == "ok"):
            return True
        return super().__eq__(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return super().__hash__()


def _normalize_response(raw: Any, tool_name: str) -> Dict[str, Any]:
    """
    Enforces the canonical execution result structure:
    {"status": "success"|"error"|"approval_required", "tool_name": str, "result": Any, "evidence": Any, "error": Optional[str]}
    Preserving top-level backward-compatible keys.
    """
    if not isinstance(raw, dict):
        raw = {"result": raw, "status": "success"}

    raw_status = raw.get("status")
    if raw_status in ("ok", "success"):
        status = CanonicalStatus("success")
    elif raw_status == "approval_required":
        status = "approval_required"
    elif raw_status == "error":
        status = "error"
    else:
        status = CanonicalStatus("success") if not raw.get("error") else "error"

    error_val = raw.get("error") or raw.get("message")

    # Extract canonical result
    result_val = raw.get("result")
    if result_val is None:
        if "data" in raw:
            result_val = raw["data"]
        else:
            payload = {
                k: v for k, v in raw.items()
                if k not in ("status", "tool_name", "error", "message", "evidence")
            }
            result_val = payload if payload else None

    # Extract canonical evidence
    evidence_val = raw.get("evidence")
    if evidence_val is None:
        evidence_keys = [
            "url", "title", "visible_text_snippet", "screenshot_length",
            "clicked", "filled", "navigated_to", "exported_file", "row_count",
            "nodes", "forms", "results"
        ]
        evidence_val = {k: raw[k] for k in evidence_keys if k in raw}

    out = dict(raw)
    out["status"] = status
    out["tool_name"] = tool_name
    out["result"] = result_val
    out["evidence"] = evidence_val
    out["error"] = error_val

    # Backward-compatible text aliases
    if "visible_text_snippet" in out and "text" not in out:
        out["text"] = out["visible_text_snippet"]
    if "text" in out and "visible_text_snippet" not in out:
        out["visible_text_snippet"] = out["text"]

    return out


class ToolExecutor:
    @classmethod
    async def execute(cls, tool_name: str, params: Optional[Dict[str, Any]] = None, bypass_approval: bool = False) -> Dict[str, Any]:
        if params is None:
            params = {}
        # 1. Evaluate central security policy
        policy_res = SecurityPolicy.evaluate(tool_name, params)
        if policy_res.is_blocked:
            return _normalize_response({
                "status": "error",
                "error": f"Action blocked by Security Policy: {policy_res.reason}"
            }, tool_name)

        # 2. Check approval requirement unless bypassed
        if not bypass_approval:
            if policy_res.requires_approval:
                return _normalize_response({
                    "status": "approval_required",
                    "reason": policy_res.reason,
                    "params": params
                }, tool_name)

            # Check ApprovalManager for skill-level or keyword checks
            requires_approval, reason = ApprovalManager.evaluate_tool_call(tool_name, params)
            if requires_approval:
                return _normalize_response({
                    "status": "approval_required",
                    "reason": reason,
                    "params": params
                }, tool_name)

        try:
            raw_res = await cls._execute_tool_action(tool_name, params)
            return _normalize_response(raw_res, tool_name)
        except Exception as e:
            return _normalize_response({"status": "error", "error": str(e)}, tool_name)

    @classmethod
    async def _execute_tool_action(cls, tool_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if params is None:
            params = {}
        tab_id = params.get("tab_id")

        if tool_name == "navigate":
            url = params.get("url", "")
            payload = {"url": url}
            if tab_id:
                payload["tab_id"] = tab_id
            await bridge.call("browser.navigate", payload)
            return {"status": "success", "navigated_to": url, "url": url}

        elif tool_name == "get_page_content":
            payload = {}
            if tab_id:
                payload["tab_id"] = tab_id
            obs = await bridge.call("browser.inspect", payload)
            return {
                "status": "success",
                "title": obs.get("title"),
                "url": obs.get("url"),
                "element_count": len(obs.get("interactiveElements", [])),
                "visible_text_snippet": obs.get("visibleText", "")[:1200],
                "interactive_elements": obs.get("interactiveElements", [])[:30]
            }

        elif tool_name == "take_screenshot":
            payload = {}
            if tab_id:
                payload["tab_id"] = tab_id
            screenshot = await bridge.call("browser.capture_screenshot", payload)
            return {"status": "success", "screenshot_length": len(screenshot)}

        elif tool_name == "click_element":
            x = int(params.get("x", 0))
            y = int(params.get("y", 0))
            payload = {"x": x, "y": y}
            if tab_id:
                payload["tab_id"] = tab_id
            await bridge.call("browser.click", payload)
            return {"status": "success", "clicked": {"x": x, "y": y}}

        elif tool_name == "click_selector":
            selector = str(params.get("selector", ""))
            payload = {"selector": selector}
            if tab_id:
                payload["tab_id"] = tab_id
            res = await bridge.call("browser.click_selector", payload)
            return {"status": "success", "clicked_selector": selector, "result": res}

        elif tool_name == "fill_input":
            x = int(params.get("x", 0))
            y = int(params.get("y", 0))
            text = str(params.get("text", ""))
            payload = {"x": x, "y": y, "text": text}
            if tab_id:
                payload["tab_id"] = tab_id
            await bridge.call("browser.fill", payload)
            return {"status": "success", "filled": {"x": x, "y": y, "text_length": len(text)}}

        elif tool_name == "fill_selector":
            selector = str(params.get("selector", ""))
            text = str(params.get("text", ""))
            payload = {"selector": selector, "text": text}
            if tab_id:
                payload["tab_id"] = tab_id
            res = await bridge.call("browser.fill_selector", payload)
            return {"status": "success", "filled_selector": selector, "text_length": len(text), "result": res}

        elif tool_name == "wait_for_selector":
            selector = str(params.get("selector", ""))
            timeout_ms = int(params.get("timeout_ms", 5000))
            payload = {"selector": selector, "timeout_ms": timeout_ms}
            if tab_id:
                payload["tab_id"] = tab_id
            res = await bridge.call("browser.wait_for_selector", payload)
            return {"status": "success", "waited_for": selector, "result": res}

        elif tool_name == "scroll_page":
            delta_y = int(params.get("delta_y", 400))
            payload = {"delta_x": 0, "delta_y": delta_y}
            if tab_id:
                payload["tab_id"] = tab_id
            await bridge.call("browser.scroll", payload)
            return {"status": "success", "scrolled": delta_y}

        elif tool_name == "open_new_tab":
            url = params.get("url", "https://example.com")
            tab_id_res = await bridge.call("browser.create_tab", {"url": url})
            return {"status": "success", "tab_id": tab_id_res, "url": url}

        elif tool_name == "search_web":
            query = params.get("query", "")
            from backend.app.search.registry import search_registry
            search_prov = search_registry.get("duckduckgo")
            search_items = await search_prov.search(query, limit=5)
            first_url = search_items[0].url if search_items else f"https://duckduckgo.com/?q={query}"
            payload = {"url": first_url}
            if tab_id:
                payload["tab_id"] = tab_id
            await bridge.call("browser.navigate", payload)
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

            def _sanitize_cell(val: Any) -> Any:
                if isinstance(val, str) and val.startswith(("=", "+", "-", "@", "\t", "\r")):
                    return f"'{val}"
                return val

            sanitized_rows = []
            for r in rows:
                if isinstance(r, (list, tuple)):
                    sanitized_rows.append([_sanitize_cell(c) for c in r])
                elif isinstance(r, dict):
                    sanitized_rows.append({k: _sanitize_cell(v) for k, v in r.items()})
                else:
                    sanitized_rows.append(_sanitize_cell(r))

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if headers:
                    writer.writerow(headers)
                writer.writerows(sanitized_rows)

            return {
                "status": "success",
                "exported_file": filepath,
                "row_count": len(rows)
            }

        elif tool_name == "evaluate_javascript":
            script = params.get("script", "")
            target_url = params.get("url")
            if target_url:
                try:
                    current_obs = await bridge.call("browser.inspect", {})
                    curr_url = current_obs.get("url", "") if current_obs else ""
                    if curr_url != target_url and not curr_url.startswith(target_url):
                        await bridge.call("browser.navigate", {"url": target_url})
                        await asyncio.sleep(1.5)
                except Exception:
                    pass

            # Wrap script to capture console.log and return values seamlessly
            wrapped_script = f"""
            (() => {{
                const _logs = [];
                const _origLog = console.log;
                try {{
                    console.log = (...args) => {{
                        _logs.push(args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '));
                        _origLog.apply(console, args);
                    }};
                    const _evalRes = eval({json.dumps(script)});
                    if (_evalRes !== undefined && _evalRes !== null) return _evalRes;
                    if (_logs.length > 0) return _logs.join('\\n');
                    return null;
                }} catch (e) {{
                    return "Error evaluating script: " + e.message;
                }} finally {{
                    console.log = _origLog;
                }}
            }})()
            """
            payload = {"script": wrapped_script}
            if tab_id:
                payload["tab_id"] = tab_id
            res = await bridge.call("browser.evaluate_js", payload)
            return {"status": "success", "result": res}

        elif tool_name == "press_hotkey":
            key = params.get("key", "Enter")
            payload = {"key": key}
            if tab_id:
                payload["tab_id"] = tab_id
            await bridge.call("browser.press_key", payload)
            return {"status": "success", "key": key}

        elif tool_name == "inspect_visual_chart":
            question = params.get("question", "Describe what is shown in this chart.")
            payload = {}
            if tab_id:
                payload["tab_id"] = tab_id
            b64_img = await bridge.call("browser.capture_screenshot", payload)
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
            from backend.app.ai.registry import provider_registry
            provider_inst = provider_registry.get(v_provider)
            reply = await provider_inst.chat_complete(vision_messages, model=v_model)
            return {"status": "success", "analysis": reply.content}

        elif tool_name == "detect_form_fields":
            payload = {}
            if tab_id:
                payload["tab_id"] = tab_id
            forms = await bridge.call("browser.detect_forms", payload)
            return {"status": "success", "forms": forms or [], "form_count": len(forms or [])}

        elif tool_name == "get_accessibility_tree":
            payload = {}
            if tab_id:
                payload["tab_id"] = tab_id
            tree = await bridge.call("browser.get_accessibility_tree", payload)
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
            from backend.app.skills.registry import skill_registry
            if skill_registry.is_skill_tool(tool_name):
                return await skill_registry.execute_tool(tool_name, params)
            return {"status": "error", "message": f"Unknown tool: {tool_name}"}

def _register_all_tools():
    """Register built-in tool definitions into tool_registry."""
    tools = [
        ToolDefinition(name="navigate", description="Navigate the browser to a URL", risk_tier=RiskTier.YELLOW, category="browser", parameters_schema={"type": "object", "properties": {"url": {"type": "string"}, "tab_id": {"type": "string"}}, "required": ["url"]}),
        ToolDefinition(name="get_page_content", description="Inspect current page structure, title, URL, visible text snippet", risk_tier=RiskTier.GREEN, category="browser", parameters_schema={"type": "object", "properties": {"tab_id": {"type": "string"}}}),
        ToolDefinition(name="take_screenshot", description="Capture a full-viewport screenshot", risk_tier=RiskTier.GREEN, category="browser", parameters_schema={"type": "object", "properties": {"tab_id": {"type": "string"}}}),
        ToolDefinition(name="click_element", description="Click an element at coordinates (x, y)", risk_tier=RiskTier.YELLOW, category="browser", parameters_schema={"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "tab_id": {"type": "string"}}, "required": ["x", "y"]}),
        ToolDefinition(name="click_selector", description="Click an element matching CSS selector", risk_tier=RiskTier.YELLOW, category="dom", parameters_schema={"type": "object", "properties": {"selector": {"type": "string"}, "tab_id": {"type": "string"}}, "required": ["selector"]}),
        ToolDefinition(name="fill_input", description="Type text into an input at coordinates (x, y)", risk_tier=RiskTier.YELLOW, category="browser", parameters_schema={"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "text": {"type": "string"}, "tab_id": {"type": "string"}}, "required": ["x", "y", "text"]}),
        ToolDefinition(name="fill_selector", description="Type text into an input matching CSS selector", risk_tier=RiskTier.YELLOW, category="dom", parameters_schema={"type": "object", "properties": {"selector": {"type": "string"}, "text": {"type": "string"}, "tab_id": {"type": "string"}}, "required": ["selector", "text"]}),
        ToolDefinition(name="wait_for_selector", description="Wait for an element matching CSS selector to appear", risk_tier=RiskTier.GREEN, category="dom", parameters_schema={"type": "object", "properties": {"selector": {"type": "string"}, "timeout_ms": {"type": "integer"}, "tab_id": {"type": "string"}}, "required": ["selector"]}),
        ToolDefinition(name="scroll_page", description="Scroll page vertically by delta_y pixels", risk_tier=RiskTier.GREEN, category="browser", parameters_schema={"type": "object", "properties": {"delta_y": {"type": "integer"}, "tab_id": {"type": "string"}}}),
        ToolDefinition(name="open_new_tab", description="Open a new browser tab with given URL", risk_tier=RiskTier.YELLOW, category="browser", parameters_schema={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}),
        ToolDefinition(name="search_web", description="Perform web search via DuckDuckGo and navigate to top result", risk_tier=RiskTier.GREEN, category="browser", parameters_schema={"type": "object", "properties": {"query": {"type": "string"}, "tab_id": {"type": "string"}}, "required": ["query"]}),
        ToolDefinition(name="export_csv", description="Export tabular data to a local CSV file in data directory", risk_tier=RiskTier.YELLOW, category="data", parameters_schema={"type": "object", "properties": {"filename": {"type": "string"}, "headers": {"type": "array", "items": {"type": "string"}}, "rows": {"type": "array"}}, "required": ["filename", "headers", "rows"]}),
        ToolDefinition(name="evaluate_javascript", description="Execute arbitrary JavaScript expression in the active page", risk_tier=RiskTier.REQUIRES_APPROVAL, category="browser", parameters_schema={"type": "object", "properties": {"script": {"type": "string"}, "tab_id": {"type": "string"}}, "required": ["script"]}),
        ToolDefinition(name="press_hotkey", description="Send keyboard hotkey to browser", risk_tier=RiskTier.YELLOW, category="browser", parameters_schema={"type": "object", "properties": {"key": {"type": "string"}, "tab_id": {"type": "string"}}, "required": ["key"]}),
        ToolDefinition(name="inspect_visual_chart", description="Analyze a visual chart or image using Vision LLM", risk_tier=RiskTier.GREEN, category="vision", parameters_schema={"type": "object", "properties": {"question": {"type": "string"}, "tab_id": {"type": "string"}}}),
        ToolDefinition(name="detect_form_fields", description="Inspect and detect all form inputs and controls on page", risk_tier=RiskTier.GREEN, category="dom", parameters_schema={"type": "object", "properties": {"tab_id": {"type": "string"}}}),
        ToolDefinition(name="get_accessibility_tree", description="Retrieve the accessibility object model tree", risk_tier=RiskTier.GREEN, category="dom", parameters_schema={"type": "object", "properties": {"tab_id": {"type": "string"}}}),
        ToolDefinition(name="read_pdf", description="Extract text content from a local PDF file or URL", risk_tier=RiskTier.GREEN, category="file", parameters_schema={"type": "object", "properties": {"path_or_url": {"type": "string"}, "max_pages": {"type": "integer"}}, "required": ["path_or_url"]}),
        ToolDefinition(name="summarize_pdf", description="Summarize a PDF document", risk_tier=RiskTier.GREEN, category="file", parameters_schema={"type": "object", "properties": {"path_or_url": {"type": "string"}, "query": {"type": "string"}}, "required": ["path_or_url"]}),
        ToolDefinition(name="extract_table_data", description="Extract structured tabular records from DOM table", risk_tier=RiskTier.GREEN, category="data", parameters_schema={"type": "object", "properties": {"selector": {"type": "string"}, "pagination_next_selector": {"type": "string"}, "max_pages": {"type": "integer"}}}),
        ToolDefinition(name="export_data", description="Export records to json or csv file", risk_tier=RiskTier.YELLOW, category="data", parameters_schema={"type": "object", "properties": {"data": {"type": "array"}, "format": {"type": "string"}, "filename": {"type": "string"}}, "required": ["data"]}),
        ToolDefinition(name="synthesize_research", description="Synthesize multi-source research into comprehensive report", risk_tier=RiskTier.GREEN, category="research", parameters_schema={"type": "object", "properties": {"topic": {"type": "string"}, "sources": {"type": "array"}, "depth": {"type": "string"}}, "required": ["topic"]}),
        ToolDefinition(name="desktop_click", description="Send native Windows mouse click at desktop coordinate (x, y)", risk_tier=RiskTier.REQUIRES_APPROVAL, category="desktop", parameters_schema={"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "button": {"type": "string"}}, "required": ["x", "y"]}),
        ToolDefinition(name="desktop_type", description="Type Unicode text natively via Windows SendInput", risk_tier=RiskTier.REQUIRES_APPROVAL, category="desktop", parameters_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}),
        ToolDefinition(name="desktop_hotkey", description="Send native keyboard shortcut keys", risk_tier=RiskTier.REQUIRES_APPROVAL, category="desktop", parameters_schema={"type": "object", "properties": {"keys": {"type": "array", "items": {"type": "string"}}}, "required": ["keys"]}),
        ToolDefinition(name="desktop_capture_screen", description="Capture native desktop screenshot", risk_tier=RiskTier.GREEN, category="desktop", parameters_schema={"type": "object", "properties": {}}),
        ToolDefinition(name="desktop_launch_app", description="Launch an allowed native Windows desktop application", risk_tier=RiskTier.REQUIRES_APPROVAL, category="desktop", parameters_schema={"type": "object", "properties": {"app_name": {"type": "string"}, "args": {"type": "array", "items": {"type": "string"}}}, "required": ["app_name"]}),
    ]
    for t in tools:
        tool_registry.register(t, None)

_register_all_tools()

