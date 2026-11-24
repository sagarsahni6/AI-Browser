from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class WorkflowStep(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    condition: Optional[str] = None
    max_retries: int = 2
    retry_delay: float = 0.5
    fallback_action: Optional[str] = None
    fallback_parameters: Optional[Dict[str, Any]] = None
    requires_approval: bool = False

class WorkflowDefinition(BaseModel):
    version: str = "1.0"
    id: Optional[str] = None
    name: str = "Imported Workflow"
    description: Optional[str] = ""
    trigger_type: str = "manual"
    variables: Dict[str, Any] = Field(default_factory=dict)
    steps: List[WorkflowStep] = Field(default_factory=list)

class WorkflowCheckpoint(BaseModel):
    execution_id: str
    workflow_id: str
    paused_step: int
    total_steps: int
    completed_results: List[Dict[str, Any]] = Field(default_factory=list)
    variables: Dict[str, Any] = Field(default_factory=dict)
    step_outputs: Dict[str, Any] = Field(default_factory=dict)
    pending_step: Dict[str, Any] = Field(default_factory=dict)
    remaining_steps: List[Dict[str, Any]] = Field(default_factory=list)
    approval_id: Optional[str] = None
    reason: Optional[str] = None
    paused_at: float = 0.0
