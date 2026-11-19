import httpx
from typing import List, Dict
from backend.app.search.base import BaseSearchProvider, SearchResultItem

class DuckDuckGoSearchProvider(BaseSearchProvider):
    @property
    def provider_id(self) -> str:
        return "duckduckgo"

    @property
    def name(self) -> str:
        return "DuckDuckGo Instant Answer"

    async def search(self, query: str, limit: int = 5) -> List[SearchResultItem]:
        results: List[SearchResultItem] = []
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_redirect": 1, "no_html": 1}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # 1. Primary abstract
                    if data.get("AbstractText") and data.get("AbstractURL"):
                        results.append(SearchResultItem(
                            title=data.get("Heading") or query,
                            url=data.get("AbstractURL"),
                            snippet=data.get("AbstractText")
                        ))

                    # 2. Related topics
                    for topic in data.get("RelatedTopics", []):
                        if "Text" in topic and "FirstURL" in topic:
                            results.append(SearchResultItem(
                                title=topic.get("Text", "")[:60],
                                url=topic["FirstURL"],
                                snippet=topic.get("Text", "")
                            ))
                            if len(results) >= limit:
                                break
        except Exception:
            pass

        # Fallback if no instant answers returned
        if not results:
            results.append(SearchResultItem(
                title=f"Web search for '{query}'",
                url=f"https://duckduckgo.com/?q={query}",
                snippet=f"Live search query on DuckDuckGo for: {query}"
            ))

        return results[:limit]

class SearchRegistry:
    def __init__(self):
        self._providers: Dict[str, BaseSearchProvider] = {
            "duckduckgo": DuckDuckGoSearchProvider()
        }

    def get(self, pid: str = "duckduckgo") -> BaseSearchProvider:
        return self._providers.get(pid, self._providers["duckduckgo"])

    def list_providers(self) -> List[BaseSearchProvider]:
        return list(self._providers.values())

search_registry = SearchRegistry()
