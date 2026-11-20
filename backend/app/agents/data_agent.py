import logging
from typing import Dict, Any
from backend.app.tools.executor import ToolExecutor

logger = logging.getLogger("data_agent")

class DataAgent:
    """
    Specialist agent for data extraction, table parsing,
    JSON/CSV exporting, and structured report generation.
    """

    @staticmethod
    async def execute_step(action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"DataAgent executing '{action}' with params: {parameters}")
        try:
            return await ToolExecutor.execute(action, parameters)
        except Exception as e:
            logger.error(f"DataAgent error: {e}")
            return {"status": "error", "error": str(e)}
