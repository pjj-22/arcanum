import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agents import supervisor, web_search, docs_agent, synthesis, judge
import db

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_client() -> anthropic.AsyncAnthropic:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")
    return anthropic.AsyncAnthropic(api_key=key)

def event(type: str, **data) -> dict:
    return {"data": json.dumps({"type": type, **data})}


class ResearchRequest(BaseModel):
    query: str

class SettingsUpdate(BaseModel):
    vault_path: str | None = None
    anthropic_key: str | None = None


@app.post("/api/research")
async def research(req: ResearchRequest):
    async def stream() -> AsyncGenerator:
        client = get_client()
        tavily_key = os.getenv("TAVILY_API_KEY", "")
        vault_path = os.getenv("VAULT_PATH", "")
        has_vault = bool(vault_path and os.path.exists(vault_path))

        session_id = await db.create_session(req.query)
        yield event("session", id=session_id)
        print(f"[arcanum] session {session_id} | query: {req.query!r}")
        print(f"[arcanum] has_vault={has_vault} vault_path={vault_path!r}")

        # Supervisor
        yield event("agent", name="supervisor", status="running", detail="Planning search strategy...")
        print("[arcanum] supervisor: calling plan()")
        try:
            plan = await supervisor.plan(req.query, has_vault, client)
        except Exception as e:
            print(f"[arcanum] supervisor FAILED: {e}")
            yield event("error", message=f"Supervisor failed: {str(e)}")
            return
        print(f"[arcanum] supervisor done | web={plan.search_web} docs={plan.search_docs} queries={plan.search_queries}")
        yield event("agent", name="supervisor", status="done", detail=plan.reasoning)

        # Parallel retrieval
        web_results = []
        doc_results = []
        tasks = []

        if plan.search_web and tavily_key:
            print(f"[arcanum] web_search: starting with queries {plan.search_queries}")
            yield event("agent", name="web_search", status="running",
                       detail=f"Searching: {', '.join(repr(q) for q in plan.search_queries)}")
            tasks.append(("web", web_search.search(plan.search_queries, tavily_key)))

        if plan.search_docs and has_vault and plan.doc_queries:
            print(f"[arcanum] docs: starting with queries {plan.doc_queries}")
            yield event("agent", name="docs", status="running", detail="Searching personal notes...")
            tasks.append(("docs", docs_agent.search(plan.doc_queries, vault_path)))

        if tasks:
            results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
            for (name, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    print(f"[arcanum] {name} FAILED: {result}")
                    yield event("agent", name=name, status="error", detail=str(result))
                elif name == "web":
                    web_results = result
                    print(f"[arcanum] web_search done | {len(web_results)} results")
                    yield event("agent", name="web_search", status="done",
                               detail=f"Found {len(web_results)} sources")
                else:
                    doc_results = result
                    print(f"[arcanum] docs done | {len(doc_results)} results")
                    yield event("agent", name="docs", status="done",
                               detail=f"Found {len(doc_results)} notes")

        # Synthesis + Judge loop (max 2 attempts)
        final_answer = ""
        critique = None

        for attempt in range(2):
            yield event("agent", name="synthesis", status="running",
                       detail="Compiling findings..." if attempt == 0 else "Revising answer...")

            full_answer = ""
            yield event("stream_start")
            async for chunk in synthesis.synthesize(req.query, web_results, doc_results, critique, client):
                full_answer += chunk
                yield event("stream_chunk", text=chunk)
            yield event("stream_end")

            yield event("agent", name="synthesis", status="done", detail="")

            yield event("agent", name="judge", status="running", detail="Evaluating answer quality...")
            result = await judge.evaluate(req.query, full_answer, client)
            yield event("agent", name="judge", status="done",
                       detail=result.critique if result.approved else f"Rejected: {result.critique}")

            final_answer = full_answer
            if result.approved:
                break
            critique = result.critique

        # Build sources list
        sources = [
            {"title": r.title, "url": r.url, "score": r.score}
            for r in web_results
        ] + [
            {"title": r.title, "path": r.path}
            for r in doc_results
        ]

        await db.complete_session(session_id, final_answer, sources)
        yield event("complete", sources=sources)

    return EventSourceResponse(stream())


class SaveNoteRequest(BaseModel):
    query: str
    answer: str
    sources: list[dict]

ENRICH_TOOL = {
    "name": "enrich_note",
    "description": "Generate tags and find related vault notes for this research",
    "input_schema": {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-4 lowercase single-word or hyphenated tags describing the topic (e.g. algorithms, dynamic-programming, web-dev)"
            },
            "related_notes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Titles of existing vault notes that are genuinely related to this research. Only include notes that share meaningful topic overlap."
            }
        },
        "required": ["tags", "related_notes"]
    }
}

