import logging
from backend.app.agents.supervisor import SupervisorAgent

logger = logging.getLogger("orchestrator")

class TaskOrchestrator:
    """
    Backwards-compatible interface that delegates execution to the SupervisorAgent.
    """
    @staticmethod
    async def run_task(task_id: str):
        logger.info(f"TaskOrchestrator delegating task {task_id} to SupervisorAgent")
        await SupervisorAgent.run_task(task_id)
