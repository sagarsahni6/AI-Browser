import json
import logging
from typing import Dict, Any, Optional
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.repository import Repository

logger = logging.getLogger("checkpoint_manager")

class CheckpointManager:
    """Manages SQLite persistence of execution checkpoints for tasks."""

    @staticmethod
    async def save_checkpoint(task_id: str, step_number: int, state: Dict[str, Any]) -> str:
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            checkpoint = await repo.create_runtime_checkpoint(
                task_id=task_id,
                step_number=step_number,
                state=state
            )
            logger.info(f"Saved runtime checkpoint for task {task_id} at step {step_number}")
            return checkpoint.id

    @staticmethod
    async def load_checkpoint(task_id: str) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            checkpoint = await repo.get_latest_runtime_checkpoint(task_id)
            if not checkpoint:
                return None
            try:
                return json.loads(checkpoint.state_json)
            except Exception as e:
                logger.error(f"Failed to parse checkpoint JSON for task {task_id}: {e}")
                return None

    @staticmethod
    async def clear_checkpoint(task_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            return await repo.clear_runtime_checkpoints(task_id)
