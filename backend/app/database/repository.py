import time
import uuid
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from backend.app.database.models import (
    Conversation, Message, AgentTask, TaskStep, ApprovalRequest, ResearchCollection, ResearchSource, AppSetting,
    Workflow, WorkflowExecution, UserMemory, WebsiteMonitor, ResearchReport, DesktopAuditLog
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

    # WORKFLOWS
    async def create_workflow(
        self,
        name: str,
        description: Optional[str] = None,
        trigger_type: str = "manual",
        steps: Optional[List[Dict[str, Any]]] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Workflow:
        wf = Workflow(
            id=f"wf-{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            trigger_type=trigger_type,
            steps_json=json.dumps(steps or []),
            variables_json=json.dumps(variables or {}),
            created_at=time.time(),
            updated_at=time.time()
        )
        self.db.add(wf)
        await self.db.commit()
        await self.db.refresh(wf)
        return wf

    async def get_workflows(self, limit: int = 50) -> List[Workflow]:
        stmt = select(Workflow).order_by(Workflow.updated_at.desc()).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_workflow(self, wf_id: str) -> Optional[Workflow]:
        stmt = select(Workflow).where(Workflow.id == wf_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def update_workflow(
        self,
        wf_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Optional[Workflow]:
        stmt = select(Workflow).where(Workflow.id == wf_id)
        res = await self.db.execute(stmt)
        wf = res.scalars().first()
        if not wf:
            return None
        if name is not None: wf.name = name
        if description is not None: wf.description = description
        if steps is not None: wf.steps_json = json.dumps(steps)
        if variables is not None: wf.variables_json = json.dumps(variables)
        wf.updated_at = time.time()
        await self.db.commit()
        await self.db.refresh(wf)
        return wf

    async def delete_workflow(self, wf_id: str) -> bool:
        stmt = delete(Workflow).where(Workflow.id == wf_id)
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount > 0

    async def create_workflow_execution(self, wf_id: str) -> WorkflowExecution:
        exec_item = WorkflowExecution(
            id=f"wfexec-{uuid.uuid4().hex[:12]}",
            workflow_id=wf_id,
            status="running",
            current_step=0,
            started_at=time.time()
        )
        self.db.add(exec_item)
        await self.db.commit()
        await self.db.refresh(exec_item)
        return exec_item

    async def update_workflow_execution(
        self,
        exec_id: str,
        status: str,
        current_step: int = 0,
        result: Optional[str] = None,
        error: Optional[str] = None
    ) -> Optional[WorkflowExecution]:
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == exec_id)
        res = await self.db.execute(stmt)
        exec_item = res.scalars().first()
        if not exec_item:
            return None
        exec_item.status = status
        exec_item.current_step = current_step
        if result is not None: exec_item.result_json = result
        if error is not None: exec_item.error = error
        if status in ("completed", "failed", "cancelled"):
            exec_item.completed_at = time.time()
        await self.db.commit()
        await self.db.refresh(exec_item)
        return exec_item

    # RESEARCH REPORTS
    async def create_research_report(
        self,
        topic: str,
        content_markdown: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        summary: Optional[str] = None
    ) -> ResearchReport:
        report = ResearchReport(
            id=f"rep-{uuid.uuid4().hex[:12]}",
            topic=topic,
            content_markdown=content_markdown,
            sources_json=json.dumps(sources or []),
            summary=summary,
            created_at=time.time()
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def get_research_reports(self) -> List[ResearchReport]:
        stmt = select(ResearchReport).order_by(ResearchReport.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_research_report(self, report_id: str) -> Optional[ResearchReport]:
        stmt = select(ResearchReport).where(ResearchReport.id == report_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def delete_research_report(self, report_id: str) -> bool:
        stmt = delete(ResearchReport).where(ResearchReport.id == report_id)
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount > 0

    # USER MEMORY
    async def create_user_memory(
        self,
        key: str,
        value: str,
        category: str = "preference",
        tags: Optional[List[str]] = None
    ) -> UserMemory:
        mem = UserMemory(
            id=f"mem-{uuid.uuid4().hex[:12]}",
            key=key,
            value=value,
            category=category,
            tags_json=json.dumps(tags or []),
            created_at=time.time(),
            updated_at=time.time()
        )
        self.db.add(mem)
        await self.db.commit()
        await self.db.refresh(mem)
        return mem

    async def get_user_memories(self, category: Optional[str] = None) -> List[UserMemory]:
        stmt = select(UserMemory)
        if category:
            stmt = stmt.where(UserMemory.category == category)
        stmt = stmt.order_by(UserMemory.updated_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def delete_user_memory(self, mem_id: str) -> bool:
        stmt = delete(UserMemory).where(UserMemory.id == mem_id)
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount > 0

    # WEBSITE MONITORS
    async def create_website_monitor(
        self,
        url: str,
        name: str,
        selector: Optional[str] = None,
        check_interval: int = 3600
    ) -> WebsiteMonitor:
        mon = WebsiteMonitor(
            id=f"mon-{uuid.uuid4().hex[:12]}",
            url=url,
            name=name,
            selector=selector,
            check_interval=check_interval,
            created_at=time.time()
        )
        self.db.add(mon)
        await self.db.commit()
        await self.db.refresh(mon)
        return mon

    async def get_website_monitors(self) -> List[WebsiteMonitor]:
        stmt = select(WebsiteMonitor).order_by(WebsiteMonitor.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def delete_website_monitor(self, mon_id: str) -> bool:
        stmt = delete(WebsiteMonitor).where(WebsiteMonitor.id == mon_id)
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount > 0

    # DESKTOP AUDIT LOGS
    async def create_desktop_audit_log(
        self,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
        authorized: bool = True,
        result: Optional[str] = None
    ) -> DesktopAuditLog:
        log_entry = DesktopAuditLog(
            id=f"log-{uuid.uuid4().hex[:12]}",
            action=action,
            parameters_json=json.dumps(parameters or {}),
            authorized=authorized,
            result=result,
            timestamp=time.time()
        )
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        return log_entry

    async def get_desktop_audit_logs(self, limit: int = 100) -> List[DesktopAuditLog]:
        stmt = select(DesktopAuditLog).order_by(DesktopAuditLog.timestamp.desc()).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
