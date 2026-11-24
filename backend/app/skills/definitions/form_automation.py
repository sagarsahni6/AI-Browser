from typing import Dict, Any, List
from backend.app.skills.base import BaseSkill, SkillManifest, SkillTool
from backend.app.browser.bridge import bridge


class FormAutomationSkill(BaseSkill):
    def __init__(self):
        self.manifest = SkillManifest(
            id="form_automation",
            name="Smart Form Automation & Autofill",
            description="Deep semantic form detection, profile-based autofill, radio/select handling, and gated submission.",
            category="automation",
            icon="FileCheck",
            enabled=True,
            triggers=[
                "fill form", "autofill", "submit form", "registration",
                "checkout", "signup", "login form", "input data", "fill input", "form"
            ],
            tools=[
                SkillTool(
                    name="analyze_form_fields",
                    description="Inspect and return all form fields, labels, input types, required flags, and current values on the active page.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "form_selector": {"type": "string", "description": "Optional selector for a specific form container."}
                        }
                    },
                    risk_tier="green"
                ),
                SkillTool(
                    name="autofill_form",
                    description="Smartly populate multiple form fields using a key-value dictionary of values mapped to field labels or names.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "field_values": {
                                "type": "object",
                                "description": "Key-value mapping of field labels/names to text values (e.g. {'Name': 'Alex Doe', 'Email': 'alex@example.com'})."
                            },
                            "form_selector": {"type": "string", "description": "Optional form selector."}
                        },
                        "required": ["field_values"]
                    },
                    risk_tier="yellow"
                ),
                SkillTool(
                    name="submit_form",
                    description="Submit the form. Financial or credential submissions automatically require human approval.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "submit_button_selector": {"type": "string", "description": "Selector for the submit button (e.g. 'button[type=submit]')."},
                            "is_financial_or_auth": {"type": "boolean", "description": "True if form contains passwords, payment or critical auth data."}
                        }
                    },
                    risk_tier="red"
                )
            ]
        )

    def get_system_prompt_snippet(self) -> str:
        return (
            "When encountering web forms, first call `analyze_form_fields` to inspect all fields, types, and labels. "
            "Use `autofill_form` to fill in non-sensitive fields. For final submission, use `submit_form`."
        )

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "analyze_form_fields":
            form_sel = params.get("form_selector")
            script = f"""
            (() => {{
                const root = {f'document.querySelector("{form_sel}")' if form_sel else 'document'};
                if (!root) return {{ found: false, fields: [] }};
                const inputs = Array.from(root.querySelectorAll('input, select, textarea'));
                const fields = inputs.map((el, i) => {{
                    let label = "";
                    if (el.id) {{
                        const lbl = document.querySelector(`label[for="${{el.id}}"]`);
                        if (lbl) label = lbl.innerText.trim();
                    }}
                    if (!label && el.closest('label')) label = el.closest('label').innerText.trim();
                    if (!label) label = el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.name || "";
                    
                    return {{
                        index: i,
                        tag: el.tagName.toLowerCase(),
                        type: el.type || 'text',
                        name: el.name || '',
                        id: el.id || '',
                        label: label,
                        placeholder: el.placeholder || '',
                        required: el.required || false,
                        value: el.value || '',
                        disabled: el.disabled || false
                    }};
                }});
                return {{ found: true, field_count: fields.length, fields }};
            }})()
            """
            res = await bridge.call("browser.evaluate_js", {"script": script})
            return {"status": "success", "form_analysis": res}

        elif tool_name == "autofill_form":
            values = params.get("field_values", {})
            form_sel = params.get("form_selector")
            payload_json = json.dumps(values)

            script = f"""
            (() => {{
                const root = {f'document.querySelector("{form_sel}")' if form_sel else 'document'};
                if (!root) return {{ success: false, error: "Form root not found" }};
                const values = {payload_json};
                const filled = [];
                const inputs = Array.from(root.querySelectorAll('input:not([type=hidden]):not([type=submit]), select, textarea'));

                for (const [key, val] of Object.entries(values)) {{
                    const cleanKey = key.toLowerCase().trim();
                    const target = inputs.find(el => {{
                        const lbl = (el.getAttribute('aria-label') || el.placeholder || el.name || el.id || '').toLowerCase();
                        let parentLabel = el.closest('label')?.innerText?.toLowerCase() || '';
                        return lbl.includes(cleanKey) || parentLabel.includes(cleanKey);
                    }});

                    if (target) {{
                        target.focus();
                        target.value = val;
                        target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        target.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        filled.push({{ key, matched_element: target.name || target.id || target.tagName }});
                    }}
                }}
                return {{ success: true, filled_count: filled.length, filled }};
            }})()
            """
            res = await bridge.call("browser.evaluate_js", {"script": script})
            return {"status": "success", "result": res}

        elif tool_name == "submit_form":
            submit_sel = params.get("submit_button_selector") or 'button[type="submit"], input[type="submit"], form button'
            click_res = await bridge.call("browser.click_selector", {"selector": submit_sel})
            return {"status": "success", "submitted": True, "details": click_res}

        return {"status": "error", "message": f"Unknown tool '{tool_name}'"}
