from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Any, Dict, List
import json
import asyncio

from backend.app.database.engine import get_db, AsyncSessionLocal
from backend.app.database.repository import Repository
from backend.app.dependencies import verify_local_token
from backend.app.browser.bridge import bridge
from backend.app.ai.router import ModelRouter

router = APIRouter(prefix="/assistant", tags=["assistant"])

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    tab_id: Optional[str] = None
    selected_text: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    stream: bool = False
    provider_id: Optional[str] = None
    model: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    model: str

def sanitize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return str(text).encode("utf-8", "ignore").decode("utf-8")

def build_system_prompt(page_context: Optional[Dict[str, Any]] = None, selected_text: Optional[str] = None) -> str:
    prompt = (
        "You are the intelligent AI Assistant integrated into AI Browser. "
        "You help users understand webpages, conduct cited research, extract data, and plan tasks.\n"
    )

    if page_context:
        title = sanitize_text(page_context.get("title", "Unknown"))
        url = sanitize_text(page_context.get("url", "Unknown"))
        prompt += (
            f"\n[CURRENT WEBPAGE CONTEXT]\n"
            f"Title: {title}\n"
            f"URL: {url}\n"
        )
        if page_context.get("visibleText"):
            snippet = sanitize_text(page_context["visibleText"])[:4000]
            prompt += f"Page Content Excerpt:\n{snippet}\n"

    if selected_text:
        prompt += f"\n[USER SELECTED TEXT]:\n\"{sanitize_text(selected_text)}\"\n"

    return prompt

@router.post("/chat")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)

    # 1. Fetch or create conversation
    conv_id = req.conversation_id
    if not conv_id:
        conv = await repo.create_conversation(title=req.message[:30] or "New Chat")
        conv_id = conv.id

    # 2. Extract or inspect current tab context if provided
    page_ctx = req.context or {}
    if req.tab_id and not page_ctx:
        try:
            obs = await bridge.call("browser.inspect", {})
            if obs:
                page_ctx = {
                    "url": obs.get("url"),
                    "title": obs.get("title"),
                    "visibleText": obs.get("visibleText")
                }
        except Exception:
            pass

    # 3. Store user message in DB
    await repo.add_message(
        conversation_id=conv_id,
        sender="user",
        content=req.message,
        tab_id=req.tab_id,
        url=page_ctx.get("url")
    )

    # 4. Route model and provider
    provider, model = ModelRouter.route_for_task(
        task_type="text",
        preferred_provider=req.provider_id,
        preferred_model=req.model
    )

    system_prompt = build_system_prompt(page_ctx, req.selected_text)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.message}
    ]

    # 5. Handle streaming or standard response
    if req.stream:
        async def event_generator():
            full_reply = ""
            try:
                async for chunk in provider.stream_completion(messages=messages, model=model):
                    full_reply += chunk
                    yield f"data: {json.dumps({'chunk': chunk, 'conversation_id': conv_id})}\n\n"
            finally:
                # Store assistant response in DB
                async with AsyncSessionLocal() as session:
                    r = Repository(session)
                    await r.add_message(
                        conversation_id=conv_id,
                        sender="assistant",
                        content=full_reply or "[No response generated]"
                    )
                yield f"data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        result = await provider.chat_completion(messages=messages, model=model)
        reply_content = result.content

        # Store in DB
        await repo.add_message(
            conversation_id=conv_id,
            sender="assistant",
            content=reply_content
        )

        return ChatResponse(
            reply=reply_content,
            conversation_id=conv_id,
            model=model
        )
