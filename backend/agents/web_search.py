import asyncio
from dataclasses import dataclass
from tavily import TavilyClient

@dataclass
class SearchResult:
    title: str
    url: str
    content: str
    score: float

async def search(queries: list[str], api_key: str) -> list[SearchResult]:
    client = TavilyClient(api_key=api_key)

    async def run_query(q: str) -> list[SearchResult]:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: client.search(q, max_results=4, include_raw_content=False)
        )
        results = []
        for r in resp.get("results", []):
            results.append(SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                score=r.get("score", 0.0)
            ))
        return results

    batches = await asyncio.gather(*[run_query(q) for q in queries])

    seen_urls = set()
    results = []
    for batch in batches:
        for r in sorted(batch, key=lambda x: x.score, reverse=True):
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                results.append(r)

    return sorted(results, key=lambda x: x.score, reverse=True)[:8]
