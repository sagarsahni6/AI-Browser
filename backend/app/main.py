import asyncio
import os
import sys
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.browser.bridge import bridge
from backend.app.api.assistant import router as assistant_router
from backend.app.api.browser import router as browser_router

# Handle RPC methods invoked directly by Electron
async def handle_assistant_chat(params: dict):
    msg = params.get("message", "")
    context = params.get("context", {})
    return {
        "reply": f"Python AI Assistant received: '{msg}'. Context attached: {list(context.keys())}. Ready to assist."
    }

bridge.register_method("assistant.chat", handle_assistant_chat)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Start stdin/stdout bridge in background task
    bridge_task = asyncio.create_task(bridge.start())

    # 2. Notify Electron that backend is ready
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

# Strictly local CORS
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.PORT))
    host = os.environ.get("HOST", "127.0.0.1")
    # stdout is reserved for JSON-RPC; configure uvicorn log to stderr
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_config=None,
        access_log=False
    )
