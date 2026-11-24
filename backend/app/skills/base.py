from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class SkillTool(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    risk_tier: str = "green"  # "green" | "yellow" | "red"

    def to_function_def(self) -> Dict[str, Any]:
        """Convert to OpenAI / NIM standard tool function definition schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {"type": "object", "properties": {}}
            }
        }


class SkillManifest(BaseModel):
    id: str
    name: str
    description: str
    category: str = "general"  # scraping, automation, diagnostics, research, finance, developer, general
    icon: str = "Zap"
    enabled: bool = True
    triggers: List[str] = Field(default_factory=list)
    tools: List[SkillTool] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "icon": self.icon,
            "enabled": self.enabled,
            "triggers": self.triggers,
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                    "riskTier": t.risk_tier
                }
                for t in self.tools
            ]
        }


class BaseSkill(ABC):
    """
    Abstract Base Class for an Agent Skill in AI Browser.
    Encapsulates manifest metadata, prompt injection, and tool execution.
    """
    manifest: SkillManifest

    @abstractmethod
    def get_system_prompt_snippet(self) -> str:
        """Returns instructional prompt text to guide the model when this skill is active."""
        pass

    @abstractmethod
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a specific tool provided by this skill."""
        pass
