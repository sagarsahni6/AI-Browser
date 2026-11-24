"""
tests/e2e/conftest.py — Global Test Fixtures and Hermetic Test Harness for AI Browser 2.0.

Provides complete hermetic test isolation:
1. In-memory SQLite database via SQLAlchemy StaticPool monkeypatching AsyncSessionLocal and engine.
2. VirtualElectronBridge mocking CDP DOM state, tab management, screenshots, and capturing notifications.
3. MockNvidiaNimProvider eliminating external cloud calls and enabling deterministic completions.
4. Mock desktop primitives preventing OS side-effects while capturing database audit logs.
5. async_client (httpx ASGITransport) and ipc_client (stdio JSON-RPC bridge invoker).
"""

import sys
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, AsyncMock

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# Set test environment flags
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["TESTING"] = "1"

from backend.app.config import settings
from backend.app.database.models import Base
import backend.app.database.engine as db_engine
from backend.app.browser.bridge import bridge
from backend.app.ai.registry import provider_registry
from backend.app.ai.providers.base import BaseAIProvider, ChatCompletionResult
from backend.app.ai.capabilities import ModelCapabilities
import backend.app.automation.desktop.service as desktop_mod
from backend.app.main import app


# ---------------------------------------------------------------------------
# 1. Virtual Electron Bridge Engine
# ---------------------------------------------------------------------------
class VirtualElectronBridge:
    """In-memory mock for Electron stdio bridge and browser CDP state."""

    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self.notifications: List[Dict[str, Any]] = []
        self.active_tab_id: str = "tab-1"
        self.tabs: List[Dict[str, Any]] = [
            {"id": "tab-1", "url": "https://example.com", "title": "Example Domain", "active": True}
        ]
        self.dom_state: Dict[str, Any] = {
            "url": "https://example.com",
            "title": "Example Domain",
            "visibleText": "Example Domain for testing. Welcome to AI Browser 2.0 automated environment.",
            "interactiveElements": [
                {"id": "el-0", "selector": "#btn-submit", "tagName": "button", "text": "Submit", "x": 100, "y": 200},
                {"id": "el-1", "selector": "input#search", "tagName": "input", "label": "Search", "x": 150, "y": 50},
                {"id": "el-2", "selector": "a.checkout-link", "tagName": "a", "text": "Checkout", "x": 300, "y": 400},
            ]
        }
        self.custom_responses: Dict[str, Any] = {}

    def set_dom_state(self, url: str, title: str, text: str, elements: Optional[List[dict]] = None):
        self.dom_state = {
            "url": url,
            "title": title,
            "visibleText": text,
            "interactiveElements": elements or []
        }

    async def handle_call(self, method: str, params: Optional[dict] = None, timeout: float = 15.0) -> Any:
        params = params or {}
        self.calls.append({"method": method, "params": params})

        if method in self.custom_responses:
            resp = self.custom_responses[method]
            if callable(resp):
                return resp(params)
            return resp

        if method == "browser.inspect":
            tab_id = params.get("tabId") or params.get("tab_id")
            if tab_id and tab_id != self.active_tab_id:
                # Return state for target tab
                for t in self.tabs:
                    if t["id"] == tab_id:
                        return {
                            "url": t.get("url", "about:blank"),
                            "title": t.get("title", "Tab"),
                            "visibleText": f"Content of {t.get('url')}",
                            "interactiveElements": []
                        }
            return dict(self.dom_state)

        elif method == "browser.get_tabs":
            return list(self.tabs)

        elif method == "browser.create_tab":
            new_id = f"tab-{len(self.tabs) + 1}"
            url = params.get("url", "about:blank")
            for t in self.tabs:
                t["active"] = False
            self.tabs.append({"id": new_id, "url": url, "title": "New Tab", "active": True})
            self.active_tab_id = new_id
            return new_id

        elif method == "browser.switch_tab":
            target = params.get("tabId") or params.get("tab_id")
            found = False
            for t in self.tabs:
                if t["id"] == target:
                    t["active"] = True
                    found = True
                else:
                    t["active"] = False
            if found:
                self.active_tab_id = target
                return {"status": "ok", "active_tab": target}
            return {"status": "error", "error": f"Tab {target} not found"}

        elif method == "browser.close_tab":
            target = params.get("tabId") or params.get("tab_id")
            self.tabs = [t for t in self.tabs if t["id"] != target]
            if self.tabs and self.active_tab_id == target:
                self.tabs[0]["active"] = True
                self.active_tab_id = self.tabs[0]["id"]
            return {"status": "ok"}

        elif method == "browser.navigate":
            url = params.get("url", "")
            tab_id = params.get("tabId") or params.get("tab_id")
            if tab_id:
                for t in self.tabs:
                    if t["id"] == tab_id:
                        t["url"] = url
            else:
                self.dom_state["url"] = url
                for t in self.tabs:
                    if t["id"] == self.active_tab_id:
                        t["url"] = url
            return {"status": "ok", "url": url}

        elif method in ("browser.click", "browser.click_selector"):
            selector = params.get("selector") or f"({params.get('x')}, {params.get('y')})"
            return {"status": "ok", "clicked": selector}

        elif method in ("browser.fill", "browser.fill_selector"):
            return {"status": "ok", "filled": params.get("text", "")}

        elif method == "browser.capture_screenshot":
            # Valid transparent 1x1 base64 PNG data URI
            return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

        elif method == "browser.detect_forms":
            return [{"id": "form-1", "action": "/submit", "inputs": [{"name": "q", "type": "text"}]}]

        elif method == "browser.get_accessibility_tree":
            return {"role": "RootWebArea", "name": self.dom_state.get("title", ""), "children": []}

        elif method == "browser.evaluate_js":
            script = params.get("script", "")
            if "Boolean(document.querySelector" in script:
                return True
            return {"found": True, "visible": True, "text": "Submit", "value": None}

        return {"status": "ok"}

    def handle_notify(self, method: str, params: Optional[dict] = None):
        self.notifications.append({"method": method, "params": params or {}})


