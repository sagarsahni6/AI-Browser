from fastapi import APIRouter
from typing import Any, List
from backend.app.browser.bridge import bridge

router = APIRouter(prefix="/browser", tags=["browser"])

@router.get("/tabs")
async def get_tabs() -> List[dict[str, Any]]:
    try:
        tabs = await bridge.call("browser.get_tabs", {})
        return tabs or []
    except Exception as e:
        return [{"error": str(e)}]

@router.post("/context")
async def get_page_context() -> dict[str, Any]:
    try:
        obs = await bridge.call("browser.inspect", {})
        return obs or {}
    except Exception as e:
        return {"error": str(e)}
