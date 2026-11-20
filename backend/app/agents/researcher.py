import logging
from typing import Dict, Any, List
from backend.app.tools.executor import ToolExecutor

logger = logging.getLogger("researcher_agent")

class ResearcherAgent:
    """
    Specialist agent for web searches, multi-source exploration,
    fact comparison, and research synthesis.
    """

    @staticmethod
    async def execute_step(action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"ResearcherAgent executing '{action}' with params: {parameters}")
        try:
            if action == "search_web":
                query = parameters.get("query", "")
                return await ToolExecutor.execute("search_web", {"query": query})
            elif action == "compare_tabs":
                return await ToolExecutor.execute("compare_tabs", parameters)
            else:
                return await ToolExecutor.execute(action, parameters)
        except Exception as e:
            logger.error(f"ResearcherAgent error: {e}")
            return {"status": "error", "error": str(e)}
