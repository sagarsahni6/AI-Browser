import time
from sqlalchemy import Column, String, Integer, Float, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True)
    title = Column(String(255), nullable=False, default="New Conversation")
    model = Column(String(128), nullable=False, default="nvidia/llama-3.3-70b-instruct")
    created_at = Column(Float, default=time.time, index=True)
    updated_at = Column(Float, default=time.time)

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

class Message(Base):
    __tablename__ = "messages"

    id = Column(String(64), primary_key=True)
    conversation_id = Column(String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender = Column(String(32), nullable=False) # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    tab_id = Column(String(64), nullable=True)
    url = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(Float, default=time.time, index=True)

    conversation = relationship("Conversation", back_populates="messages")

class AgentTask(Base):
    __tablename__ = "tasks"

    id = Column(String(64), primary_key=True)
    title = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pending", index=True) # pending, planned, running, paused, completed, failed, cancelled
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(Float, default=time.time, index=True)
    completed_at = Column(Float, nullable=True)
    # LangGraph integration columns (nullable — existing rows unaffected)
    graph_thread_id = Column(String(128), nullable=True, index=True)
    lg_checkpoint_id = Column(String(128), nullable=True)

    steps = relationship("TaskStep", back_populates="task", cascade="all, delete-orphan", order_by="TaskStep.step_number")
    approvals = relationship("ApprovalRequest", back_populates="task", cascade="all, delete-orphan")

class TaskStep(Base):
    __tablename__ = "task_steps"

    id = Column(String(64), primary_key=True)
    task_id = Column(String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    description = Column(String(255), nullable=False)
    tool_name = Column(String(64), nullable=True)
    parameters_json = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="pending") # pending, running, completed, failed
    error = Column(Text, nullable=True)
    created_at = Column(Float, default=time.time)

    task = relationship("AgentTask", back_populates="steps")

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String(64), primary_key=True)
    task_id = Column(String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=True)
    tool_name = Column(String(64), nullable=False)
    action_type = Column(String(64), nullable=False) # financial, credential, data_export, navigation, sensitive_operation
    description = Column(Text, nullable=False)
    parameters_json = Column(Text, nullable=True)
    session_checkpoint_json = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="pending", index=True) # pending, approved, rejected, executed, failed
    resolved_at = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(Float, default=time.time)

    task = relationship("AgentTask", back_populates="approvals")

class ResearchCollection(Base):
    __tablename__ = "research_collections"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(Float, default=time.time, index=True)

    sources = relationship("ResearchSource", back_populates="collection", cascade="all, delete-orphan")

class ResearchSource(Base):
    __tablename__ = "research_sources"

    id = Column(String(64), primary_key=True)
    collection_id = Column(String(64), ForeignKey("research_collections.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    title = Column(String(255), nullable=False)
    excerpt = Column(Text, nullable=True)
    cited_at = Column(Float, default=time.time)

    collection = relationship("ResearchCollection", back_populates="sources")

class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String(64), primary_key=True)
    value_json = Column(Text, nullable=False)
    updated_at = Column(Float, default=time.time)

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(String(64), nullable=False, default="manual") # manual, schedule, url_match
    steps_json = Column(Text, nullable=False, default="[]")
    variables_json = Column(Text, nullable=True, default="{}")
    created_at = Column(Float, default=time.time, index=True)
    updated_at = Column(Float, default=time.time)

    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(String(64), primary_key=True)
    workflow_id = Column(String(64), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="pending") # pending, running, completed, failed, cancelled
    current_step = Column(Integer, default=0)
    result_json = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(Float, default=time.time)
    completed_at = Column(Float, nullable=True)

    workflow = relationship("Workflow", back_populates="executions")

class UserMemory(Base):
    __tablename__ = "user_memories"

    id = Column(String(64), primary_key=True)
    category = Column(String(64), nullable=False, default="preference") # preference, research, workflow, context
    key = Column(String(128), nullable=False, index=True)
    value = Column(Text, nullable=False)
    tags_json = Column(Text, nullable=True, default="[]")
    created_at = Column(Float, default=time.time, index=True)
    updated_at = Column(Float, default=time.time)

class WebsiteMonitor(Base):
    __tablename__ = "website_monitors"

    id = Column(String(64), primary_key=True)
    url = Column(Text, nullable=False)
    name = Column(String(255), nullable=False)
    selector = Column(String(255), nullable=True)
    last_content_hash = Column(String(64), nullable=True)
    last_text_snippet = Column(Text, nullable=True)
    check_interval = Column(Integer, default=3600) # seconds
    last_check_at = Column(Float, nullable=True)
    status = Column(String(32), default="active") # active, paused, alert
    alert_on_change = Column(Boolean, default=True)
    created_at = Column(Float, default=time.time)

class ResearchReport(Base):
    __tablename__ = "research_reports"

    id = Column(String(64), primary_key=True)
    topic = Column(String(255), nullable=False)
    content_markdown = Column(Text, nullable=False)
    sources_json = Column(Text, nullable=True, default="[]")
    summary = Column(Text, nullable=True)
    created_at = Column(Float, default=time.time, index=True)

class DesktopAuditLog(Base):
    __tablename__ = "desktop_audit_logs"

    id = Column(String(64), primary_key=True)
    action = Column(String(64), nullable=False) # mouse_click, key_press, screen_capture, app_launch
    action_type = Column(String(64), nullable=True) # normalized action type
    target = Column(String(255), nullable=True)
    status = Column(String(32), nullable=True) # authorized, denied, completed, failed
    duration_ms = Column(Float, nullable=True)
    parameters_json = Column(Text, nullable=True)
    authorized = Column(Boolean, default=True)
    result = Column(Text, nullable=True)
    timestamp = Column(Float, default=time.time, index=True)

class RuntimeCheckpoint(Base):
    __tablename__ = "runtime_checkpoints"

    id = Column(String(64), primary_key=True)
    task_id = Column(String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False, default=0)
    state_json = Column(Text, nullable=False)
    created_at = Column(Float, default=time.time)
    updated_at = Column(Float, default=time.time, index=True)

    task = relationship("AgentTask", backref="runtime_checkpoints")

