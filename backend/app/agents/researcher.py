import logging
from typing import Dict, Any, List, Optional
from backend.app.tools.executor import ToolExecutor
from backend.app.research.service import ResearchService

logger = logging.getLogger("researcher_agent")

class ResearcherAgent:
    """
    Specialist agent for web searches, multi-source exploration,
    fact comparison, and deep research synthesis.
    """

    @classmethod
    async def execute_step(cls, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"ResearcherAgent executing '{action}' with params: {parameters}")
        try:
            if action == "synthesize_research":
                topic = parameters.get("topic", "")
                sources = parameters.get("sources", [])
                depth = parameters.get("depth", "quick")
                return await ResearchService.synthesize(topic=topic, sources=sources, depth=depth)
            elif action == "search_web":
                query = parameters.get("query", "")
                return await ToolExecutor.execute("search_web", {"query": query})
            elif action == "compare_tabs":
                return await ToolExecutor.execute("compare_tabs", parameters)
            else:
                return await ToolExecutor.execute(action, parameters)
        except Exception as e:
            logger.error(f"ResearcherAgent error: {e}")
            return {"status": "error", "error": str(e)}
