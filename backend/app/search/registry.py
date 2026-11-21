import httpx
import re
import urllib.parse
from typing import List, Dict
from backend.app.search.base import BaseSearchProvider, SearchResultItem

class DuckDuckGoSearchProvider(BaseSearchProvider):
    @property
    def provider_id(self) -> str:
        return "duckduckgo"

    @property
    def name(self) -> str:
        return "DuckDuckGo Web Search"

    async def search(self, query: str, limit: int = 5) -> List[SearchResultItem]:
        results: List[SearchResultItem] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # 1. Primary: DuckDuckGo HTML search for real web search results
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                resp = await client.post("https://html.duckduckgo.com/html/", data={"q": query}, headers=headers)
                if resp.status_code == 200:
                    matches = re.findall(
                        r'<a class="result__snippet[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                        resp.text,
                        re.DOTALL
                    )
                    if matches:
                        for u, s in matches[:limit]:
                            clean_s = re.sub(r'<[^>]+>', '', s).strip()
                            clean_u = u
                            if "uddg=" in clean_u:
                                try:
                                    clean_u = urllib.parse.unquote(clean_u.split("uddg=")[1].split("&")[0])
                                except Exception:
                                    pass
                            results.append(SearchResultItem(
                                title=f"Search result for '{query}'",
                                url=clean_u,
                                snippet=clean_s
                            ))
                    else:
                        snippets = re.findall(r'<a[^>]*class="result__snippet[^"]*"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
                        urls = re.findall(r'<a[^>]*class="result__url[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
                        for idx, s in enumerate(snippets[:limit]):
                            clean_s = re.sub(r'<[^>]+>', '', s).strip()
                            url = urls[idx][0] if idx < len(urls) else f"https://duckduckgo.com/?q={query}"
                            results.append(SearchResultItem(
                                title=f"Result {idx+1} for '{query}'",
                                url=url,
                                snippet=clean_s
                            ))
        except Exception:
            pass

        # 2. Fallback to DuckDuckGo Instant Answer API if HTML search failed
        if not results:
            try:
                async with httpx.AsyncClient(timeout=6.0) as client:
                    resp = await client.get(
                        "https://api.duckduckgo.com/",
                        params={"q": query, "format": "json", "no_redirect": 1, "no_html": 1}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("AbstractText") and data.get("AbstractURL"):
                            results.append(SearchResultItem(
                                title=data.get("Heading") or query,
                                url=data.get("AbstractURL"),
                                snippet=data.get("AbstractText")
                            ))
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

        # 3. Safe fallback
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
