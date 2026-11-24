"""
Restricted MCP Gateway API for Hermes Agent.

Provides an isolated, restricted gateway exposing only a strict whitelist of tools.
Guarantees:
  1. Header authentication using X-Hermes-Token.
  2. Strict tool whitelist enforcement (no raw CDP, no arbitrary JS, no shell, no desktop control).
  3. All invocations still pass through ToolExecutor and SecurityPolicy.
  4. Actions requiring approval or blocked actions are rejected with 403.
"""
from __future__ import annotations

import logging
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel

from backend.app.config import settings
from backend.app.tools.executor import ToolExecutor
from backend.app.security.policy import SecurityPolicy, RiskTier

logger = logging.getLogger("api.hermes_gateway")

router = APIRouter(prefix="/mcp/hermes", tags=["hermes-gateway"])

# Whitelist: ONLY read-only and safe extraction tools
HERMES_ALLOWED_TOOLS = frozenset([
    "get_page_content",
    "search_web",
    "extract_table_data",
    "synthesize_research",
    "get_accessibility_tree",
    "read_pdf",
    "summarize_pdf",
])

class HermesToolCall(BaseModel):
    tool: str
    parameters: Dict[str, Any] = {}

def verify_hermes_token(x_hermes_token: str = Header(..., alias="X-Hermes-Token")) -> str:
    expected_token = getattr(settings, "HERMES_GATEWAY_TOKEN", "hermes-local-gateway-token")
    if x_hermes_token != expected_token:
        logger.warning(f"[Hermes Gateway] Unauthorized attempt with token: {x_hermes_token[:6]}...")
        raise HTTPException(status_code=403, detail="Invalid Hermes gateway token")
    return x_hermes_token

@router.get("/tools")
async def list_hermes_tools(_: str = Depends(verify_hermes_token)):
    """List tools available to Hermes Agent through the restricted gateway."""
    from backend.app.tools.registry import tool_registry
    tools = []
    for tool_name in sorted(HERMES_ALLOWED_TOOLS):
        td = tool_registry.get(tool_name)
        if td:
            tools.append({
                "name": td.name,
                "description": td.description,
                "category": td.category,
                "parameters": td.parameters_schema if isinstance(td.parameters_schema, dict) else td.parameters_schema.model_json_schema() if hasattr(td.parameters_schema, "model_json_schema") else {}
            })
        else:
            tools.append({"name": tool_name, "description": f"Restricted tool: {tool_name}"})
    return {"tools": tools}

@router.post("/tool")
async def execute_hermes_tool(
    call: HermesToolCall,
    _: str = Depends(verify_hermes_token)
):
    """Execute an approved tool call on behalf of Hermes Agent."""
    tool_name = call.tool
    params = call.parameters or {}

    # 1. Whitelist validation
    if tool_name not in HERMES_ALLOWED_TOOLS:
        logger.warning(f"[Hermes Gateway] Blocked attempt to call non-whitelisted tool: '{tool_name}'")
        raise HTTPException(
            status_code=403,
            detail=f"Tool '{tool_name}' is not in the Hermes restricted gateway whitelist."
        )

    # 2. Central Security Policy Evaluation
    policy_res = SecurityPolicy.evaluate(tool_name, params)
    if policy_res.is_blocked:
        logger.warning(f"[Hermes Gateway] Policy blocked tool '{tool_name}': {policy_res.reason}")
        raise HTTPException(
            status_code=403,
            detail=f"Tool '{tool_name}' blocked by Security Policy: {policy_res.reason}"
        )
    if policy_res.requires_approval:
        logger.warning(f"[Hermes Gateway] Tool '{tool_name}' requires approval (disallowed via external gateway)")
        raise HTTPException(
            status_code=403,
            detail=f"Tool '{tool_name}' requires human approval and cannot be executed via the external Hermes gateway."
        )

    # 3. Execution via unified ToolExecutor
    try:
        logger.info(f"[Hermes Gateway] Executing whitelisted tool '{tool_name}'")
        result = await ToolExecutor.execute(tool_name, params)
        return result
    except Exception as e:
        logger.error(f"[Hermes Gateway] Error executing tool '{tool_name}': {e}")
        return {"status": "error", "error": str(e), "tool_name": tool_name}
