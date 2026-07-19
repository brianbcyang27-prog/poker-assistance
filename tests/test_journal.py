import sys
import os
import asyncio
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime, timedelta
from jarvis.journal.models import DailyJournal, EventCategory, JournalEvent, WeeklyReview
from jarvis.journal import JournalEngine


# ---------------------------------------------------------------------------
# JournalModels
# ---------------------------------------------------------------------------


class TestJournalModels:
    def test_journal_event_creation(self):
        e = JournalEvent(
            timestamp=datetime(2025, 6, 15, 10, 30),
            category=EventCategory.CODE,
            description="Implemented login module",
            duration_minutes=45,
            files_affected=["auth.py", "login.py"],
            project="jarvis",
        )
        assert e.category == EventCategory.CODE
        assert e.duration_minutes == 45
        assert len(e.files_affected) == 2
        assert e.project == "jarvis"

    def test_journal_event_to_dict(self):
        e = JournalEvent(
            timestamp=datetime(2025, 1, 1, 8, 0),
            category=EventCategory.COMMIT,
            description="fix: resolve crash on startup",
            duration_minutes=10,
        )
        d = e.to_dict()
        assert d["category"] == "commit"
        assert d["duration_minutes"] == 10
        assert d["timestamp"] == "2025-01-01T08:00:00"

    def test_journal_event_from_dict(self):
        d = {
            "timestamp": "2025-07-20T14:00:00",
            "category": "bug",
            "description": "Fix null pointer",
            "duration_minutes": 30,
            "files_affected": ["fix.py"],
            "project": "jarvis",
        }
        e = JournalEvent.from_dict(d)
        assert e.category == EventCategory.BUG
        assert e.files_affected == ["fix.py"]

    def test_event_category_values(self):
        assert EventCategory.CODE.value == "code"
        assert EventCategory.COMMIT.value == "commit"
        assert EventCategory.BUG.value == "bug"
        assert EventCategory.FEATURE.value == "feature"
        assert EventCategory.RESEARCH.value == "research"

    def test_daily_journal_defaults(self):
        j = DailyJournal(date="2025-06-15")
        assert j.date == "2025-06-15"
        assert j.events == []
        assert j.summary == ""
        assert j.hours_active == 0.0
        assert j.mood == "neutral"

    def test_daily_journal_to_dict(self):
        j = DailyJournal(date="2025-06-15", summary="Good day", hours_active=6.5)
        d = j.to_dict()
        assert d["date"] == "2025-06-15"
        assert d["hours_active"] == 6.5
        assert d["mood"] == "neutral"

    def test_daily_journal_from_dict_roundtrip(self):
        j = DailyJournal(
            date="2025-03-01",
            summary="Productive",
            accomplishments=["Shipped feature X"],
            hours_active=8.0,
            mood="productive",
        )
        d = j.to_dict()
        j2 = DailyJournal.from_dict(d)
        assert j2.date == j.date
        assert j2.summary == j.summary
        assert j2.mood == "productive"
        assert j2.accomplishments == ["Shipped feature X"]

    def test_weekly_review_defaults(self):
        r = WeeklyReview(week_start="2025-06-09", week_end="2025-06-15")
        assert r.week_start == "2025-06-09"
        assert r.week_end == "2025-06-15"
        assert r.accomplishments == []
        assert r.hours_spent == 0.0

    def test_weekly_review_to_dict(self):
        r = WeeklyReview(
            week_start="2025-06-09", week_end="2025-06-15",
            accomplishments=["Built dashboard"], hours_spent=40.0,
        )
        d = r.to_dict()
        assert d["hours_spent"] == 40.0
        assert "Built dashboard" in d["accomplishments"]

    def test_weekly_review_from_dict_roundtrip(self):
        r = WeeklyReview(
            week_start="2025-06-09", week_end="2025-06-15",
            accomplishments=["Deploy v1.0"], hours_spent=35.5,
            libraries_learned=["fastapi"],
        )
        d = r.to_dict()
        r2 = WeeklyReview.from_dict(d)
        assert r2.hours_spent == 35.5
        assert "fastapi" in r2.libraries_learned


# ---------------------------------------------------------------------------
# JournalEngine
# ---------------------------------------------------------------------------


