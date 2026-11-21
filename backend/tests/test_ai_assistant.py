import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.ai.registry import provider_registry
from backend.app.ai.router import ModelRouter

@pytest.mark.asyncio
async def test_ai_provider_routing():
    # 1. Test model router
    provider, model = ModelRouter.route_for_task(task_type="text")
    assert provider.provider_id == "nvidia_nim"
    assert "llama" in model.lower() or "nemotron" in model.lower() or "minimax" in model.lower()

    # Vision routing
    v_provider, v_model = ModelRouter.route_for_task(task_type="vision")
    assert "vision" in v_model.lower() or "vl" in v_model.lower() or "4o" in v_model.lower()

    # 2. Test completion with mocked/offline fallback
    res = await provider.chat_completion(
        messages=[{"role": "user", "content": "What is AI Browser?"}]
    )
    assert res.content is not None
    assert len(res.content) > 0

@pytest.mark.asyncio
async def test_assistant_chat_with_webpage_context():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/assistant/chat", json={
            "message": "Summarize this page",
            "context": {
                "title": "Example Domain",
                "url": "https://example.com",
                "visibleText": "This domain is established to be used for illustrative examples in documents."
            }
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert "conversation_id" in data
        assert len(data["reply"]) > 0

@pytest.mark.asyncio
async def test_assistant_chat_shopping_recommendation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/assistant/chat", json={
            "message": "TOP MOTORCYCLE UNDER 200000",
            "context": {
                "title": "Page Not Found",
                "url": "https://www.bikedekho.com/bikes-under-2-lakh",
                "visibleText": "Oops! We can't seem to find the page."
            }
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert len(data["reply"]) > 20
        # Must not return "Action completed."
        assert "Action completed." not in data["reply"]

def test_comet_system_prompt_cached():
    from backend.app.api.assistant import get_comet_system_prompt, COMET_SYSTEM_PROMPT
    prompt = get_comet_system_prompt()
    assert prompt is not None
    assert len(prompt) > 0
    assert "COMET AUTONOMOUS BROWSER AGENT ENGINE" in prompt
    assert prompt == COMET_SYSTEM_PROMPT
