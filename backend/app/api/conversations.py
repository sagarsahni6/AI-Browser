from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
from backend.app.database.engine import get_db
from backend.app.database.repository import Repository
from backend.app.dependencies import verify_local_token

router = APIRouter(prefix="/conversations", tags=["conversations"], dependencies=[Depends(verify_local_token)])

class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"
    model: Optional[str] = "nvidia/llama-3.3-70b-instruct"

class ConversationResponse(BaseModel):
    id: str
    title: str
    model: str
    created_at: float
    updated_at: float

class MessageResponse(BaseModel):
    id: str
    sender: str
    content: str
    tab_id: Optional[str] = None
    url: Optional[str] = None
    created_at: float

class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse]

@router.get("", response_model=List[ConversationResponse])
async def list_conversations(limit: int = 50, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    convs = await repo.get_conversations(limit=limit)
    return [
        ConversationResponse(
            id=c.id,
            title=c.title,
            model=c.model,
            created_at=c.created_at,
            updated_at=c.updated_at
        )
        for c in convs
    ]

@router.post("", response_model=ConversationResponse)
async def create_conversation(req: CreateConversationRequest, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    conv = await repo.create_conversation(title=req.title or "New Conversation", model=req.model or "nvidia/llama-3.3-70b-instruct")
    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        model=conv.model,
        created_at=conv.created_at,
        updated_at=conv.updated_at
    )

@router.get("/{conv_id}", response_model=ConversationDetailResponse)
async def get_conversation(conv_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    conv = await repo.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs = await repo.get_messages(conv_id)
    return ConversationDetailResponse(
        id=conv.id,
        title=conv.title,
        model=conv.model,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[
            MessageResponse(
                id=m.id,
                sender=m.sender,
                content=m.content,
                tab_id=m.tab_id,
                url=m.url,
                created_at=m.created_at
            )
            for m in msgs
        ]
    )

@router.delete("/{conv_id}")
async def delete_conversation(conv_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    deleted = await repo.delete_conversation(conv_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted", "id": conv_id}