# ---------------------------------------------------------------------------
# 2. Mock AI Provider for NVIDIA NIM
# ---------------------------------------------------------------------------
class MockNvidiaNimProvider(BaseAIProvider):
    """Hermetic mock for NVIDIA NIM provider, isolating tests from external network calls."""

    def __init__(self):
        self.completion_queue: List[ChatCompletionResult] = []
        self.recorded_prompts: List[List[Dict[str, Any]]] = []
        self.simulate_rate_limit: bool = False
        self.simulate_timeout: bool = False
        self.connection_status: bool = True

    @property
    def provider_id(self) -> str:
        return "nvidia_nim"

    @property
    def name(self) -> str:
        return "NVIDIA NIM Mock"

    def get_capabilities(self, model: str) -> ModelCapabilities:
        return ModelCapabilities(supports_tools=True, supports_vision=True, supports_streaming=True)

    async def check_connection(self) -> bool:
        return self.connection_status and not self.simulate_timeout

    async def list_models(self) -> List[str]:
        return [
            "meta/llama-3.3-70b-instruct",
            "meta/llama-3.2-90b-vision-instruct",
            "nvidia/nemotron-3.5-lightning-30b-a3b",
            "mistralai/mistral-large-4-1t-a52b",
        ]

    def queue_completion(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None, model: str = "meta/llama-3.3-70b-instruct"):
        self.completion_queue.append(ChatCompletionResult(
            content=content,
            model=model,
            tool_calls=tool_calls
        ))

    async def chat_completion(self, messages: List[Dict[str, Any]], model: Optional[str] = None, **kwargs) -> ChatCompletionResult:
        self.recorded_prompts.append(messages)
        if self.simulate_timeout:
            raise asyncio.TimeoutError("Simulated NIM provider timeout")
        if self.simulate_rate_limit:
            raise RuntimeError("429 Too Many Requests: Rate limit exceeded")
        if self.completion_queue:
            return self.completion_queue.pop(0)

        # Check if last user message requested something specific
        last_msg = messages[-1].get("content", "") if messages else ""
        if isinstance(last_msg, list):
            last_msg = str(last_msg)

        return ChatCompletionResult(
            content=f"Mocked response for prompt: {last_msg[:60]}",
            model=model or "meta/llama-3.3-70b-instruct",
            tool_calls=None
        )

    async def stream_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        self.recorded_prompts.append(messages)
        words = ["Mocked", "stream", "chunk", "content."]
        for w in words:
            yield w + " "

    async def analyze_image(
        self,
        image_base64: str,
        prompt: str,
        model: Optional[str] = None
    ) -> str:
        return f"Mocked image analysis for prompt: {prompt}"


