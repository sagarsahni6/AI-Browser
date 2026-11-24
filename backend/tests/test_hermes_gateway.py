import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.config import settings
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_hermes_gateway_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Missing token header -> 422
        resp = await client.get("/api/v1/mcp/hermes/tools")
        assert resp.status_code == 422

        # 2. Invalid token header -> 403
        resp = await client.get(
            "/api/v1/mcp/hermes/tools",
            headers={"X-Hermes-Token": "invalid-token"}
        )
        assert resp.status_code == 403

        # 3. Valid token -> 200
        resp = await client.get(
            "/api/v1/mcp/hermes/tools",
            headers={"X-Hermes-Token": settings.HERMES_GATEWAY_TOKEN}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        tool_names = [t["name"] for t in data["tools"]]
        assert "get_page_content" in tool_names
        assert "search_web" in tool_names
        # Ensure sensitive tools are NOT in the list
        assert "evaluate_javascript" not in tool_names
        assert "desktop_click" not in tool_names


@pytest.mark.asyncio
async def test_hermes_gateway_tool_execution_whitelist():
    transport = ASGITransport(app=app)
    headers = {"X-Hermes-Token": settings.HERMES_GATEWAY_TOKEN}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Allowed whitelisted tool: get_page_content
        with patch("backend.app.tools.executor.ToolExecutor.execute", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"status": "success", "title": "Example", "url": "https://example.com"}

            resp = await client.post(
                "/api/v1/mcp/hermes/tool",
                headers=headers,
                json={"tool": "get_page_content", "parameters": {}}
            )
            assert resp.status_code == 200
            mock_exec.assert_called_once_with("get_page_content", {})

        # 2. Disallowed non-whitelisted tool: evaluate_javascript -> 403
        resp = await client.post(
            "/api/v1/mcp/hermes/tool",
            headers=headers,
            json={"tool": "evaluate_javascript", "parameters": {"script": "alert(1)"}}
        )
        assert resp.status_code == 403
        assert "whitelist" in resp.json()["detail"].lower()

        # 3. Disallowed non-whitelisted desktop tool: desktop_click -> 403
        resp = await client.post(
            "/api/v1/mcp/hermes/tool",
            headers=headers,
            json={"tool": "desktop_click", "parameters": {"x": 100, "y": 200}}
        )
        assert resp.status_code == 403
