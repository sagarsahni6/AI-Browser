import time
import uuid
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from backend.app.database.models import (
    Conversation, Message, AgentTask, TaskStep, ApprovalRequest, ResearchCollection, ResearchSource, AppSetting
)

class Repository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # CONVERSATIONS
    async def create_conversation(self, title: str = "New Conversation", model: str = "nvidia/llama-3.3-70b-instruct") -> Conversation:
        conv = Conversation(
            id=f"conv-{uuid.uuid4().hex[:12]}",
            title=title,
            model=model,
            created_at=time.time(),
            updated_at=time.time()
        )
        self.db.add(conv)
        await self.db.commit()
        await self.db.refresh(conv)
        return conv

    async def get_conversations(self, limit: int = 50) -> List[Conversation]:
        stmt = select(Conversation).order_by(Conversation.updated_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        stmt = select(Conversation).where(Conversation.id == conv_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def delete_conversation(self, conv_id: str) -> bool:
        stmt = delete(Conversation).where(Conversation.id == conv_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    # MESSAGES
    async def add_message(
        self,
        conversation_id: str,
        sender: str,
        content: str,
        tab_id: Optional[str] = None,
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        msg = Message(
            id=f"msg-{uuid.uuid4().hex[:12]}",
            conversation_id=conversation_id,
            sender=sender,
            content=content,
            tab_id=tab_id,
            url=url,
            metadata_json=json.dumps(metadata) if metadata else None,
            created_at=time.time()
        )
        self.db.add(msg)

        # Update conversation timestamp
        await self.db.execute(
            update(Conversation).where(Conversation.id == conversation_id).values(updated_at=time.time())
        )

        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def get_messages(self, conversation_id: str) -> List[Message]:
        stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # AGENT TASKS
    async def create_task(self, title: str, prompt: str) -> AgentTask:
        task = AgentTask(
            id=f"task-{uuid.uuid4().hex[:12]}",
            title=title,
            prompt=prompt,
            status="pending",
            created_at=time.time()
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_tasks(self, limit: int = 50) -> List[AgentTask]:
        stmt = select(AgentTask).order_by(AgentTask.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_task(self, task_id: str) -> Optional[AgentTask]:
        stmt = select(AgentTask).where(AgentTask.id == task_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def update_task_status(self, task_id: str, status: str, result: Optional[str] = None, error: Optional[str] = None):
        values: Dict[str, Any] = {"status": status}
        if result is not None: values["result"] = result
        if error is not None: values["error"] = error
        if status in ("completed", "failed", "cancelled"):
            values["completed_at"] = time.time()

        await self.db.execute(update(AgentTask).where(AgentTask.id == task_id).values(**values))
        await self.db.commit()

    async def add_task_step(
        self,
        task_id: str,
        step_number: int,
        description: str,
        tool_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> TaskStep:
        step = TaskStep(
            id=f"step-{uuid.uuid4().hex[:12]}",
            task_id=task_id,
            step_number=step_number,
            description=description,
            tool_name=tool_name,
            parameters_json=json.dumps(parameters) if parameters else None,
            status="pending",
            created_at=time.time()
        )
        self.db.add(step)
        await self.db.commit()
        await self.db.refresh(step)
        return step

    async def update_step_status(self, step_id: str, status: str, result: Optional[Any] = None, error: Optional[str] = None):
        values: Dict[str, Any] = {"status": status}
        if result is not None:
            values["result_json"] = json.dumps(result) if not isinstance(result, str) else result
        if error is not None:
            values["error"] = error

        await self.db.execute(update(TaskStep).where(TaskStep.id == step_id).values(**values))
        await self.db.commit()

    async def get_task_steps(self, task_id: str) -> List[TaskStep]:
        stmt = select(TaskStep).where(TaskStep.task_id == task_id).order_by(TaskStep.step_number.asc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    # Research Collections
    async def create_collection(self, name: str, description: Optional[str] = None) -> ResearchCollection:
        col = ResearchCollection(
            id=f"col-{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            created_at=time.time()
        )
        self.db.add(col)
        await self.db.commit()
        await self.db.refresh(col)
        return col

    async def get_collections(self, limit: int = 50) -> List[ResearchCollection]:
        stmt = select(ResearchCollection).order_by(ResearchCollection.created_at.desc()).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_collection(self, col_id: str) -> Optional[ResearchCollection]:
        stmt = select(ResearchCollection).where(ResearchCollection.id == col_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def add_source_to_collection(self, col_id: str, url: str, title: str, excerpt: Optional[str] = None) -> ResearchSource:
        src = ResearchSource(
            id=f"src-{uuid.uuid4().hex[:12]}",
            collection_id=col_id,
            url=url,
            title=title,
            excerpt=excerpt,
            cited_at=time.time()
        )
        self.db.add(src)
        await self.db.commit()
        await self.db.refresh(src)
        return src

    async def delete_collection(self, col_id: str) -> bool:
        from sqlalchemy import delete
        await self.db.execute(delete(ResearchCollection).where(ResearchCollection.id == col_id))
        await self.db.commit()
        return True

    # Approvals
    async def create_approval_request(
        self,
        task_id: str,
        tool_name: str,
        action_type: str,
        description: str,
        parameters_json: Optional[str] = None
    ) -> ApprovalRequest:
        appr = ApprovalRequest(
            id=f"appr-{uuid.uuid4().hex[:12]}",
            task_id=task_id,
            tool_name=tool_name,
            action_type=action_type,
            description=description,
            parameters_json=parameters_json,
            status="pending",
            created_at=time.time()
        )
        self.db.add(appr)
        await self.db.commit()
        await self.db.refresh(appr)
        return appr

    async def update_approval_status(self, request_id: str, status: str) -> Optional[ApprovalRequest]:
        stmt = select(ApprovalRequest).where(ApprovalRequest.id == request_id)
        res = await self.db.execute(stmt)
        appr = res.scalars().first()
        if appr:
            appr.status = status
            await self.db.commit()
            await self.db.refresh(appr)
        return appr
