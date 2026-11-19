from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
from backend.app.browser.bridge import bridge

router = APIRouter(prefix="/assistant", tags=["assistant"])

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    tab_id: Optional[str] = None
    context: Optional[dict[str, Any]] = None

class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    model: str

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # If the user asks about current page or inspects, we can call the browser bridge
    tab_info = "No active tab context"
    if req.tab_id:
        try:
            obs = await bridge.call("browser.inspect", {})
            tab_info = f"Inspected page: {obs.get('title')} ({obs.get('url')}) with {len(obs.get('interactiveElements', []))} elements."
        except Exception as e:
            tab_info = f"Tab inspection error: {e}"

    reply = (
        f"I received your request: '{req.message}'.\n\n"
        f"Browser state: {tab_info}\n\n"
        f"Connected to AI Browser Python Backend. Ready to orchestrate research and automation."
    )

    return ChatResponse(
        reply=reply,
        conversation_id=req.conversation_id or "conv-default",
        model="nvidia/meta/llama-3.3-70b-instruct"
    )
