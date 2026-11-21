import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from backend.app.memory.service import MemoryService
from backend.app.scheduler.monitor import WebsiteMonitorService
from backend.app.api.assistant import build_system_prompt
from backend.app.database.engine import init_db

@pytest.mark.asyncio
async def test_memory_lifecycle():
    await init_db()
    
    # 1. Remember preference
    mem = await MemoryService.remember(
        key="theme_preference",
        value="dark_mode",
        category="preference",
        tags=["ui", "appearance"]
    )
    assert mem["action"] == "created"
    assert mem["key"] == "theme_preference"
    mem_id = mem["id"]

    # 2. Update memory
    mem_update = await MemoryService.remember(
        key="theme_preference",
        value="high_contrast_dark",
        category="preference"
    )
    assert mem_update["action"] == "updated"
    assert mem_update["value"] == "high_contrast_dark"

    # 3. Recall memory
    recalled = await MemoryService.recall("contrast")
    assert len(recalled) >= 1
    assert recalled[0]["key"] == "theme_preference"

    # 4. Context injection string
    ctx = await MemoryService.get_memory_context()
    assert "[USER PREFERENCES & LONG-TERM CONTEXT]" in ctx
    assert "theme_preference: high_contrast_dark" in ctx

    # 5. System prompt integration
    prompt = build_system_prompt(page_context=None, memory_context=ctx)
    assert "theme_preference: high_contrast_dark" in prompt

    # 6. Forget memory
    deleted = await MemoryService.forget(mem_id)
    assert deleted is True
    assert len(await MemoryService.recall("contrast")) == 0


@pytest.mark.asyncio
async def test_website_monitor_lifecycle_and_diff():
    await init_db()

    with patch("backend.app.scheduler.monitor.WebsiteMonitorService.fetch_target_content", new_callable=AsyncMock) as mock_fetch:
        # Initial baseline fetch
        mock_fetch.return_value = {
            "status": "ok",
            "text": "Current Price: $99.99 in stock"
        }

        created = await WebsiteMonitorService.create_monitor(
            url="https://store.example.com/item",
            name="Item Price Tracker"
        )
        mon_id = created["id"]
        assert mon_id is not None
        assert created["name"] == "Item Price Tracker"

        # Check with same content -> no change
        check1 = await WebsiteMonitorService.check_monitor(mon_id)
        assert check1["status"] == "ok"
        assert check1["changed"] is False

        # Simulate price drop / change
        mock_fetch.return_value = {
            "status": "ok",
            "text": "Current Price: $79.99 sale"
        }

        with patch("backend.app.browser.bridge.bridge.notify") as mock_notify:
            check2 = await WebsiteMonitorService.check_monitor(mon_id)
            assert check2["status"] == "ok"
            assert check2["changed"] is True
            mock_notify.assert_called_once()
            call_args = mock_notify.call_args[0]
            assert call_args[0] == "monitor.change_detected"
            assert call_args[1]["monitor_id"] == mon_id

        # List monitors
        monitors = await WebsiteMonitorService.list_monitors()
        assert any(m["id"] == mon_id for m in monitors)

        # Delete monitor
        del_res = await WebsiteMonitorService.delete_monitor(mon_id)
        assert del_res is True
