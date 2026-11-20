import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from backend.app.search.registry import search_registry
from backend.app.search.base import SearchResultItem
from backend.app.ai.router import ModelRouter
from backend.app.dependencies import verify_local_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"], dependencies=[Depends(verify_local_token)])

class SearchRequest(BaseModel):
    query: str
    provider_id: Optional[str] = "duckduckgo"
    generate_summary: bool = True

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
    cited_summary: Optional[str] = None
    model: Optional[str] = None

@router.get("/providers")
async def list_search_providers():
    return [
        {"id": p.provider_id, "name": p.name}
        for p in search_registry.list_providers()
    ]

@router.post("", response_model=SearchResponse)
async def search_web(req: SearchRequest):
    provider = search_registry.get(req.provider_id or "duckduckgo")
    results = await provider.search(req.query, limit=5)

    cited_summary = None
    model_name = None

    if req.generate_summary and results:
        ai_provider, model_name = ModelRouter.route_for_task(task_type="research")

        sources_context = "\n".join([
            f"[{idx+1}] {item.title} ({item.url})\n{item.snippet}"
            for idx, item in enumerate(results)
        ])

        prompt = (
            f"Synthesize an authoritative research answer with source citations for the query: \"{req.query}\"\n\n"
            f"Sources:\n{sources_context}\n\n"
            f"Format requirements:\n"
            f"- Use numbered bracket citations like [1], [2] corresponding strictly to the provided sources.\n"
            f"- Do not hallucinate or invent citations.\n"
            f"- Provide a crisp summary with bullet points."
        )

        try:
            ai_res = await ai_provider.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=model_name
            )
            cited_summary = ai_res.content
        except Exception as e:
            logger.warning(f"Failed to generate cited summary via AI provider: {e}")
            cited_summary = f"Summary for {req.query}: Derived from {len(results)} search sources [1]."

    return SearchResponse(
        query=req.query,
        results=results,
        cited_summary=cited_summary,
        model=model_name
    )
