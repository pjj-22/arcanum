import anthropic
import json
from dataclasses import dataclass

@dataclass
class ResearchPlan:
    search_queries: list[str]
    search_web: bool
    search_docs: bool
    doc_queries: list[str]
    reasoning: str

PLAN_TOOL = {
    "name": "create_research_plan",
    "description": "Create a structured research plan for the given query",
    "input_schema": {
        "type": "object",
        "properties": {
            "search_queries": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-3 specific web search queries with varied phrasing to maximize coverage"
            },
            "search_web": {
                "type": "boolean",
                "description": "Whether web search would help answer this query"
            },
            "search_docs": {
                "type": "boolean",
                "description": "Whether searching personal notes might be useful"
            },
            "doc_queries": {
                "type": "array",
                "items": {"type": "string"},
                "description": "1-2 queries for searching personal notes"
            },
            "reasoning": {
                "type": "string",
                "description": "Brief reasoning for the research strategy"
            }
        },
        "required": ["search_queries", "search_web", "search_docs", "doc_queries", "reasoning"]
    }
}

async def plan(query: str, has_vault: bool, client: anthropic.AsyncAnthropic) -> ResearchPlan:
    system = """You are a research planning agent for Arcanum, a personal knowledge assistant.
Given a user query, create an optimal search strategy.

Generate varied search queries that approach the topic from different angles to maximize coverage.
Only suggest searching personal notes if the query seems like something a user would have notes about."""

    messages = [{"role": "user", "content": f"Plan research for: {query}\n\nPersonal notes vault available: {has_vault}"}]

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        tools=[PLAN_TOOL],
        tool_choice={"type": "tool", "name": "create_research_plan"},
        messages=messages
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "create_research_plan":
            data = block.input
            return ResearchPlan(
                search_queries=data["search_queries"],
                search_web=data["search_web"],
                search_docs=data.get("search_docs", False) and has_vault,
                doc_queries=data.get("doc_queries", []),
                reasoning=data.get("reasoning", "")
            )

    raise ValueError("Supervisor failed to produce a plan")
