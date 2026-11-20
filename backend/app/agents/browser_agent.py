import logging
from typing import Dict, Any
from backend.app.tools.executor import ToolExecutor

logger = logging.getLogger("browser_agent")

class BrowserAgent:
    """
    Specialist agent for DOM and visual browser interactions:
    navigating, clicking elements, typing into inputs, scrolling, and keypresses.
    """

    @staticmethod
    async def execute_step(action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"BrowserAgent executing action '{action}' with params: {parameters}")
        try:
            result = await ToolExecutor.execute(action, parameters)
            return result
        except Exception as e:
            logger.error(f"BrowserAgent failed action '{action}': {e}")
            return {"status": "error", "error": str(e)}
