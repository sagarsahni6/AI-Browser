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
    tool_name = Column(String(64), nullable=False)
    action_type = Column(String(64), nullable=False) # financial, credential, data_export, navigation
    description = Column(Text, nullable=False)
    parameters_json = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="pending", index=True) # pending, approved, rejected
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
