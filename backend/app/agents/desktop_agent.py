import logging
from typing import Dict, Any
from backend.app.automation.desktop.service import DesktopService
from backend.app.tools.executor import _normalize_response

logger = logging.getLogger("desktop_agent")

class DesktopAgent:
    """
    Specialist agent for native Windows desktop automation, offloading
    mouse, keyboard, app launching, and desktop screen inspection.
    """

    @classmethod
    async def execute_step(cls, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if action == "desktop_click":
            x = int(parameters.get("x", 0))
            y = int(parameters.get("y", 0))
            button = str(parameters.get("button", "left"))
            res = await DesktopService.mouse_click(x=x, y=y, button=button)
            return _normalize_response(res, action)

        elif action == "desktop_type":
            text = str(parameters.get("text", ""))
            res = await DesktopService.type_text(text)
            return _normalize_response(res, action)

        elif action == "desktop_hotkey":
            keys = parameters.get("keys", [])
            res = await DesktopService.send_hotkey(keys)
            return _normalize_response(res, action)

        elif action == "desktop_capture_screen":
            res = await DesktopService.capture_screen()
            return _normalize_response(res, action)

        elif action == "desktop_launch_app":
            app_name = str(parameters.get("app_name", ""))
            args = parameters.get("args")
            res = await DesktopService.launch_app(app_name=app_name, args=args)
            return _normalize_response(res, action)

        else:
            from backend.app.tools.executor import ToolExecutor
            return await ToolExecutor.execute(action, parameters)
