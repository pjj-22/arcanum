import anthropic
from dataclasses import dataclass

@dataclass
class JudgeResult:
    approved: bool
    critique: str

JUDGE_TOOL = {
    "name": "evaluate_answer",
    "description": "Evaluate the quality and accuracy of the synthesized answer",
    "input_schema": {
        "type": "object",
        "properties": {
            "approved": {
                "type": "boolean",
                "description": "Whether the answer is acceptable to send to the user"
            },
            "critique": {
                "type": "string",
                "description": "If not approved: specific issues to fix. If approved: brief note on quality."
            }
        },
        "required": ["approved", "critique"]
    }
}

async def evaluate(query: str, answer: str, client: anthropic.AsyncAnthropic) -> JudgeResult:
    system = """You are a quality judge for an AI research assistant. Evaluate the answer against the query.

Reject (approved=false) if:
- The answer directly contradicts itself
- Key claims are made with no source support
- The query is not actually answered
- The answer is evasive or padded with filler

Approve in all other cases — do not over-reject. Minor gaps or uncertainty are acceptable."""

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=system,
        tools=[JUDGE_TOOL],
        tool_choice={"type": "tool", "name": "evaluate_answer"},
        messages=[
            {"role": "user", "content": f"Query: {query}\n\nAnswer:\n{answer}"}
        ]
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "evaluate_answer":
            return JudgeResult(
                approved=block.input["approved"],
                critique=block.input["critique"]
            )

    return JudgeResult(approved=True, critique="")
