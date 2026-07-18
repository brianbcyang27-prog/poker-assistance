"""Tests for the human-like memory system (v4.1.0)."""

import asyncio
import time
import os
import sys
import aiosqlite

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

TEST_DB = ":memory:"


async def _make_db():
    db = await aiosqlite.connect(TEST_DB)
    db.row_factory = aiosqlite.Row
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS working_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot TEXT NOT NULL UNIQUE,
            content TEXT NOT NULL,
            priority INTEGER DEFAULT 5,
            importance REAL DEFAULT 0.0,
            created_at REAL DEFAULT 0,
            expires_at REAL DEFAULT 0,
            access_count INTEGER DEFAULT 0,
            last_accessed REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            episode_type TEXT NOT NULL DEFAULT 'conversation',
            project TEXT DEFAULT '',
            participants TEXT DEFAULT '[]',
            goals TEXT DEFAULT '[]',
            decisions TEXT DEFAULT '[]',
            outcome TEXT DEFAULT '',
            importance_score REAL DEFAULT 0.0,
            tags TEXT DEFAULT '[]',
            source_conversation_ids TEXT DEFAULT '[]',
            source_task_ids TEXT DEFAULT '[]',
            created_at REAL DEFAULT 0,
            consolidated_at REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS personal_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            confidence REAL DEFAULT 0.8,
            source TEXT DEFAULT '',
            remember_mode TEXT DEFAULT 'always',
            created_at REAL DEFAULT 0,
            updated_at REAL DEFAULT 0,
            UNIQUE(category, key)
        );
        CREATE TABLE IF NOT EXISTS memory_access_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_type TEXT NOT NULL,
            memory_id TEXT NOT NULL,
            query TEXT DEFAULT '',
            relevance REAL DEFAULT 0.0,
            accessed_at REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT,
            user_request TEXT,
            summary TEXT,
            created_at REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            path TEXT NOT NULL,
            description TEXT DEFAULT '',
            language TEXT DEFAULT 'unknown',
            context TEXT DEFAULT '',
            created_at REAL DEFAULT 0,
            updated_at REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            decision TEXT NOT NULL,
            reason TEXT DEFAULT '',
            created_at REAL DEFAULT 0
        );
    """)
    await db.commit()
    return db


# ── Importance Scorer ────────────────────────────────────────

async def test_importance_scorer():
    from jarvis.brain.memory.importance import ImportanceScorer

    scorer = ImportanceScorer()

    # Explicit signal: "remember" = 100
    score = scorer.score("Please remember that I prefer Python over JavaScript")
    assert score >= 70, f"Expected >= 70 for 'remember' signal, got {score}"

    # Explicit signal: "i prefer" = 60
    score = scorer.score("I prefer dark mode for all UIs")
    assert score >= 50, f"Expected >= 50 for 'i prefer' signal, got {score}"

    # Topic signal: "architecture"
    score = scorer.score("The architecture uses microservices with event bus")
    assert score >= 40, f"Expected >= 40 for architecture topic, got {score}"

    # Normal low-importance content
    score = scorer.score("Can you help me write a function?")
    assert 0 <= score <= 50, f"Expected 0-50 for normal content, got {score}"

    # Signals extraction returns dict
    signals = scorer.extract_signals("Remember to never use var in JavaScript")
    assert isinstance(signals, dict), f"Expected dict, got {type(signals)}"
    assert len(signals) > 0

    print("  ✓ ImportanceScorer")
    return True


# ── Working Memory ───────────────────────────────────────────

async def test_working_memory():
    from jarvis.brain.memory.working import WorkingMemoryManager

    db = await _make_db()
    wm = WorkingMemoryManager(db)

    # set() and get()
    await wm.set("mission", "Building a robot arm", priority=8)
    content = await wm.get("mission")
    assert content is not None
    assert "robot arm" in content, f"Expected 'robot arm' in content, got {content}"

    # get_all()
    all_entries = await wm.get_all()
    assert "mission" in all_entries

    # get_context()
    context = await wm.get_context()
    assert "robot arm" in context

    # clear()
    await wm.clear("mission")
    content = await wm.get("mission")
    assert content is None or content == ""

    await db.close()
    print("  ✓ WorkingMemoryManager")
    return True


# ── Episodic Memory ──────────────────────────────────────────

async def test_episodic_memory():
    from jarvis.brain.memory.episodic import EpisodicMemoryManager

    db = await _make_db()
    em = EpisodicMemoryManager(db)

    # create_episode()
    result = await em.create_episode(
        title="Fixed memory leak in database pool",
        summary="Identified and patched a connection leak in aiosqlite pool manager",
        episode_type="bug",
        participants=["Brian", "JARVIS"],
        decisions=["Switched to context manager pattern"],
        importance_score=70,
        tags=["database", "performance"],
    )
    assert result is not None
    assert "id" in result

    # get()
    ep = await em.get(result["id"])
    assert ep is not None
    assert "memory leak" in ep.title
    assert len(ep.decisions) > 0

    # search()
    results = await em.search("database pool", limit=5)
    assert len(results) > 0

    # get_recent()
    episodes = await em.get_recent(limit=10)
    assert len(episodes) >= 1

    # get_stats()
    stats = await em.get_stats()
    assert stats["total"] >= 1

    await db.close()
    print("  ✓ EpisodicMemoryManager")
    return True


# ── Personal Memory ──────────────────────────────────────────

async def test_personal_memory():
    from jarvis.brain.memory.personal import PersonalMemoryManager

    db = await _make_db()
    pm = PersonalMemoryManager(db)

    # remember()
    result = await pm.remember(
        "preference", "language", "Python is preferred over JavaScript",
        confidence=0.9,
    )
    assert isinstance(result, dict)
    assert "id" in result

    # get()
    mem = await pm.get("preference", "language")
    assert mem is not None
    assert "Python" in mem.value

    # Update (same category+key)
    result2 = await pm.remember(
        "preference", "language", "Python and Rust are preferred",
        confidence=0.95,
    )
    assert result2["id"] == result["id"]  # updated same row

    # search()
    results = await pm.search("Python", limit=5)
    assert len(results) > 0

    # get_profile()
    profile = await pm.get_profile()
    assert isinstance(profile, dict)

    # forget()
    success = await pm.forget(category="preference", key="language")
    assert success
    mem = await pm.get("preference", "language")
    assert mem is None

    await db.close()
    print("  ✓ PersonalMemoryManager")
    return True


# ── Retrieval Engine ─────────────────────────────────────────

async def test_retrieval_engine():
    from jarvis.brain.memory.retrieval import MemoryRetrievalEngine, IntentDetector

    # Intent detection
    detector = IntentDetector()
    intents = detector.detect("What did we decide about the database?")
    assert "decision" in intents, f"Expected 'decision' in {intents}"

    intents = detector.detect("Continue the robot project")
    assert "continue" in intents, f"Expected 'continue' in {intents}"

    intents = detector.detect("I prefer dark mode")
    assert "preference" in intents, f"Expected 'preference' in {intents}"

    intents = detector.detect("How does the memory system work?")
    assert "learn" in intents, f"Expected 'learn' in {intents}"

    # Memory type selection
    types = detector.get_memory_types(["decision"])
    assert "episodic" in types

    # Retrieval with populated data
    db = await _make_db()
    engine = MemoryRetrievalEngine(db)

    # Seed conversations
    now = time.time()
    await db.execute(
        "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        ("test", "user", "I prefer Python for backend development", now),
    )
    await db.execute(
        "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        ("test", "assistant", "Noted, Python is great for backend!", now),
    )
    await db.commit()

    results = await engine.retrieve("What language do I prefer?", max_results=5)
    assert isinstance(results, list)

    context = engine.assemble_context(results)
    assert isinstance(context, str)

    stats = engine.get_stats()
    assert stats["retrievals"] >= 1

    await db.close()
    print("  ✓ MemoryRetrievalEngine")
    return True


# ── Daily Journal ────────────────────────────────────────────

async def test_journal():
    from jarvis.brain.memory.journal import DailyJournal

    db = await _make_db()
    j = DailyJournal(db)
    await j._ensure_table()

    await j.log_conversation(
        "session1",
        "Fixed the memory leak in the connection pool",
        decisions=["Switch to context manager pattern"],
        tags=["database", "performance"],
    )

    entry = await j.get_today()
    assert entry is not None
    assert len(entry.highlights) > 0
    assert len(entry.decisions) > 0

    await j.add_highlight("Completed v4.1.0 memory system")
    entry = await j.get_today()
    assert len(entry.highlights) >= 2

    await j.set_mood("productive")
    entry = await j.get_today()
    assert entry.mood == "productive"

    await j.set_tomorrow(["Run tests", "Deploy to staging"])
    entry = await j.get_today()
    assert len(entry.tomorrow) == 2

    entries = await j.get_recent(days=1)
    assert len(entries) >= 1

    summary = await j.get_summary_for_context()
    assert len(summary) > 0

    await db.close()
    print("  ✓ DailyJournal")
    return True


# ── Memory API Router ────────────────────────────────────────

async def test_memory_api():
    from jarvis.web.routers.memory import (
        router, WorkingMemoryUpdate, EpisodeCreate,
        PersonalMemoryCreate, JournalUpdate,
        RetrievalQuery, ConsolidateRequest,
    )

    assert router.prefix == "/api/memory"

    w = WorkingMemoryUpdate(slot="mission", content="Test")
    assert w.importance == 0.5

    e = EpisodeCreate(title="Test episode")
    assert e.episode_type == "conversation"

    p = PersonalMemoryCreate(category="preference", key="lang", value="Python")
    assert p.confidence == 0.6

    r = RetrievalQuery(query="test query")
    assert r.max_results == 10

    c = ConsolidateRequest()
    assert c.force is False

    print("  ✓ Memory API router (models valid)")
    return True


# ── Run Tests ────────────────────────────────────────────────

async def main():
    print("\n🧪 Memory System Tests (v4.1.0)\n")
    results = []

    tests = [
        ("ImportanceScorer", test_importance_scorer),
        ("WorkingMemoryManager", test_working_memory),
        ("EpisodicMemoryManager", test_episodic_memory),
        ("PersonalMemoryManager", test_personal_memory),
        ("MemoryRetrievalEngine", test_retrieval_engine),
        ("DailyJournal", test_journal),
        ("Memory API Models", test_memory_api),
    ]

    for name, test_fn in tests:
        try:
            ok = await test_fn()
            results.append((name, ok))
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    print(f"\n{'✓' if failed == 0 else '✗'} {passed}/{len(results)} passed")
    if failed:
        print(f"  Failed: {[name for name, ok in results if not ok]}")
    return failed == 0


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
