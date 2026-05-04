import aiosqlite
import json
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "arcanum.db"

async def init():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                answer TEXT,
                sources TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.commit()

async def create_session(query: str) -> str:
    session_id = str(uuid.uuid4())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sessions (id, query) VALUES (?, ?)",
            (session_id, query)
        )
        await db.commit()
    return session_id

async def complete_session(session_id: str, answer: str, sources: list):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET answer = ?, sources = ? WHERE id = ?",
            (answer, json.dumps(sources), session_id)
        )
        await db.commit()

async def get_history(limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, query, created_at FROM sessions ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def delete_session(session_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await db.commit()
        return cursor.rowcount > 0

async def get_session(session_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        if d.get("sources"):
            d["sources"] = json.loads(d["sources"])
        return d
