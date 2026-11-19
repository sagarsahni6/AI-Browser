import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.database.engine import init_db, AsyncSessionLocal
from backend.app.database.repository import Repository

@pytest.mark.asyncio
async def test_database_and_conversations():
    await init_db()

    # 1. Test repository directly
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        conv = await repo.create_conversation(title="Test DB Conv", model="nvidia/llama-3.3-70b-instruct")
        assert conv.id.startswith("conv-")
        assert conv.title == "Test DB Conv"

        msg = await repo.add_message(conversation_id=conv.id, sender="user", content="Hello DB")
        assert msg.id.startswith("msg-")
        assert msg.content == "Hello DB"

        messages = await repo.get_messages(conv.id)
        assert len(messages) == 1
        assert messages[0].content == "Hello DB"

    # 2. Test via FastAPI endpoints
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get conversations list
        resp = await client.get("/api/v1/conversations")
        assert resp.status_code == 200
        data = resp.json()
        assert any(c["id"] == conv.id for c in data)

        # Create task via endpoint
        task_resp = await client.post("/api/v1/agent/tasks", json={
            "title": "Search AI trends",
            "prompt": "Find recent articles about autonomous agents"
        })
        assert task_resp.status_code == 200
        task_data = task_resp.json()
        assert task_data["title"] == "Search AI trends"
        assert task_data["status"] == "pending"

        # List tasks
        tasks_list = await client.get("/api/v1/agent/tasks")
        assert tasks_list.status_code == 200
        assert len(tasks_list.json()) >= 1

        # Providers list
        prov_resp = await client.get("/api/v1/providers")
        assert prov_resp.status_code == 200
        providers = prov_resp.json()
        assert any(p["id"] == "nvidia_nim" for p in providers)
