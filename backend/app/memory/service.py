import logging
import json
import time
from typing import Dict, Any, List, Optional
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.repository import Repository
from backend.app.database.models import UserMemory
from sqlalchemy import select, delete

logger = logging.getLogger("memory_service")

class MemoryService:
    """
    Persistent Long-Term Memory Service:
    Stores and recalls user preferences, behavioral traits, and cross-session context.
    """

    @classmethod
    async def remember(
        cls,
        key: str,
        value: str,
        category: str = "preference",
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Add or update a persistent user memory."""
        k = key.strip()
        v = value.strip()
        tags_list = tags or []

        async with AsyncSessionLocal() as session:
            # Check if key already exists
            stmt = select(UserMemory).where(UserMemory.key == k)
            res = await session.execute(stmt)
            existing = res.scalars().first()

            if existing:
                existing.value = v
                existing.category = category
                existing.tags_json = json.dumps(tags_list)
                existing.updated_at = time.time()
                await session.commit()
                await session.refresh(existing)
                return {
                    "id": existing.id,
                    "key": existing.key,
                    "value": existing.value,
                    "category": existing.category,
                    "action": "updated"
                }
            else:
                repo = Repository(session)
                mem = await repo.create_user_memory(key=k, value=v, category=category, tags=tags_list)
                return {
                    "id": mem.id,
                    "key": mem.key,
                    "value": mem.value,
                    "category": mem.category,
                    "action": "created"
                }

    @classmethod
    async def recall(cls, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search stored memories by keyword query."""
        q_lower = query.lower().strip()
        results: List[Dict[str, Any]] = []

        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            memories = await repo.get_user_memories(category=category)

            for m in memories:
                k_match = q_lower in m.key.lower()
                v_match = q_lower in m.value.lower()
                tags = json.loads(m.tags_json or "[]")
                tag_match = any(q_lower in str(t).lower() for t in tags)

                if k_match or v_match or tag_match:
                    results.append({
                        "id": m.id,
                        "key": m.key,
                        "value": m.value,
                        "category": m.category,
                        "tags": tags,
                        "updated_at": m.updated_at
                    })

        return results

    @classmethod
    async def get_all(cls, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all memories, optionally filtered by category."""
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            memories = await repo.get_user_memories(category=category)
            return [
                {
                    "id": m.id,
                    "key": m.key,
                    "value": m.value,
                    "category": m.category,
                    "tags": json.loads(m.tags_json or "[]"),
                    "updated_at": m.updated_at
                }
                for m in memories
            ]

    @classmethod
    async def forget(cls, memory_id: str) -> bool:
        """Delete a memory by ID."""
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            return await repo.delete_user_memory(memory_id)

    @classmethod
    async def get_memory_context(cls, category: Optional[str] = None, limit: int = 15) -> str:
        """
        Format active memories as context lines for system prompt injection.
        """
        memories = await cls.get_all(category=category)
        if not memories:
            return ""

        lines = ["[USER PREFERENCES & LONG-TERM CONTEXT]"]
        for m in memories[:limit]:
            lines.append(f"- {m['key']}: {m['value']}")
        return "\n".join(lines) + "\n"
