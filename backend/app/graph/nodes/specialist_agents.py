"""
Specialist agent nodes — thin wrappers over existing agent classes.

Each node follows the same contract:
  Input:  GraphState with current_step set by supervisor
  Output: GraphState with step_results appended, current_step_index incremented,
          next_agent set to "supervisor" (or "recovery_agent" on error)

The actual logic lives in backend/app/agents/*.py and is NOT duplicated here.
"""
from __future__ import annotations

import logging
from typing import Dict, Any

from backend.app.graph.state import GraphState

logger = logging.getLogger("graph.nodes.agents")


def _make_agent_node(agent_class, agent_label: str):
    """Factory: creates a typed graph node for a given agent class."""

    async def node(state: GraphState) -> GraphState:
        step: Dict[str, Any] = state.get("current_step") or {}
        action: str = step.get("action", "")
        params: Dict[str, Any] = step.get("parameters") or {}
        idx: int = state.get("current_step_index", 0)
        task_id: str = state.get("task_id", "")

        logger.info(f"[{agent_label}] Executing step {idx}: action='{action}'")

        try:
            result: Dict[str, Any] = await agent_class.execute_step(action, params)
        except Exception as e:
            logger.error(f"[{agent_label}] Exception on action='{action}': {e}")
            result = {"status": "error", "error": str(e)}

        exec_status = result.get("status", "completed")
        next_agent = "recovery_agent" if exec_status == "error" else "supervisor"

        # Objective verification strategy (mirrors legacy SupervisorAgent logic)
        v_strat = step.get("verification_strategy", "none")
        if v_strat and v_strat != "none" and exec_status in ("completed", "success"):
            try:
                from backend.app.agents.verifier import VerifierAgent
                v_params = dict(step.get("verification_params") or {})
                if "expected_url_pattern" in v_params and "pattern" not in v_params:
                    v_params["pattern"] = v_params["expected_url_pattern"]
                if "records" not in v_params:
                    v_params["records"] = result.get("result") or result.get("data") or []

                v_res: Dict[str, Any] = {}
                if v_strat == "dom_assertion":
                    v_res = await VerifierAgent.verify_dom_assertion(v_params)
                elif v_strat == "url_match":
                    v_res = await VerifierAgent.verify_url_match(v_params)
                elif v_strat == "data_validation":
                    v_res = VerifierAgent.verify_data_validation(v_params)
                elif v_strat == "file_validation":
                    v_res = VerifierAgent.verify_file_validation(v_params)
                elif v_strat == "form_submission":
                    v_res = await VerifierAgent.verify_form_submission(v_params)

                if v_res and not v_res.get("verified", True):
                    exec_status = "failed"
                    result["status"] = "failed"
                    result["error"] = f"Verification failed: {v_res.get('reason')}"
                    next_agent = "recovery_agent"
            except Exception as ve:
                logger.warning(f"[{agent_label}] Verification error (non-fatal): {ve}")

        return {
            "step_results": [result],
        }

    node.__name__ = f"{agent_label.lower().replace(' ', '_')}_node"
    return node


# ── Import existing agents ────────────────────────────────────────────────────
from backend.app.agents.browser_agent import BrowserAgent
from backend.app.agents.dom_agent import DOMAgent
from backend.app.agents.vision_agent import VisionAgent
from backend.app.agents.researcher import ResearcherAgent
from backend.app.agents.data_agent import DataAgent
from backend.app.agents.desktop_agent import DesktopAgent
from backend.app.agents.file_agent import FileAgent
from backend.app.agents.memory_agent import MemoryAgent

# ── Node functions ────────────────────────────────────────────────────────────
browser_agent_node = _make_agent_node(BrowserAgent, "BrowserAgent")
dom_agent_node = _make_agent_node(DOMAgent, "DOMAgent")
vision_agent_node = _make_agent_node(VisionAgent, "VisionAgent")
research_agent_node = _make_agent_node(ResearcherAgent, "ResearchAgent")
data_agent_node = _make_agent_node(DataAgent, "DataAgent")
desktop_agent_node = _make_agent_node(DesktopAgent, "DesktopAgent")
file_agent_node = _make_agent_node(FileAgent, "FileAgent")
memory_agent_node = _make_agent_node(MemoryAgent, "MemoryAgent")
