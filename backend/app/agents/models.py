from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from enum import Enum
from datetime import datetime

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    APPROVAL_REQUIRED = "approval_required"

class TaskStep(BaseModel):
    id: int
    agent: Literal["browser", "researcher", "data", "verifier", "supervisor"] = "browser"
    action: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    expected_outcome: Optional[str] = None
    timeout_seconds: int = 45
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class TaskPlan(BaseModel):
    task_id: str
    description: str
    steps: List[TaskStep]
    estimated_time_seconds: int = 60
    requires_approval: bool = False

class TaskEvent(BaseModel):
    task_id: str
    event_type: Literal[
        "task_started", "plan_created", "step_started",
        "step_completed", "step_failed", "approval_required",
        "task_completed", "task_failed"
    ]
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
