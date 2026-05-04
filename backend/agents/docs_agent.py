import os
import re
from dataclasses import dataclass
from pathlib import Path

@dataclass
class DocResult:
    title: str
    path: str
    excerpt: str
    score: float

def _score_file(content: str, queries: list[str]) -> float:
    content_lower = content.lower()
    score = 0.0
    for query in queries:
        for term in query.lower().split():
            if len(term) > 3:
                score += content_lower.count(term) * (1.0 / len(term))
    return score

def _extract_excerpt(content: str, queries: list[str], max_chars: int = 600) -> str:
    terms = {t.lower() for q in queries for t in q.split() if len(t) > 3}
    lines = content.split("\n")
    best_lines = []
    best_score = -1

    for i, line in enumerate(lines):
        line_lower = line.lower()
        score = sum(line_lower.count(t) for t in terms)
        if score > best_score:
            best_score = score
            start = max(0, i - 1)
            end = min(len(lines), i + 4)
            best_lines = lines[start:end]

    excerpt = "\n".join(best_lines).strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars] + "..."
    return excerpt or content[:max_chars]

async def search(queries: list[str], vault_path: str) -> list[DocResult]:
    vault = Path(vault_path)
    if not vault.exists():
        return []

    md_files = list(vault.rglob("*.md"))
    results = []

    for filepath in md_files:
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            if not content.strip():
                continue
            score = _score_file(content, queries)
            if score > 0:
                title = filepath.stem.replace("-", " ").replace("_", " ")
                excerpt = _extract_excerpt(content, queries)
                results.append(DocResult(
                    title=title,
                    path=str(filepath.relative_to(vault)),
                    excerpt=excerpt,
                    score=score
                ))
        except Exception:
            continue

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:5]
