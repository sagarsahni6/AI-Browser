import logging
import time
from typing import Dict, Any, Optional, List
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.repository import Repository
from backend.app.tools.executor import _normalize_response

logger = logging.getLogger("memory_agent")

class MemoryAgent:
    """
    Specialist agent for working memory management, context caching,
    and cross-step fact extraction.
    """
    _in_memory_store: Dict[str, Any] = {}

    @classmethod
    async def execute_step(cls, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if action == "store_memory":
            key = str(parameters.get("key", ""))
            value = parameters.get("value")
            category = str(parameters.get("category", "general"))
            cls._in_memory_store[key] = {
                "value": value,
                "category": category,
                "timestamp": time.time()
            }
            try:
                async with AsyncSessionLocal() as session:
                    repo = Repository(session)
                    await repo.create_user_memory(
                        key=key,
                        value=str(value),
                        category=category
                    )
            except Exception as e:
                logger.debug(f"Memory persistence notice: {e}")
            return _normalize_response({"status": "success", "key": key, "stored": True}, action)

        elif action == "retrieve_memory":
            key = str(parameters.get("key", ""))
            entry = cls._in_memory_store.get(key)
            if entry:
                return _normalize_response({"status": "success", "key": key, "value": entry["value"], "category": entry.get("category")}, action)

            # Try DB lookup
            try:
                async with AsyncSessionLocal() as session:
                    repo = Repository(session)
                    memories = await repo.get_user_memories()
                    for m in memories:
                        if m.key == key:
                            return _normalize_response({"status": "success", "key": key, "value": m.value, "category": m.category}, action)
            except Exception:
                pass
            return _normalize_response({"status": "error", "error": f"Memory key '{key}' not found."}, action)

        elif action == "get_context":
            category = parameters.get("category")
            if category:
                matched = {k: v["value"] for k, v in cls._in_memory_store.items() if v.get("category") == category}
            else:
                matched = {k: v["value"] for k, v in cls._in_memory_store.items()}
            return _normalize_response({"status": "success", "context": matched, "count": len(matched)}, action)

        else:
            from backend.app.tools.executor import ToolExecutor
            return await ToolExecutor.execute(action, parameters)