# ---------------------------------------------------------------------------
# 3. Hermetic Database & Module Monkeypatch Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
async def test_db(monkeypatch):
    """
    Provides a fresh, hermetic in-memory SQLite database via StaticPool for every test.
    Ensures zero interaction with the real ai_browser.db file.
    """
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
    test_sessionmaker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )

    # Monkeypatch central database module references
    monkeypatch.setattr(db_engine, "engine", test_engine)
    monkeypatch.setattr(db_engine, "AsyncSessionLocal", test_sessionmaker)

    # Monkeypatch all currently loaded modules that have bound AsyncSessionLocal
    for mod_name, mod in list(sys.modules.items()):
        if mod and hasattr(mod, "AsyncSessionLocal"):
            try:
                monkeypatch.setattr(mod, "AsyncSessionLocal", test_sessionmaker)
            except Exception:
                pass

    # Build schema
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_sessionmaker

    # Teardown schema
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture(autouse=True)
def mock_bridge(monkeypatch):
    """Mocks Electron stdio bridge and disables background stdin reading thread."""
    v_bridge = VirtualElectronBridge()
    monkeypatch.setattr(bridge, "call", v_bridge.handle_call)
    monkeypatch.setattr(bridge, "notify", v_bridge.handle_notify)
    monkeypatch.setattr(bridge, "start", AsyncMock())
    monkeypatch.setattr(bridge, "stop", MagicMock())
    monkeypatch.setattr(bridge, "notify_ready", MagicMock())
    return v_bridge


@pytest.fixture(autouse=True)
def mock_nim_provider(monkeypatch):
    """Mocks NVIDIA NIM provider and registers it in provider_registry."""
    mock_prov = MockNvidiaNimProvider()
    monkeypatch.setattr(provider_registry, "get", lambda pid=None: mock_prov)
    monkeypatch.setattr(provider_registry, "get_primary", lambda: mock_prov)
    return mock_prov


@pytest.fixture(autouse=True)
def mock_desktop_primitives(monkeypatch):
    """
    Mocks native OS desktop automation primitives (win32api, subprocess.Popen)
    to prevent physical mouse/keyboard side-effects on developer machines while
    preserving DesktopService audit logging and emergency kill switch functionality.
    """
    mock_popen = MagicMock()
    mock_popen.return_value.pid = 9999
    monkeypatch.setattr("subprocess.Popen", mock_popen)

    if sys.platform == "win32":
        try:
            import win32api
            import win32con
            import win32gui
            monkeypatch.setattr(win32api, "SetCursorPos", MagicMock())
            monkeypatch.setattr(win32api, "mouse_event", MagicMock())
            monkeypatch.setattr(win32api, "keybd_event", MagicMock())
            monkeypatch.setattr(win32api, "VkKeyScan", lambda char: 0x41)
        except ImportError:
            pass

    # Ensure emergency stop is clear before each test
    desktop_mod.DesktopService._emergency_stopped = False

    return mock_popen


# ---------------------------------------------------------------------------
# 4. HTTP and IPC Test Clients
# ---------------------------------------------------------------------------
@pytest.fixture
async def async_client():
    """Provides httpx.AsyncClient connected to the FastAPI application with valid auth headers."""
    headers = {"X-Local-Token": settings.SECRET_TOKEN}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as client:
        yield client


@pytest.fixture
def ipc_client():
    """Provides an invoker for incoming Electron stdio JSON-RPC calls."""
    async def _invoke(method: str, params: Optional[dict] = None) -> Any:
        handler = bridge._method_handlers.get(method)
        if not handler:
            raise ValueError(f"Method '{method}' is not registered on bridge._method_handlers")
        return await handler(params or {})
    return _invoke
