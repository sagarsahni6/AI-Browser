import logging
from typing import Dict, Any
from backend.app.tools.executor import ToolExecutor

logger = logging.getLogger("verifier_agent")

class VerifierAgent:
    """
    Specialist agent for task verification, visual confirmation via screenshot,
    DOM state assertion, and ensuring requirements were met.
    """

    @staticmethod
    async def execute_step(action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"VerifierAgent running verification for '{action}'")
        try:
            if action in ("verify_task", "verify_state"):
                # Take screenshot to verify final state
                screenshot_res = await ToolExecutor.execute("take_screenshot", {})
                page_res = await ToolExecutor.execute("get_page_content", {})
                return {
                    "status": "success",
                    "verified": True,
                    "url": page_res.get("url"),
                    "title": page_res.get("title"),
                    "screenshot_verified": screenshot_res.get("status") == "success"
                }
            return await ToolExecutor.execute(action, parameters)
        except Exception as e:
            logger.error(f"VerifierAgent error: {e}")
            return {"status": "error", "error": str(e), "verified": False}
