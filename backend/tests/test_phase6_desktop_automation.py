import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from backend.app.automation.desktop.service import DesktopService
from backend.app.security.approval import ApprovalManager
from backend.app.tools.executor import ToolExecutor
from backend.app.database.engine import init_db, AsyncSessionLocal
from backend.app.database.repository import Repository

@pytest.mark.asyncio
async def test_desktop_emergency_stop_lifecycle():
    await init_db()
    
    # 1. Activate Emergency Stop
    DesktopService.emergency_stop()
    assert DesktopService.is_stopped() is True

    # 2. Verify all operations are blocked and logged
    res_click = await DesktopService.mouse_click(100, 200)
    assert res_click["status"] == "error"
    assert "Emergency stop is active" in res_click["error"]

    res_type = await DesktopService.type_text("hello")
    assert res_type["status"] == "error"
    assert "Emergency stop is active" in res_type["error"]

    res_app = await DesktopService.launch_app("notepad.exe")
    assert res_app["status"] == "error"
    assert "Emergency stop is active" in res_app["error"]

    # 3. Check audit log has blocked entries with authorized=False
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        logs = await repo.get_desktop_audit_logs(limit=10)
        assert any(l.authorized is False for l in logs)

    # 4. Reset Emergency Stop
    DesktopService.reset_emergency_stop()
    assert DesktopService.is_stopped() is False


@pytest.mark.asyncio
async def test_desktop_action_execution_and_audit():
    await init_db()
    DesktopService.reset_emergency_stop()

    with patch("backend.app.automation.desktop.service.subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_popen.return_value = mock_proc

        res = await DesktopService.launch_app("calc.exe")
        assert res["status"] == "success"
        assert res["pid"] == 9999

    # Verify audit log recorded successful launch
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        logs = await repo.get_desktop_audit_logs(limit=5)
        assert any(l.action == "launch_app" and l.authorized is True for l in logs)


def test_desktop_security_approval_gates():
    # 1. Launch app requires user approval
    req_app, reason_app = ApprovalManager.evaluate_tool_call("desktop_launch_app", {"app_name": "powershell.exe"})
    assert req_app is True
    assert "approval" in reason_app.lower() or "authorization" in reason_app.lower()

    # 2. Alt+F4 termination requires user approval
    req_kill, reason_kill = ApprovalManager.evaluate_tool_call("desktop_hotkey", {"keys": ["alt", "f4"]})
    assert req_kill is True

    # 3. Standard mouse click is auto-authorized
    req_click, _ = ApprovalManager.evaluate_tool_call("desktop_click", {"x": 500, "y": 400})
    assert req_click is False


@pytest.mark.asyncio
async def test_desktop_tool_executor_dispatch():
    # Verify desktop_launch_app hits approval check in ToolExecutor
    res = await ToolExecutor.execute("desktop_launch_app", {"app_name": "cmd.exe"})
    assert res["status"] == "approval_required"
    assert res["tool_name"] == "desktop_launch_app"
