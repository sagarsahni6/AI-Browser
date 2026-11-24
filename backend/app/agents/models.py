from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional, Literal, Set
from enum import Enum
from datetime import datetime

ALLOWED_AGENTS: Set[str] = {
    "supervisor", "planner", "browser", "dom", "vision", "desktop",
    "file", "memory", "recovery", "data", "data_agent",
    "researcher", "verifier", "browser_agent", "browser_use_agent"
}

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    APPROVAL_REQUIRED = "approval_required"

class TaskStep(BaseModel):
    id: int
    agent: str = Field(default="browser", description="Specialist agent: browser, dom, vision, desktop, file, memory, recovery, data, researcher, verifier, supervisor")
    action: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[int] = Field(default_factory=list, description="IDs of preceding steps this step depends on")
    verification_strategy: str = Field(
        default="none",
        description="Verification strategy: dom_assertion, url_match, data_validation, file_validation, form_submission, or none"
    )
    verification_params: Dict[str, Any] = Field(default_factory=dict)
    expected_outcome: Optional[str] = None
    timeout_seconds: int = 45
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def step_id(self) -> int:
        return self.id

    @field_validator("agent")
    @classmethod
    def validate_agent(cls, v: str) -> str:
        if v not in ALLOWED_AGENTS:
            raise ValueError(f"Invalid specialist agent '{v}'. Allowed agents: {sorted(ALLOWED_AGENTS)}")
        return v

# Alias PlanStep to TaskStep for unified runtime compatibility
PlanStep = TaskStep


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