async def _generate_note_title(query: str, answer: str, client: anthropic.AsyncAnthropic) -> str:
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=64,
        system="Generate a concise note title (4-7 words, title case, no punctuation at end) for the research below. Return only the title, nothing else.",
        messages=[{"role": "user", "content": f"Query: {query}\n\nAnswer excerpt: {answer[:300]}"}]
    )
    title = response.content[0].text.strip().strip('"').strip("'")
    return title or query[:60]

async def _enrich_note(title: str, answer: str, vault_notes: list[str], client: anthropic.AsyncAnthropic) -> dict:
    notes_list = "\n".join(f"- {n}" for n in vault_notes) if vault_notes else "None"
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        system="You help organize a personal knowledge vault. Generate tags and identify related notes.",
        tools=[ENRICH_TOOL],
        tool_choice={"type": "tool", "name": "enrich_note"},
        messages=[{
            "role": "user",
            "content": f"Note title: {title}\n\nContent excerpt: {answer[:500]}\n\nExisting vault notes:\n{notes_list}"
        }]
    )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    return {"tags": [], "related_notes": []}

def _get_vault_note_titles(vault_path: str) -> list[str]:
    from pathlib import Path
    vault = Path(vault_path)
    return [p.stem for p in vault.rglob("*.md")]

@app.post("/api/vault/save")
async def save_to_vault(req: SaveNoteRequest):
    vault_path = os.getenv("VAULT_PATH", "")
    if not vault_path or not os.path.exists(vault_path):
        raise HTTPException(status_code=400, detail="No vault configured or vault path does not exist")

    client = get_client()
    vault_titles = _get_vault_note_titles(vault_path)

    title = await _generate_note_title(req.query, req.answer, client)
    enrichment = await _enrich_note(title, req.answer, vault_titles, client)

    safe_filename = "".join(c if c.isalnum() or c in " -_" else "" for c in title).strip()[:80]
    filepath = os.path.join(vault_path, "Nexus", f"{safe_filename}.md")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")

    tags = ["nexus"] + enrichment.get("tags", [])
    tag_str = ", ".join(tags)

    web_sources = [s for s in req.sources if "url" in s]
    doc_sources = [s for s in req.sources if "path" in s]
    related = enrichment.get("related_notes", [])

    sources_section = ""
    if web_sources:
        sources_section += "\n\n## Sources\n"
        for i, s in enumerate(web_sources, 1):
            sources_section += f"{i}. [{s['title'] or s['url']}]({s['url']})\n"

    related_all = list({r for r in related} | {s["title"] for s in doc_sources if "title" in s})
    if related_all:
        sources_section += "\n\n## Related Notes\n"
        for r in related_all:
            sources_section += f"- [[{r}]]\n"

    content = (
        f"---\n"
        f"tags: [{tag_str}]\n"
        f"date: {date_str}\n"
        f"query: \"{req.query}\"\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"{req.answer}"
        f"{sources_section}"
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "path": os.path.join("Nexus", f"{safe_filename}.md"),
        "title": title,
        "tags": tags,
        "related": related_all
    }


@app.get("/api/history")
async def get_history():
    return await db.get_history()


@app.get("/api/history/{session_id}")
async def get_session(session_id: str):
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.delete("/api/history/{session_id}")
async def delete_session(session_id: str):
    deleted = await db.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@app.post("/api/settings")
async def update_settings(settings: SettingsUpdate):
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(env_path) as f:
        lines = f.readlines()

    updates = {}
    if settings.vault_path is not None:
        updates["VAULT_PATH"] = settings.vault_path
    if settings.anthropic_key is not None:
        updates["ANTHROPIC_API_KEY"] = settings.anthropic_key

    new_lines = []
    found = set()
    for line in lines:
        key = line.split("=")[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
            found.add(key)
        else:
            new_lines.append(line)

    for key, val in updates.items():
        if key not in found:
            new_lines.append(f"{key}={val}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)

    load_dotenv(override=True)
    return {"ok": True}


@app.get("/api/settings")
async def get_settings():
    return {
        "vault_path": os.getenv("VAULT_PATH", ""),
        "has_anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY")),
        "has_tavily_key": bool(os.getenv("TAVILY_API_KEY")),
    }
