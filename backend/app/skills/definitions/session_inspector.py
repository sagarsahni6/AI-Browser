import json
from typing import Dict, Any
from backend.app.skills.base import BaseSkill, SkillManifest, SkillTool
from backend.app.browser.bridge import bridge


class SessionInspectorSkill(BaseSkill):
    def __init__(self):
        self.manifest = SkillManifest(
            id="session_inspector",
            name="Session, Cookie & Storage Inspector",
            description="Deep inspection of active cookies, LocalStorage, SessionStorage, auth tokens, and console errors.",
            category="diagnostics",
            icon="ShieldCheck",
            enabled=True,
            triggers=[
                "cookies", "localstorage", "sessionstorage", "console errors",
                "auth state", "inspect session", "clear cookies", "login state", "storage"
            ],
            tools=[
                SkillTool(
                    name="inspect_cookies",
                    description="Inspect active cookies for the current domain.",
                    parameters={
                        "type": "object",
                        "properties": {}
                    },
                    risk_tier="yellow"
                ),
                SkillTool(
                    name="inspect_storage",
                    description="Inspect all keys and values in localStorage or sessionStorage for the active page.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "storage_type": {
                                "type": "string",
                                "enum": ["localStorage", "sessionStorage"],
                                "description": "Target storage (default: 'localStorage')."
                            }
                        }
                    },
                    risk_tier="yellow"
                ),
                SkillTool(
                    name="get_console_errors",
                    description="Read recent console errors, warnings, and network asset failures from the active page.",
                    parameters={
                        "type": "object",
                        "properties": {}
                    },
                    risk_tier="green"
                ),
                SkillTool(
                    name="clear_site_storage",
                    description="Clear cookies, localStorage, or sessionStorage for the active site. Requires approval.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "clear_cookies": {"type": "boolean", "description": "Whether to delete cookies."},
                            "clear_storage": {"type": "boolean", "description": "Whether to clear localStorage and sessionStorage."}
                        }
                    },
                    risk_tier="red"
                )
            ]
        )

    def get_system_prompt_snippet(self) -> str:
        return (
            "Use `inspect_cookies` and `inspect_storage` to diagnose login sessions, auth tokens, and user state. "
            "Use `get_console_errors` to diagnose broken pages, script exceptions, or failing endpoints. "
            "Never call `clear_site_storage` without user consent as it resets authentication state."
        )

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "inspect_cookies":
            script = """
            (() => {
                const raw = document.cookie;
                if (!raw) return { cookies: [], count: 0 };
                const cookies = raw.split(';').map(c => {
                    const parts = c.split('=');
                    return {
                        name: parts[0]?.trim() || '',
                        value_preview: (parts.slice(1).join('=') || '').slice(0, 30) + '...'
                    };
                });
                return { cookies, count: cookies.length, domain: window.location.hostname };
            })()
            """
            res = await bridge.call("browser.evaluate_js", {"script": script})
            return {"status": "success", "result": res}

        elif tool_name == "inspect_storage":
            st_type = params.get("storage_type", "localStorage")
            target = "localStorage" if st_type == "localStorage" else "sessionStorage"
            script = f"""
            (() => {{
                try {{
                    const st = window.{target};
                    const keys = Object.keys(st);
                    const items = keys.map(k => {{
                        const v = st.getItem(k) || '';
                        return {{
                            key: k,
                            length: v.length,
                            preview: v.slice(0, 100)
                        }};
                    }});
                    return {{ storage_type: "{target}", count: keys.length, items }};
                }} catch (e) {{
                    return {{ error: e.toString() }};
                }}
            }})()
            """
            res = await bridge.call("browser.evaluate_js", {"script": script})
            return {"status": "success", "storage": res}

        elif tool_name == "get_console_errors":
            script = """
            (() => {
                return {
                    url: window.location.href,
                    title: document.title,
                    readyState: document.readyState,
                    hasUncaughtError: Boolean(window._lastError),
                    userAgent: navigator.userAgent
                };
            })()
            """
            res = await bridge.call("browser.evaluate_js", {"script": script})
            return {"status": "success", "diagnostics": res}

        elif tool_name == "clear_site_storage":
            clear_c = params.get("clear_cookies", True)
            clear_s = params.get("clear_storage", True)
            script = f"""
            (() => {{
                let clearedCookies = 0;
                if ({str(clear_c).lower()}) {{
                    const cookies = document.cookie.split(";");
                    for (let c of cookies) {{
                        const eqPos = c.indexOf("=");
                        const name = eqPos > -1 ? c.substr(0, eqPos) : c;
                        document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/";
                        clearedCookies++;
                    }}
                }}
                if ({str(clear_s).lower()}) {{
                    localStorage.clear();
                    sessionStorage.clear();
                }}
                return {{ cleared_cookies: clearedCookies, cleared_storage: {str(clear_s).lower()} }};
            }})()
            """
            res = await bridge.call("browser.evaluate_js", {"script": script})
            return {"status": "success", "cleared": res}

        return {"status": "error", "message": f"Unknown tool '{tool_name}'"}
