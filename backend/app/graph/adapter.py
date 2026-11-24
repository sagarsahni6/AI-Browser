"""
NimChatModel — LangChain-compatible LLM adapter over the existing ModelRouter.

This thin wrapper lets LangGraph nodes use standard LangChain LLM calls
(bind_tools, ainvoke, etc.) while preserving:
  - Circuit breaker logic in ProviderCircuitBreaker
  - Multi-provider failover (NIM → Anthropic → Groq → ...)
  - Task-type-aware model routing (vision, tools, reasoning, ...)
  - Tool call parsing already implemented in NvidiaNimProvider

No new API calls are introduced.  All inference goes through
  ModelRouter.route_for_task() → provider.chat_completion()
exactly as before.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterator, List, Optional, AsyncIterator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult

from pydantic import ConfigDict

logger = logging.getLogger("graph.adapter")


def _to_dict(msg: BaseMessage) -> Dict[str, Any]:
    """Convert a LangChain message to the dict format used by our providers."""
    if isinstance(msg, SystemMessage):
        role = "system"
    elif isinstance(msg, HumanMessage):
        role = "user"
    elif isinstance(msg, AIMessage):
        role = "assistant"
    elif isinstance(msg, ToolMessage):
        return {
            "role": "tool",
            "tool_call_id": msg.tool_call_id,
            "name": msg.name or "",
            "content": msg.content if isinstance(msg.content, str) else json.dumps(msg.content),
        }
    else:
        role = getattr(msg, "type", "user")

    content = msg.content
    if not isinstance(content, str):
        content = json.dumps(content)

    out: Dict[str, Any] = {"role": role, "content": content}

    # Preserve tool_calls on assistant messages
    if isinstance(msg, AIMessage) and msg.tool_calls:
        out["tool_calls"] = [
            {
                "id": tc.get("id", ""),
                "type": "function",
                "function": {
                    "name": tc.get("name", ""),
                    "arguments": json.dumps(tc.get("args", {})),
                },
            }
            for tc in msg.tool_calls
        ]
    return out


def _to_ai_message(result) -> AIMessage:
    """Convert a ChatCompletionResult to a LangChain AIMessage."""
    tool_calls = []
    if result.tool_calls:
        for tc in result.tool_calls:
            fn = tc.get("function", {})
            raw_args = fn.get("arguments", "{}")
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except Exception:
                args = {}
            tool_calls.append({
                "id": tc.get("id", ""),
                "name": fn.get("name", ""),
                "args": args,
                "type": "tool_call",
            })

    return AIMessage(
        content=result.content or "",
        tool_calls=tool_calls,
        additional_kwargs={
            "finish_reason": result.finish_reason,
            "usage": result.usage,
        },
    )


class NimChatModel(BaseChatModel):
    """
    LangChain BaseChatModel backed by the AI Browser's existing ModelRouter.

    Usage in graph nodes:
        llm = NimChatModel(task_type="tools")
        llm_with_tools = llm.bind_tools(openai_tool_defs)
        result = await llm_with_tools.ainvoke(messages)
    """

    task_type: str = "tools"
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None
    _bound_tools: List[Dict[str, Any]] = []

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def _llm_type(self) -> str:
        return "nim_chat_model"

    # LangChain calls this for sync usage — not used in async graph, but required
    def _generate(self, messages: List[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        raise NotImplementedError("Use async ainvoke in graph nodes.")

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        from backend.app.ai.router import ModelRouter

        provider, model = ModelRouter.route_for_task(
            task_type=self.task_type,
            preferred_provider=self.preferred_provider,
            preferred_model=self.preferred_model,
        )

        msg_dicts = [_to_dict(m) for m in messages]
        tools = self._bound_tools or kwargs.get("tools")

        result = await provider.chat_completion(
            messages=msg_dicts,
            model=model,
            tools=tools if tools else None,
        )

        ai_msg = _to_ai_message(result)
        return ChatResult(generations=[ChatGeneration(message=ai_msg)])

    def bind_tools(self, tools: List[Any], **kwargs) -> "NimChatModel":
        """
        Bind OpenAI-format tool definitions to this model.
        Returns a new NimChatModel instance with the tools attached.
        """
        # Accept both ToolDefinition dicts and raw openai_tools format
        openai_tools = []
        for t in tools:
            if isinstance(t, dict):
                openai_tools.append(t)
            elif hasattr(t, "get_openai_tools"):
                openai_tools.extend(t.get_openai_tools())
            else:
                openai_tools.append(t)

        new = NimChatModel(
            task_type=self.task_type,
            preferred_provider=self.preferred_provider,
            preferred_model=self.preferred_model,
        )
        new._bound_tools = openai_tools
        return new
