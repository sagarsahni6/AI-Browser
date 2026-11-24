import io
import os
import sys
import time
import base64
import logging
import asyncio
import subprocess
from typing import Dict, Any, List, Optional
from PIL import ImageGrab
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.repository import Repository

if sys.platform == "win32":
    import win32api
    import win32con
    import win32gui
    import ctypes
    from ctypes import wintypes

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

BLOCKED_SHELLS = frozenset([
    "cmd.exe", "cmd", "powershell.exe", "powershell", "pwsh.exe", "pwsh",
    "wscript.exe", "cscript.exe", "bash.exe", "bash", "sh.exe", "sh",
    "reg.exe", "regedit.exe", "certutil.exe", "mshta.exe"
])

ALLOWED_SYSTEM_APPS = frozenset([
    "notepad.exe", "notepad", "calc.exe", "calc", "mspaint.exe", "mspaint",
    "explorer.exe", "code.exe"
])

class DesktopService:
    """
    Sandboxed Windows Desktop Automation Service:
    Executes native OS inputs via non-blocking asyncio.to_thread worker calls,
    types Unicode accurately via Windows SendInput, enforces application allowlists,
    and supports emergency stop and detailed audit logging.
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
    async def _audit_log(
        cls,
        action: str,
        params: Dict[str, Any],
        authorized: bool,
        result: str,
        target: Optional[str] = None,
        duration_ms: Optional[float] = None
    ):
        try:
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.create_desktop_audit_log(
                    action=action,
                    parameters=params,
                    authorized=authorized,
                    result=result,
                    action_type=action,
                    target=target,
                    status="authorized" if authorized else "denied",
                    duration_ms=duration_ms
                )
        except Exception as e:
            logger.error(f"Failed to record audit log for {action}: {e}")

    # Synchronous Worker Methods (run via asyncio.to_thread)
    @classmethod
    def _sync_mouse_click(cls, x: int, y: int, button: str = "left") -> None:
        if sys.platform == "win32":
            win32api.SetCursorPos((x, y))
            time.sleep(0.02)
            if button.lower() == "right":
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
            else:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

    @classmethod
    def _sync_type_unicode(cls, text: str) -> int:
        if sys.platform != "win32":
            return len(text)

        KEYEVENTF_UNICODE = 0x0004
        KEYEVENTF_KEYUP = 0x0002

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_ulonglong)
            ]

        class INPUT(ctypes.Structure):
            class _INPUT(ctypes.Union):
                _fields_ = [("ki", KEYBDINPUT)]
            _anonymous_ = ("_input",)
            _fields_ = [
                ("type", wintypes.DWORD),
                ("_input", _INPUT)
            ]

        INPUT_KEYBOARD = 1
        encoded = text.encode("utf-16-le")
        code_units = [int.from_bytes(encoded[i:i+2], "little") for i in range(0, len(encoded), 2)]

        count = 0
        for cu in code_units:
            if cls._emergency_stopped:
                break
            inp_down = INPUT(type=INPUT_KEYBOARD)
            inp_down.ki = KEYBDINPUT(wVk=0, wScan=cu, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0)
            inp_up = INPUT(type=INPUT_KEYBOARD)
            inp_up.ki = KEYBDINPUT(wVk=0, wScan=cu, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)

            inputs = (INPUT * 2)(inp_down, inp_up)
            ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))
            time.sleep(0.01)
            count += 1

        return count

    @classmethod
    def _sync_send_hotkey(cls, keys: List[str]) -> None:
        if sys.platform != "win32":
            return
        vk_codes = []
        for k in keys:
            k_norm = k.lower().strip()
            if k_norm in VK_MAP:
                vk_codes.append(VK_MAP[k_norm])
            elif len(k_norm) == 1:
                vk_codes.append(ord(k_norm.upper()))

        for vk in vk_codes:
            win32api.keybd_event(vk, 0, 0, 0)
        time.sleep(0.03)
        for vk in reversed(vk_codes):
            win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)

    @classmethod
    def _sync_capture_screen(cls) -> Dict[str, Any]:
        img = ImageGrab.grab()
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=80)
        b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return {
            "width": img.width,
            "height": img.height,
            "data_url": f"data:image/jpeg;base64,{b64_str}"
        }

    # Public Async API
    @classmethod
    async def mouse_click(cls, x: int, y: int, button: str = "left") -> Dict[str, Any]:
        """Click at desktop coordinates (x, y) asynchronously."""
        start_t = time.time()
        if cls._emergency_stopped:
            await cls._audit_log("mouse_click", {"x": x, "y": y, "button": button}, False, "Blocked by emergency stop", target=f"({x},{y})")
            return {"status": "error", "error": "Emergency stop is active"}

        try:
            await asyncio.to_thread(cls._sync_mouse_click, x, y, button)
            dur = (time.time() - start_t) * 1000.0
            await cls._audit_log("mouse_click", {"x": x, "y": y, "button": button}, True, "Success", target=f"({x},{y})", duration_ms=dur)
            return {"status": "success", "clicked": {"x": x, "y": y, "button": button}}
        except Exception as e:
            dur = (time.time() - start_t) * 1000.0
            await cls._audit_log("mouse_click", {"x": x, "y": y, "button": button}, True, f"Failed: {e}", target=f"({x},{y})", duration_ms=dur)
            return {"status": "error", "error": str(e)}

    @classmethod
    async def type_text(cls, text: str) -> Dict[str, Any]:
        """Type Unicode text into the active desktop application asynchronously."""
        start_t = time.time()
        if cls._emergency_stopped:
            await cls._audit_log("type_text", {"text_len": len(text)}, False, "Blocked by emergency stop")
            return {"status": "error", "error": "Emergency stop is active"}

        try:
            count = await asyncio.to_thread(cls._sync_type_unicode, text)
            dur = (time.time() - start_t) * 1000.0
            await cls._audit_log("type_text", {"length": len(text)}, True, "Success", duration_ms=dur)
            return {"status": "success", "typed_length": len(text), "code_units_sent": count}
        except Exception as e:
            dur = (time.time() - start_t) * 1000.0
            await cls._audit_log("type_text", {"length": len(text)}, True, f"Failed: {e}", duration_ms=dur)
            return {"status": "error", "error": str(e)}

    @classmethod
    async def send_hotkey(cls, keys: List[str]) -> Dict[str, Any]:
        """Send key combination asynchronously."""
        start_t = time.time()
        if cls._emergency_stopped:
            await cls._audit_log("send_hotkey", {"keys": keys}, False, "Blocked by emergency stop")
            return {"status": "error", "error": "Emergency stop is active"}

        try:
            await asyncio.to_thread(cls._sync_send_hotkey, keys)
            dur = (time.time() - start_t) * 1000.0
            await cls._audit_log("send_hotkey", {"keys": keys}, True, "Success", target="+".join(keys), duration_ms=dur)
            return {"status": "success", "hotkey": "+".join(keys)}
        except Exception as e:
            dur = (time.time() - start_t) * 1000.0
            await cls._audit_log("send_hotkey", {"keys": keys}, True, f"Failed: {e}", target="+".join(keys), duration_ms=dur)
            return {"status": "error", "error": str(e)}

    @classmethod
    async def capture_screen(cls) -> Dict[str, Any]:
        """Capture the primary desktop screen asynchronously."""
        start_t = time.time()
        if cls._emergency_stopped:
            return {"status": "error", "error": "Emergency stop is active"}

        try:
            screen_info = await asyncio.to_thread(cls._sync_capture_screen)
            dur = (time.time() - start_t) * 1000.0
            await cls._audit_log("capture_screen", {}, True, "Captured screenshot", duration_ms=dur)
            return {
                "status": "success",
                "width": screen_info["width"],
                "height": screen_info["height"],
                "data_url": screen_info["data_url"]
            }
        except Exception as e:
            dur = (time.time() - start_t) * 1000.0
            await cls._audit_log("capture_screen", {}, True, f"Failed: {e}", duration_ms=dur)
            return {"status": "error", "error": str(e)}

    @classmethod
    async def launch_app(cls, app_name: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Launch an allowed desktop application executable safely."""
        start_t = time.time()
        if cls._emergency_stopped:
            await cls._audit_log("launch_app", {"app_name": app_name}, False, "Blocked by emergency stop", target=app_name)
            return {"status": "error", "error": "Emergency stop is active"}

        base_name = os.path.basename(app_name).lower().strip()

        # Enforce Security Allowlist
        if base_name in BLOCKED_SHELLS:
            reason = f"Execution of command shell '{base_name}' is permanently blocked by security policy."
            await cls._audit_log("launch_app", {"app_name": app_name}, False, reason, target=app_name)
            return {"status": "error", "error": reason}

        # Check if known app or absolute path in allowed directories
        is_allowed = (base_name in ALLOWED_SYSTEM_APPS)
        if not is_allowed and os.path.isabs(app_name):
            norm_path = os.path.normpath(app_name).lower()
            allowed_prefixes = [
                os.environ.get("ProgramFiles", "C:\\Program Files").lower(),
                os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)").lower(),
                os.environ.get("SystemRoot", "C:\\Windows").lower(),
                os.environ.get("LocalAppData", "").lower(),
            ]
            if any(norm_path.startswith(p) for p in allowed_prefixes if p):
                is_allowed = True

        if not is_allowed:
            reason = f"Application '{base_name}' is not on the desktop execution allowlist."
            await cls._audit_log("launch_app", {"app_name": app_name}, False, reason, target=app_name)
            return {"status": "error", "error": reason}

        try:
            cmd = [app_name] + (args or [])
            proc = subprocess.Popen(cmd, shell=False)
            res_str = f"Launched PID {proc.pid}"
            dur = (time.time() - start_t) * 1000.0
            await cls._audit_log("launch_app", {"app_name": app_name, "pid": proc.pid}, True, res_str, target=app_name, duration_ms=dur)
            return {"status": "success", "pid": proc.pid, "app": app_name}
        except Exception as e:
            dur = (time.time() - start_t) * 1000.0
            await cls._audit_log("launch_app", {"app_name": app_name}, True, f"Failed: {e}", target=app_name, duration_ms=dur)
            return {"status": "error", "error": str(e)}