class TestJournalEngine:
    @pytest.fixture
    def engine(self, tmp_path):
        eng = JournalEngine(storage_dir=str(tmp_path / "journal"))
        return eng

    def test_init(self, engine):
        assert engine._journals == {}
        assert engine._reviews == {}

    def test_start_day(self, engine):
        asyncio.get_event_loop().run_until_complete(engine.start_day())
        today = engine._today()
        assert today in engine._journals
        assert isinstance(engine._journals[today], DailyJournal)

    def test_start_day_idempotent(self, engine):
        asyncio.get_event_loop().run_until_complete(engine.start_day())
        asyncio.get_event_loop().run_until_complete(engine.start_day())
        today = engine._today()
        assert len([k for k in engine._journals if k == today]) == 1

    def test_log_event(self, engine):
        event = JournalEvent(
            timestamp=datetime.now(),
            category=EventCategory.CODE,
            description="Implemented auth module",
            duration_minutes=60,
            files_affected=["auth.py"],
        )
        asyncio.get_event_loop().run_until_complete(engine.log_event(event))
        today = asyncio.get_event_loop().run_until_complete(engine.get_today())
        assert len(today.events) == 1
        assert today.events[0].description == "Implemented auth module"
        assert today.hours_active == 1.0

    def test_log_event_commit(self, engine):
        event = JournalEvent(
            timestamp=datetime.now(),
            category=EventCategory.COMMIT,
            description="feat: add login page",
            duration_minutes=15,
        )
        asyncio.get_event_loop().run_until_complete(engine.log_event(event))
        today = asyncio.get_event_loop().run_until_complete(engine.get_today())
        assert "feat: add login page" in today.commits

    def test_log_event_files_modified(self, engine):
        event = JournalEvent(
            timestamp=datetime.now(),
            category=EventCategory.CODE,
            description="Refactor utils",
            duration_minutes=30,
            files_affected=["utils.py", "helpers.py"],
        )
        asyncio.get_event_loop().run_until_complete(engine.log_event(event))
        today = asyncio.get_event_loop().run_until_complete(engine.get_today())
        assert "utils.py" in today.files_modified
        assert "helpers.py" in today.files_modified

    def test_get_today_creates_if_needed(self, engine):
        today = asyncio.get_event_loop().run_until_complete(engine.get_today())
        assert isinstance(today, DailyJournal)
        assert today.date == engine._today()

    def test_get_journal_specific_date(self, engine):
        engine.set_today("2025-06-15")
        event = JournalEvent(
            timestamp=datetime(2025, 6, 15, 10, 0),
            category=EventCategory.RESEARCH,
            description="Explored FastAPI",
        )
        asyncio.get_event_loop().run_until_complete(engine.log_event(event))
        journal = asyncio.get_event_loop().run_until_complete(engine.get_journal("2025-06-15"))
        assert journal is not None
        assert len(journal.events) == 1

    def test_get_journal_nonexistent(self, engine):
        journal = asyncio.get_event_loop().run_until_complete(
            engine.get_journal("2000-01-01")
        )
        assert journal is None

    def test_list_journals(self, engine):
        engine.set_today("2025-06-16")
        engine._journals["2025-06-15"] = DailyJournal(date="2025-06-15")
        engine._journals["2025-06-14"] = DailyJournal(date="2025-06-14")
        journals = asyncio.get_event_loop().run_until_complete(engine.list_journals(days=7))
        assert len(journals) >= 2

    def test_generate_weekly_review(self, engine):
        engine.set_today("2025-06-15")
        event1 = JournalEvent(
            timestamp=datetime(2025, 6, 15, 10, 0),
            category=EventCategory.FEATURE,
            description="Built dashboard",
            duration_minutes=120,
        )
        asyncio.get_event_loop().run_until_complete(engine.log_event(event1))
        asyncio.get_event_loop().run_until_complete(engine.get_today())
        review = asyncio.get_event_loop().run_until_complete(engine.generate_weekly_review())
        assert isinstance(review, WeeklyReview)
        assert review.week_start <= "2025-06-15"
        assert review.week_end >= "2025-06-15"
        assert review.hours_spent > 0

    def test_get_outstanding_tasks(self, engine):
        engine.set_today("2025-06-15")
        asyncio.get_event_loop().run_until_complete(engine.start_day())
        today = asyncio.get_event_loop().run_until_complete(engine.get_today())
        today.outstanding_tasks = ["Finish auth module", "Write tests"]
        tasks = asyncio.get_event_loop().run_until_complete(engine.get_outstanding_tasks())
        assert "Finish auth module" in tasks
        assert "Write tests" in tasks

    def test_save_and_load(self, tmp_path):
        storage = str(tmp_path / "journal_save")
        e1 = JournalEngine(storage_dir=storage)
        e1.set_today("2025-06-15")
        event = JournalEvent(
            timestamp=datetime(2025, 6, 15, 10, 0),
            category=EventCategory.CODE,
            description="Testing persistence",
            duration_minutes=30,
        )
        asyncio.get_event_loop().run_until_complete(e1.log_event(event))
        asyncio.get_event_loop().run_until_complete(e1.save())

        e2 = JournalEngine(storage_dir=storage)
        asyncio.get_event_loop().run_until_complete(e2.load())
        journal = asyncio.get_event_loop().run_until_complete(e2.get_journal("2025-06-15"))
        assert journal is not None
        assert len(journal.events) == 1
        assert journal.events[0].description == "Testing persistence"

    def test_set_today_override(self, engine):
        engine.set_today("2099-12-31")
        assert engine._today() == "2099-12-31"

    def test_multiple_events_accumulate_hours(self, engine):
        for i in range(3):
            event = JournalEvent(
                timestamp=datetime.now(),
                category=EventCategory.CODE,
                description=f"Task {i}",
                duration_minutes=30,
            )
            asyncio.get_event_loop().run_until_complete(engine.log_event(event))
        today = asyncio.get_event_loop().run_until_complete(engine.get_today())
        assert abs(today.hours_active - 1.5) < 0.01
