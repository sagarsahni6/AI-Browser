import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ExecutionBudget(BaseModel):
    max_steps: int = Field(default=30, description="Maximum total steps allowed")
    max_tool_calls: int = Field(default=50, description="Maximum tool executions allowed")
    max_duration_seconds: float = Field(default=600.0, description="Maximum execution duration in seconds")
    max_retries_per_step: int = Field(default=3, description="Maximum retries per failed step")
    max_tokens: int = Field(default=100_000, description="Maximum model tokens consumed")

    # Consumption counters
    steps_taken: int = 0
    tool_calls_made: int = 0
    tokens_used: int = 0
    start_time: float = Field(default_factory=time.time)

    def record_step(self, count: int = 1) -> None:
        self.steps_taken += count

    def record_tool_call(self, count: int = 1) -> None:
        self.tool_calls_made += count

    def record_tokens(self, count: int) -> None:
        self.tokens_used += count

    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    def is_exhausted(self) -> bool:
        if self.steps_taken >= self.max_steps:
            return True
        if self.tool_calls_made >= self.max_tool_calls:
            return True
        if self.elapsed_seconds() >= self.max_duration_seconds:
            return True
        if self.tokens_used >= self.max_tokens:
            return True
        return False

    def exhaustion_reason(self) -> Optional[str]:
        if self.steps_taken >= self.max_steps:
            return f"Execution budget exhausted: max steps reached ({self.steps_taken}/{self.max_steps})"
        if self.tool_calls_made >= self.max_tool_calls:
            return f"Execution budget exhausted: max tool calls reached ({self.tool_calls_made}/{self.max_tool_calls})"
        if self.elapsed_seconds() >= self.max_duration_seconds:
            return f"Execution budget exhausted: max duration reached ({self.elapsed_seconds():.1f}s/{self.max_duration_seconds}s)"
        if self.tokens_used >= self.max_tokens:
            return f"Execution budget exhausted: max tokens reached ({self.tokens_used}/{self.max_tokens})"
        return None

    def remaining_summary(self) -> Dict[str, Any]:
        return {
            "remaining_steps": max(0, self.max_steps - self.steps_taken),
            "remaining_tool_calls": max(0, self.max_tool_calls - self.tool_calls_made),
            "remaining_seconds": max(0.0, self.max_duration_seconds - self.elapsed_seconds()),
            "remaining_tokens": max(0, self.max_tokens - self.tokens_used),
            "steps_taken": self.steps_taken,
            "tool_calls_made": self.tool_calls_made,
            "elapsed_seconds": round(self.elapsed_seconds(), 2)
        }

    def can_retry_step(self, current_retries: int) -> bool:
        return current_retries < self.max_retries_per_step and not self.is_exhausted()
