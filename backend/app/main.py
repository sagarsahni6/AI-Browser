import asyncio
import os
import sys
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.database.engine import init_db, AsyncSessionLocal
from backend.app.database.repository import Repository
from backend.app.browser.bridge import bridge
from backend.app.api.assistant import router as assistant_router
from backend.app.api.browser import router as browser_router
from backend.app.api.conversations import router as conversations_router
from backend.app.api.tasks import router as tasks_router
from backend.app.api.providers import router as providers_router
from backend.app.api.search import router as search_router

# Handle RPC methods invoked directly by Electron
async def handle_assistant_chat(params: dict):
    msg_content = params.get("message", "")
    context = params.get("context", {})
    conv_id = params.get("conversation_id")

    reply_content = f"Python AI Assistant received: '{msg_content}'. Context attached: {list(context.keys())}. Ready to assist."

    # Persist message and reply to database
    try:
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            if not conv_id:
                conv = await repo.create_conversation(title=msg_content[:30] or "New Conversation")
                conv_id = conv.id

            await repo.add_message(
                conversation_id=conv_id,
                sender="user",
                content=msg_content,
                tab_id=context.get("tabId"),
                url=context.get("url")
            )
            await repo.add_message(
                conversation_id=conv_id,
                sender="assistant",
                content=reply_content
            )
    except Exception as e:
        sys.stderr.write(f"[DB Error in RPC] {e}\n")

    return {
        "reply": reply_content,
        "conversation_id": conv_id
    }

bridge.register_method("assistant.chat", handle_assistant_chat)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize SQLite database schema
    await init_db()

    # 2. Start stdin/stdout bridge in background task
    bridge_task = asyncio.create_task(bridge.start())

    # 3. Notify Electron that backend is ready
    bridge.notify_ready(port=settings.PORT, token=settings.SECRET_TOKEN)

    yield

    # Cleanup
    bridge.stop()
    bridge_task.cancel()

app = FastAPI(
    title="AI Browser Backend",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
async def health_check():
    return {
        "version": "0.1.0",
        "status": "healthy",
        "database": "sqlite_ready",
        "ai_provider": "nvidia_nim_ready",
        "port": settings.PORT
    }

app.include_router(assistant_router, prefix="/api/v1")
app.include_router(browser_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(providers_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.PORT))
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_config=None,
        access_log=False
    )
