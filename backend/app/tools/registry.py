import asyncio
from enum import Enum
from typing import Dict, Any, Optional, Callable, Type, Union, List
from pydantic import BaseModel, Field

class RiskTier(str, Enum):
    GREEN = "green"                         # Safe read-only inspection
    YELLOW = "yellow"                       # Low-risk navigation/clicks
    REQUIRES_APPROVAL = "requires_approval" # Financial, sensitive forms, desktop input, app launch
    BLOCKED = "blocked"                     # Shell commands, loopback SSRF, file:// protocol

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters_schema: Union[Type[BaseModel], Dict[str, Any]] = Field(default_factory=dict)
    return_schema: Optional[Union[Type[BaseModel], Dict[str, Any]]] = None
    risk_tier: RiskTier = RiskTier.GREEN
    has_side_effects: bool = False
    timeout_seconds: float = 30.0
    category: str = "browser"  # browser, dom, vision, desktop, file, data, research, system
    applicable_agent: Optional[str] = None

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable] = {}

    def register(self, tool_def: ToolDefinition, handler: Optional[Callable] = None) -> None:
        self._tools[tool_def.name] = tool_def
        if handler:
            self._handlers[tool_def.name] = handler

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[ToolDefinition]:
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())

    def get_openai_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        tools = self.list_tools(category)
        openai_tools = []
        for t in tools:
            schema = t.parameters_schema
            if isinstance(schema, type) and issubclass(schema, BaseModel):
                param_dict = schema.model_json_schema()
            elif isinstance(schema, dict):
                param_dict = schema
            else:
                param_dict = {"type": "object", "properties": {}}
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": param_dict
                }
            })
        return openai_tools

    async def execute(self, name: str, params: Dict[str, Any], context: Optional[Any] = None) -> Dict[str, Any]:
        tool = self.get(name)
        if not tool:
            from backend.app.tools.executor import ToolExecutor
            return await ToolExecutor.execute(name, params)

        handler = self._handlers.get(name)
        if handler:
            try:
                res = handler(params)
                if asyncio.iscoroutine(res):
                    res = await asyncio.wait_for(res, timeout=tool.timeout_seconds)
                from backend.app.tools.executor import _normalize_response
                return _normalize_response(res, name)
            except asyncio.TimeoutError:
                from backend.app.tools.executor import _normalize_response
                return _normalize_response({"status": "error", "error": f"Tool '{name}' timed out after {tool.timeout_seconds}s"}, name)
            except Exception as e:
                from backend.app.tools.executor import _normalize_response
                return _normalize_response({"status": "error", "error": str(e)}, name)

        from backend.app.tools.executor import ToolExecutor
        return await ToolExecutor.execute(name, params)

# Global singleton
tool_registry = ToolRegistry()
