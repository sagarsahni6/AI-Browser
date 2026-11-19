from fastapi import APIRouter, HTTPException
from typing import Any, List, Dict, Optional
from pydantic import BaseModel
from backend.app.browser.bridge import bridge
from backend.app.ai.router import ModelRouter

router = APIRouter(prefix="/browser", tags=["browser"])

class SummarizeRequest(BaseModel):
    tab_id: Optional[str] = None
    focus_query: Optional[str] = None

class CompareTabsRequest(BaseModel):
    tab_ids: Optional[List[str]] = None
    comparison_criteria: Optional[str] = None

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

@router.post("/multi-tab-context")
async def get_multi_tab_context() -> List[dict[str, Any]]:
    try:
        tabs_obs = await bridge.call("browser.inspect_all_tabs", {})
        return tabs_obs or []
    except Exception as e:
        return [{"error": str(e)}]

@router.post("/summarize")
async def summarize_page(req: SummarizeRequest) -> dict[str, Any]:
    try:
        obs = await bridge.call("browser.inspect", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect page: {e}")

    title = obs.get("title", "Untitled")
    url = obs.get("url", "")
    text = obs.get("visibleText", "")

    prompt = (
        f"Provide a structured, executive summary of the following webpage:\n"
        f"Title: {title}\n"
        f"URL: {url}\n"
        f"Content:\n{text[:6000]}\n\n"
    )
    if req.focus_query:
        prompt += f"Focus specifically on: {req.focus_query}\n"

    prompt += "\nFormat with key takeaways and bullet points."

    provider, model = ModelRouter.route_for_task(task_type="text")
    result = await provider.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        model=model
    )

    return {
        "title": title,
        "url": url,
        "summary": result.content,
        "model": model
    }

@router.post("/compare-tabs")
async def compare_tabs(req: CompareTabsRequest) -> dict[str, Any]:
    try:
        all_obs = await bridge.call("browser.inspect_all_tabs", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect tabs: {e}")

    if not all_obs or len(all_obs) < 2:
        return {
            "comparison": "At least two open tabs are required for comparison. Currently only 1 tab is available.",
            "tabs_compared": len(all_obs or [])
        }

    sources_text = ""
    for idx, obs in enumerate(all_obs[:5]):
        sources_text += f"\n--- Tab {idx+1}: {obs.get('title')} ({obs.get('url')}) ---\n"
        sources_text += f"{obs.get('visibleText', '')[:2000]}\n"

    prompt = (
        f"Compare and contrast the content across these open browser tabs:\n"
        f"{sources_text}\n"
    )
    if req.comparison_criteria:
        prompt += f"Compare specifically along these criteria: {req.comparison_criteria}\n"

    prompt += "\nProduce a clear comparison matrix and cite which tab each fact originates from."

    provider, model = ModelRouter.route_for_task(task_type="research")
    result = await provider.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        model=model
    )

    return {
        "comparison": result.content,
        "tabs_compared": len(all_obs),
        "model": model
    }
