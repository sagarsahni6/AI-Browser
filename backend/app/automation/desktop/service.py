import io
import os
import sys
import time
import base64
import logging
import subprocess
from typing import Dict, Any, List, Optional
from PIL import ImageGrab
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.repository import Repository

if sys.platform == "win32":
    import win32api
    import win32con
    import win32gui

logger = logging.getLogger("desktop_automation")

# Key mapping for common hotkeys
VK_MAP = {
    "ctrl": 0x11,
    "control": 0x11,
    "shift": 0x10,
    "alt": 0x12,
    "enter": 0x0D,
    "return": 0x0D,
    "esc": 0x1B,
    "escape": 0x1B,
    "tab": 0x09,
    "space": 0x20,
    "backspace": 0x08,
    "win": 0x5B,
    "windows": 0x5B,
}

class DesktopService:
    """
    Sandboxed Windows Desktop Automation Service:
    Executes native OS inputs, captures screen, launches applications,
    and enforces emergency stop and audit logging.
    """

    _emergency_stopped: bool = False

    @classmethod
    def emergency_stop(cls) -> Dict[str, Any]:
        """Trigger emergency stop halting all desktop automation immediately."""
        cls._emergency_stopped = True
        logger.critical("EMERGENCY KILL SWITCH ACTIVATED! All desktop automation halted.")
        return {"status": "ok", "emergency_stopped": True}

    @classmethod
    def reset_emergency_stop(cls) -> Dict[str, Any]:
        """Reset emergency stop state after user verification."""
        cls._emergency_stopped = False
        logger.info("Emergency kill switch reset. Desktop automation resumed.")
        return {"status": "ok", "emergency_stopped": False}

    @classmethod
    def is_stopped(cls) -> bool:
        return cls._emergency_stopped

    @classmethod
    async def _audit_log(cls, action: str, params: Dict[str, Any], authorized: bool, result: str):
        try:
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.create_desktop_audit_log(
                    action=action,
                    parameters=params,
                    authorized=authorized,
                    result=result
                )
        except Exception as e:
            logger.error(f"Failed to record audit log for {action}: {e}")

    @classmethod
    async def mouse_click(cls, x: int, y: int, button: str = "left") -> Dict[str, Any]:
        """Click at desktop coordinates (x, y)."""
        if cls._emergency_stopped:
            await cls._audit_log("mouse_click", {"x": x, "y": y, "button": button}, False, "Blocked by emergency stop")
            return {"status": "error", "error": "Emergency stop is active"}

        try:
            if sys.platform == "win32":
                win32api.SetCursorPos((x, y))
                time.sleep(0.05)
                if button.lower() == "right":
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
                else:
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

            await cls._audit_log("mouse_click", {"x": x, "y": y, "button": button}, True, "Success")
            return {"status": "success", "clicked": {"x": x, "y": y, "button": button}}
        except Exception as e:
            await cls._audit_log("mouse_click", {"x": x, "y": y, "button": button}, True, f"Failed: {e}")
            return {"status": "error", "error": str(e)}

    @classmethod
    async def type_text(cls, text: str) -> Dict[str, Any]:
        """Type string into the currently focused Windows application."""
        if cls._emergency_stopped:
            await cls._audit_log("type_text", {"text_len": len(text)}, False, "Blocked by emergency stop")
            return {"status": "error", "error": "Emergency stop is active"}

        try:
            if sys.platform == "win32":
                for char in text:
                    if cls._emergency_stopped:
                        break
                    # Send unicode character via keybd_event
                    vk = win32api.VkKeyScan(char)
                    if vk != -1:
                        shift_needed = (vk >> 8) & 1
                        if shift_needed:
                            win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)
                        win32api.keybd_event(vk & 0xFF, 0, 0, 0)
                        win32api.keybd_event(vk & 0xFF, 0, win32con.KEYEVENTF_KEYUP, 0)
                        if shift_needed:
                            win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)
                    time.sleep(0.01)

            await cls._audit_log("type_text", {"length": len(text)}, True, "Success")
            return {"status": "success", "typed_length": len(text)}
        except Exception as e:
            await cls._audit_log("type_text", {"length": len(text)}, True, f"Failed: {e}")
            return {"status": "error", "error": str(e)}

    @classmethod
    async def send_hotkey(cls, keys: List[str]) -> Dict[str, Any]:
        """Send key combination like ['ctrl', 'c'] or ['alt', 'tab']."""
        if cls._emergency_stopped:
            await cls._audit_log("send_hotkey", {"keys": keys}, False, "Blocked by emergency stop")
            return {"status": "error", "error": "Emergency stop is active"}

        try:
            vk_codes = []
            for k in keys:
                k_norm = k.lower().strip()
                if k_norm in VK_MAP:
                    vk_codes.append(VK_MAP[k_norm])
                elif len(k_norm) == 1:
                    vk_codes.append(ord(k_norm.upper()))

            if sys.platform == "win32":
                # Key down in sequence
                for vk in vk_codes:
                    win32api.keybd_event(vk, 0, 0, 0)
                time.sleep(0.05)
                # Key up in reverse
                for vk in reversed(vk_codes):
                    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)

            await cls._audit_log("send_hotkey", {"keys": keys}, True, "Success")
            return {"status": "success", "hotkey": "+".join(keys)}
        except Exception as e:
            await cls._audit_log("send_hotkey", {"keys": keys}, True, f"Failed: {e}")
            return {"status": "error", "error": str(e)}

    @classmethod
    async def capture_screen(cls) -> Dict[str, Any]:
        """Capture the primary desktop screen."""
        if cls._emergency_stopped:
            return {"status": "error", "error": "Emergency stop is active"}

        try:
            img = ImageGrab.grab()
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=80)
            b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
            
            await cls._audit_log("capture_screen", {}, True, "Captured screenshot")
            return {
                "status": "success",
                "width": img.width,
                "height": img.height,
                "data_url": f"data:image/jpeg;base64,{b64_str}"
            }
        except Exception as e:
            await cls._audit_log("capture_screen", {}, True, f"Failed: {e}")
            return {"status": "error", "error": str(e)}

    @classmethod
    async def launch_app(cls, app_name: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Launch a desktop application executable safely."""
        if cls._emergency_stopped:
            await cls._audit_log("launch_app", {"app_name": app_name}, False, "Blocked by emergency stop")
            return {"status": "error", "error": "Emergency stop is active"}

        try:
            cmd = [app_name] + (args or [])
            proc = subprocess.Popen(cmd, shell=False)
            res_str = f"Launched PID {proc.pid}"
            await cls._audit_log("launch_app", {"app_name": app_name, "pid": proc.pid}, True, res_str)
            return {"status": "success", "pid": proc.pid, "app": app_name}
        except Exception as e:
            await cls._audit_log("launch_app", {"app_name": app_name}, True, f"Failed: {e}")
            return {"status": "error", "error": str(e)}
