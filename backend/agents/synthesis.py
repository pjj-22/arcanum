import anthropic
from .web_search import SearchResult
from .docs_agent import DocResult

def _format_web(results: list[SearchResult]) -> str:
    if not results:
        return "No web results found."
    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"[{i}] {r.title}\nURL: {r.url}\n{r.content}")
    return "\n\n".join(parts)

def _format_docs(results: list[DocResult]) -> str:
    if not results:
        return ""
    parts = []
    for r in results:
        parts.append(f"Note: {r.title} ({r.path})\n{r.excerpt}")
    return "\n\n".join(parts)

async def synthesize(
    query: str,
    web_results: list[SearchResult],
    doc_results: list[DocResult],
    critique: str | None,
    client: anthropic.AsyncAnthropic
) -> str:
    web_section = _format_web(web_results)
    doc_section = _format_docs(doc_results)

    sources_block = f"## Web Sources\n{web_section}"
    if doc_section:
        sources_block += f"\n\n## Personal Notes\n{doc_section}"

    critique_block = ""
    if critique:
        critique_block = f"\n\nPrevious answer was rejected. Critique to address:\n{critique}\n"

    system = """You are Arcanum, a personal research assistant. Synthesize the provided sources into a clear, thorough answer.

Guidelines:
- Lead with the direct answer, then provide supporting detail
- Cite sources inline using [1], [2] etc. for web results
- Note when personal notes add context
- Be honest when sources conflict or are incomplete
- Use markdown formatting (headers, bullets) for readability
- Do not pad or repeat yourself"""

    messages = [
        {
            "role": "user",
            "content": f"Query: {query}\n{critique_block}\n\n{sources_block}"
        }
    ]

    async with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system,
        messages=messages
    ) as stream:
        async for text in stream.text_stream:
            yield text
