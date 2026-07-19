"""JARVIS Daily Journal & Weekly Review — structured daily memory and reflection.

Maintains daily journal entries with event logging, auto-summarization,
and weekly review generation by aggregating daily journals.

Usage:
    engine = JournalEngine()
    await engine.start_day()
    await engine.log_event(JournalEvent(...))
    today = await engine.get_today()
    review = await engine.generate_weekly_review()
"""

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .models import (
    DailyJournal,
    EventCategory,
    JournalEvent,
    WeeklyReview,
)

logger = logging.getLogger(__name__)


class JournalEngine:
    """Maintains daily journals and generates weekly reviews."""

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self._storage_dir = storage_dir or os.path.join(
            os.path.expanduser("~"), ".jarvis", "journal"
        )
        self._journals: Dict[str, DailyJournal] = {}
        self._reviews: Dict[str, WeeklyReview] = {}
        self._today_str: Optional[str] = None

    def _today(self) -> str:
        """Return today's date as YYYY-MM-DD."""
        if self._today_str is not None:
            return self._today_str
        return datetime.now().strftime("%Y-%m-%d")

    def set_today(self, date_str: str) -> None:
        """Override today's date (useful for testing)."""
        self._today_str = date_str

    def _week_key(self, date_str: str) -> str:
        """Return the week key YYYY-WXX for a given date string."""
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        iso_cal = dt.isocalendar()
        return f"{iso_cal[0]}-W{iso_cal[1]:02d}"

    def _week_bounds(self, date_str: Optional[str] = None) -> tuple:
        """Return (week_start, week_end) for the given or current date."""
        if date_str is None:
            date_str = self._today()
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekday = dt.weekday()  # Monday=0
        start = dt - timedelta(days=weekday)
        end = start + timedelta(days=6)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    async def start_day(self) -> None:
        """Create today's journal entry if it doesn't exist."""
        today = self._today()
        if today not in self._journals:
            self._journals[today] = DailyJournal(date=today)
            logger.info("Started journal for %s", today)

    async def log_event(self, event: JournalEvent) -> None:
        """Log an event to today's journal.

        Auto-creates today's journal if it doesn't exist.
        """
        today = self._today()
        if today not in self._journals:
            await self.start_day()

        journal = self._journals[today]
        journal.events.append(event)

        # Auto-populate commits and files_modified
        if event.category == EventCategory.COMMIT:
            desc = event.description
            if desc not in journal.commits:
                journal.commits.append(desc)

        for f in event.files_affected:
            if f not in journal.files_modified:
                journal.files_modified.append(f)

        # Accumulate hours_active from duration
        journal.hours_active = round(
            journal.hours_active + (event.duration_minutes / 60.0), 2
        )

        logger.debug("Logged event: %s", event.description[:80])

    async def get_today(self) -> DailyJournal:
        """Get today's journal, creating it if needed."""
        today = self._today()
        if today not in self._journals:
            await self.start_day()
        return self._journals[today]

    async def get_journal(self, date: str) -> Optional[DailyJournal]:
        """Get journal for a specific date (YYYY-MM-DD).

        Tries in-memory first, then loads from disk.
        """
        if date in self._journals:
            return self._journals[date]

        journal = await self._load_journal(date)
        if journal is not None:
            self._journals[date] = journal
        return journal

    async def list_journals(self, days: int = 30) -> List[DailyJournal]:
        """List journals for the last N days, newest first."""
        journals: List[DailyJournal] = []
        today = datetime.strptime(self._today(), "%Y-%m-%d")

        for i in range(days):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            journal = await self.get_journal(date)
            if journal is not None:
                journals.append(journal)

        return journals

    async def generate_weekly_review(self) -> WeeklyReview:
        """Generate this week's review by aggregating daily journals."""
        week_start, week_end = self._week_bounds()
        week_key = self._week_key(self._today())

        if week_key in self._reviews:
            return self._reviews[week_key]

        # Gather all journals this week
        week_journals: List[DailyJournal] = []
        start_dt = datetime.strptime(week_start, "%Y-%m-%d")
        end_dt = datetime.strptime(week_end, "%Y-%m-%d")
        current = start_dt

        while current <= end_dt:
            date_str = current.strftime("%Y-%m-%d")
            journal = await self.get_journal(date_str)
            if journal is not None:
                week_journals.append(journal)
            current += timedelta(days=1)

        # Aggregate
        all_accomplishments: List[str] = []
        all_mistakes: List[str] = []
        all_projects: set = set()
        total_hours = 0.0
        all_events: List[JournalEvent] = []
        all_libraries: set = set()
        all_architecture: List[str] = []
        all_lessons: List[str] = []

        for j in week_journals:
            all_accomplishments.extend(j.accomplishments)
            all_mistakes.extend(j.mistakes)
            all_lessons.extend(j.lessons_learned)
            total_hours += j.hours_active
            all_events.extend(j.events)

        # Extract projects from events
        for ev in all_events:
            if ev.project:
                all_projects.add(ev.project)
            # Detect library research events
            if ev.category == EventCategory.RESEARCH:
                desc = ev.description.lower()
                if "library" in desc or "framework" in desc or "package" in desc:
                    # Extract potential library names (words after "using"/"tried"/"learned")
                    for word in ["using", "tried", "learned", "explored"]:
                        idx = desc.find(word)
                        if idx >= 0:
                            snippet = desc[idx + len(word):].strip()
                            first_word = snippet.split()[0] if snippet.split() else ""
                            if first_word:
                                all_libraries.add(first_word.capitalize())

        # Deduplicate
        accomplishments_dedup = list(dict.fromkeys(all_accomplishments))
        mistakes_dedup = list(dict.fromkeys(all_mistakes))
        lessons_dedup = list(dict.fromkeys(all_lessons))

        review = WeeklyReview(
            week_start=week_start,
            week_end=week_end,
            accomplishments=accomplishments_dedup,
            mistakes=mistakes_dedup,
            libraries_learned=sorted(all_libraries),
            projects_progressed=sorted(all_projects),
            hours_spent=round(total_hours, 2),
            skills_improved=[],
            architecture_changes=all_architecture,
            goals_next_week=[],
            summary=self._build_weekly_summary(
                week_journals, total_hours, len(accomplishments_dedup)
            ),
        )

        self._reviews[week_key] = review
        return review

    async def get_outstanding_tasks(self) -> List[str]:
        """Get incomplete tasks from today and recent journals."""
        tasks: List[str] = []

        today = await self.get_today()
        tasks.extend(today.outstanding_tasks)

        # Check yesterday too
        yesterday = (datetime.strptime(self._today(), "%Y-%m-%d") - timedelta(days=1))
        yesterday_journal = await self.get_journal(yesterday.strftime("%Y-%m-%d"))
        if yesterday_journal is not None:
            for task in yesterday_journal.outstanding_tasks:
                if task not in tasks:
                    tasks.append(task)

        return tasks

    async def save(self) -> None:
        """Persist all journals to JSON files."""
        os.makedirs(self._storage_dir, exist_ok=True)

        for date_str, journal in self._journals.items():
            path = os.path.join(self._storage_dir, f"{date_str}.json")
            with open(path, "w") as f:
                json.dump(journal.to_dict(), f, indent=2)

        # Save weekly reviews
        review_dir = os.path.join(self._storage_dir, "reviews")
        os.makedirs(review_dir, exist_ok=True)
        for week_key, review in self._reviews.items():
            path = os.path.join(review_dir, f"{week_key}.json")
            with open(path, "w") as f:
                json.dump(review.to_dict(), f, indent=2)

        logger.info(
            "Saved %d journals and %d reviews",
            len(self._journals), len(self._reviews),
        )

    async def load(self) -> None:
        """Load journals and reviews from disk."""
        if not os.path.isdir(self._storage_dir):
            logger.info("No journal directory at %s", self._storage_dir)
            return

        # Load daily journals
        for fname in os.listdir(self._storage_dir):
            if fname.endswith(".json"):
                date_str = fname[:-5]  # strip .json
                journal = await self._load_journal(date_str)
                if journal is not None:
                    self._journals[date_str] = journal

        # Load weekly reviews
        review_dir = os.path.join(self._storage_dir, "reviews")
        if os.path.isdir(review_dir):
            for fname in os.listdir(review_dir):
                if fname.endswith(".json"):
                    week_key = fname[:-5]
                    review = await self._load_review(week_key)
                    if review is not None:
                        self._reviews[week_key] = review

        logger.info(
            "Loaded %d journals and %d reviews",
            len(self._journals), len(self._reviews),
        )

    async def auto_summarize(self) -> None:
        """Auto-summarize today's journal based on logged events."""
        today_str = self._today()
        journal = self._journals.get(today_str)
        if journal is None:
            return

        if not journal.events:
            return

        # Build summary from events
        categories: Dict[str, int] = defaultdict(int)
        for ev in journal.events:
            categories[ev.category.value] += 1

        parts = []
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            parts.append(f"{count} {cat} event(s)")

        journal.summary = f"Today: {', '.join(parts)}. Active for {journal.hours_active:.1f} hours."

        # Auto-extract accomplishments (commits and features)
        for ev in journal.events:
            if ev.category == EventCategory.COMMIT:
                acc = f"Committed: {ev.description[:100]}"
                if acc not in journal.accomplishments:
                    journal.accomplishments.append(acc)
            elif ev.category == EventCategory.FEATURE:
                acc = f"Feature: {ev.description[:100]}"
                if acc not in journal.accomplishments:
                    journal.accomplishments.append(acc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_journal(self, date_str: str) -> Optional[DailyJournal]:
        """Load a journal from disk."""
        path = os.path.join(self._storage_dir, f"{date_str}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return DailyJournal.from_dict(data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load journal %s: %s", date_str, exc)
            return None

    async def _load_review(self, week_key: str) -> Optional[WeeklyReview]:
        """Load a weekly review from disk."""
        path = os.path.join(self._storage_dir, "reviews", f"{week_key}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return WeeklyReview.from_dict(data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load review %s: %s", week_key, exc)
            return None

    def _build_weekly_summary(
        self, journals: List[DailyJournal], hours: float, accomplishment_count: int
    ) -> str:
        """Build a human-readable weekly summary."""
        day_count = len(journals)
        if day_count == 0:
            return "No activity recorded this week."

        moods = [j.mood for j in journals if j.mood and j.mood != "neutral"]
        mood_str = ""
        if moods:
            from collections import Counter
            most_common = Counter(moods).most_common(1)[0][0]
            mood_str = f" Predominant mood: {most_common}."

        total_events = sum(len(j.events) for j in journals)
        return (
            f"Week of {journals[0].date} to {journals[-1].date}: "
            f"{day_count} active day(s), {total_events} events, "
            f"{hours:.1f} hours, {accomplishment_count} accomplishment(s).{mood_str}"
        )
