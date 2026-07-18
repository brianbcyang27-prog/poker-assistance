"""Daily Journal — Structured daily memory summaries.

The journal captures daily summaries of what happened, what was learned,
what decisions were made, and what to continue tomorrow.

Usage:
    journal = DailyJournal(db)
    await journal.write_entry("Today I fixed the memory leak in the database pool...")
    entries = await journal.get_recent(days=7)
"""

import time
import json
import logging
from typing import Optional
from dataclasses import dataclass

log = logging.getLogger("jarvis.memory.journal")


@dataclass
class JournalEntry:
    id: int
    date: str              # YYYY-MM-DD
    summary: str           # what happened today
    highlights: list[str]  # key achievements
    decisions: list[str]   # decisions made
    tomorrow: list[str]    # things to continue tomorrow
    mood: str              # neutral, focused, productive, stuck
    importance: float      # 0-1
    tags: list[str]
    created_at: float


class DailyJournal:
    """Manages daily journal entries for long-term memory continuity.

    Creates a daily narrative that helps JARVIS understand:
    - What was accomplished over time
    - Patterns in work and decisions
    - What needs to be continued
    - How the user is feeling about the project

    Usage:
        journal = DailyJournal(db)
        await journal.log_conversation(session_id, summary, decisions)
        today = await journal.get_today()
        week = await journal.get_recent(days=7)
    """

    async def _ensure_table(self):
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS daily_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                summary TEXT,
                highlights TEXT DEFAULT '[]',
                decisions TEXT DEFAULT '[]',
                tomorrow TEXT DEFAULT '[]',
                mood TEXT DEFAULT 'neutral',
                importance REAL DEFAULT 0.5,
                tags TEXT DEFAULT '[]',
                created_at REAL DEFAULT (strftime('%s', 'now'))
            )
        """)
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_journal_date ON daily_journal(date)"
        )

    def __init__(self, db=None):
        self._db = db
        self._initialized = False

    async def _ensure_db(self):
        if self._initialized:
            return
        if self._db is None:
            from ..core.database import get_db
            self._db = await get_db()
        await self._ensure_table()
        self._initialized = True

    async def log_conversation(
        self,
        session_id: str,
        summary: str,
        decisions: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
    ):
        """Log a conversation summary to today's journal entry."""
        await self._ensure_db()
        today = self._today()
        entry = await self._get_or_create_entry(today)

        # Append summary to highlights if significant
        highlights = json.loads(entry["highlights"]) if entry["highlights"] else []
        if summary and len(summary) > 20:
            highlights.append(summary[:200])

        # Append decisions
        existing_decisions = json.loads(entry["decisions"]) if entry["decisions"] else []
        if decisions:
            existing_decisions.extend(decisions)

        # Merge tags
        existing_tags = json.loads(entry["tags"]) if entry["tags"] else []
        if tags:
            existing_tags = list(set(existing_tags + tags))

        await self._db.execute(
            """UPDATE daily_journal
               SET highlights = ?, decisions = ?, tags = ?
               WHERE id = ?""",
            (
                json.dumps(highlights[-20:]),  # keep last 20
                json.dumps(existing_decisions[-10:]),
                json.dumps(existing_tags),
                entry["id"],
            ),
        )
        await self._db.commit()

    async def add_highlight(self, highlight: str, tags: Optional[list[str]] = None):
        """Add a highlight to today's journal."""
        await self._ensure_db()
        today = self._today()
        entry = await self._get_or_create_entry(today)

        highlights = json.loads(entry["highlights"]) if entry["highlights"] else []
        highlights.append(highlight[:300])

        existing_tags = json.loads(entry["tags"]) if entry["tags"] else []
        if tags:
            existing_tags = list(set(existing_tags + tags))

        await self._db.execute(
            "UPDATE daily_journal SET highlights = ?, tags = ? WHERE id = ?",
            (json.dumps(highlights[-20:]), json.dumps(existing_tags), entry["id"]),
        )
        await self._db.commit()

    async def add_decision(self, decision: str):
        """Record a decision made today."""
        await self._ensure_db()
        today = self._today()
        entry = await self._get_or_create_entry(today)

        decisions = json.loads(entry["decisions"]) if entry["decisions"] else []
        decisions.append(decision[:300])

        await self._db.execute(
            "UPDATE daily_journal SET decisions = ? WHERE id = ?",
            (json.dumps(decisions[-10:]), entry["id"]),
        )
        await self._db.commit()

    async def set_tomorrow(self, items: list[str]):
        """Set things to continue tomorrow."""
        await self._ensure_db()
        today = self._today()
        entry = await self._get_or_create_entry(today)

        await self._db.execute(
            "UPDATE daily_journal SET tomorrow = ? WHERE id = ?",
            (json.dumps(items[:5]), entry["id"]),
        )
        await self._db.commit()

    async def set_mood(self, mood: str):
        """Set today's mood: neutral, focused, productive, stuck."""
        await self._ensure_db()
        today = self._today()
        entry = await self._get_or_create_entry(today)

        await self._db.execute(
            "UPDATE daily_journal SET mood = ? WHERE id = ?",
            (mood, entry["id"]),
        )
        await self._db.commit()

    async def set_summary(self, summary: str):
        """Set today's summary."""
        await self._ensure_db()
        today = self._today()
        entry = await self._get_or_create_entry(today)

        await self._db.execute(
            "UPDATE daily_journal SET summary = ? WHERE id = ?",
            (summary[:500], entry["id"]),
        )
        await self._db.commit()

    async def get_today(self) -> Optional[JournalEntry]:
        """Get today's journal entry."""
        await self._ensure_db()
        return self._row_to_entry(await self._get_or_create_entry(self._today()))

    async def get_entry(self, date: str) -> Optional[JournalEntry]:
        """Get journal entry for a specific date (YYYY-MM-DD)."""
        await self._ensure_db()
        cursor = await self._db.execute(
            "SELECT * FROM daily_journal WHERE date = ?", (date,)
        )
        row = await cursor.fetchone()
        return self._row_to_entry(row) if row else None

    async def get_recent(self, days: int = 7) -> list[JournalEntry]:
        """Get journal entries for the last N days."""
        await self._ensure_db()
        import datetime
        cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
        cursor = await self._db.execute(
            "SELECT * FROM daily_journal WHERE date >= ? ORDER BY date DESC",
            (cutoff,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_entry(r) for r in rows]

    async def get_summary_for_context(self, days: int = 3) -> str:
        """Get a compact summary of recent days for LLM context injection."""
        entries = await self.get_recent(days)
        if not entries:
            return "No recent journal entries."

        lines = [f"=== Last {days} Days ==="]
        for entry in entries:
            if not entry:
                continue
            line = f"\n📅 {entry.date}"
            if entry.summary:
                line += f" — {entry.summary}"
            if entry.decisions:
                line += f"\n  Decisions: {'; '.join(entry.decisions[:3])}"
            if entry.tomorrow:
                line += f"\n  Continue: {'; '.join(entry.tomorrow[:2])}"
            if entry.mood and entry.mood != "neutral":
                line += f"\n  Mood: {entry.mood}"
            lines.append(line)

        return "\n".join(lines)

    async def _get_or_create_entry(self, date: str) -> dict:
        """Get or create a journal entry for a date."""
        cursor = await self._db.execute(
            "SELECT * FROM daily_journal WHERE date = ?", (date,)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "id": row[0], "date": row[1], "summary": row[2],
                "highlights": row[3], "decisions": row[4],
                "tomorrow": row[5], "mood": row[6],
                "importance": row[7], "tags": row[8], "created_at": row[9],
            }

        cursor = await self._db.execute(
            """INSERT INTO daily_journal (date) VALUES (?) RETURNING
               id, date, summary, highlights, decisions, tomorrow,
               mood, importance, tags, created_at""",
            (date,),
        )
        row = await cursor.fetchone()
        await self._db.commit()
        return {
            "id": row[0], "date": row[1], "summary": row[2],
            "highlights": row[3], "decisions": row[4],
            "tomorrow": row[5], "mood": row[6],
            "importance": row[7], "tags": row[8], "created_at": row[9],
        }

    def _row_to_entry(self, row) -> Optional[JournalEntry]:
        if not row:
            return None
        if isinstance(row, dict):
            d = row
        else:
            d = {
                "id": row[0], "date": row[1], "summary": row[2],
                "highlights": row[3], "decisions": row[4],
                "tomorrow": row[5], "mood": row[6],
                "importance": row[7], "tags": row[8], "created_at": row[9],
            }
        return JournalEntry(
            id=d["id"],
            date=d["date"],
            summary=d["summary"] or "",
            highlights=json.loads(d["highlights"]) if d["highlights"] else [],
            decisions=json.loads(d["decisions"]) if d["decisions"] else [],
            tomorrow=json.loads(d["tomorrow"]) if d["tomorrow"] else [],
            mood=d["mood"] or "neutral",
            importance=d["importance"] or 0.5,
            tags=json.loads(d["tags"]) if d["tags"] else [],
            created_at=d["created_at"] or 0,
        )

    def _today(self) -> str:
        import datetime
        return datetime.date.today().isoformat()


# Module-level singleton
_journal: Optional[DailyJournal] = None


def get_journal(db=None) -> DailyJournal:
    global _journal
    if _journal is None:
        _journal = DailyJournal(db)
    return _journal
