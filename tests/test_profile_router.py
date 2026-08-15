"""Tests for the Know-Me profile API router."""

from types import SimpleNamespace

from jarvis.brain.memory.personal import PersonalMemoryManager
from jarvis.core.database import Database
from jarvis.web.routers import profile as profile_router


async def _make_manager(tmp_path):
    db = Database()
    db._config = SimpleNamespace(db_path=str(tmp_path / "profile_test.db"))
    await db.connect()
    return db, PersonalMemoryManager(db)


async def test_onboard_persists_memories(tmp_path, monkeypatch):
    db, pm = await _make_manager(tmp_path)
    monkeypatch.setattr(profile_router, "get_personal_memory", lambda: pm)
    try:
        req = profile_router.OnboardRequest(
            name="Brian",
            timezone="Asia/Taipei",
            goal="A poker assistant",
            notes="I prefer short answers",
        )
        result = await profile_router.onboard(req)
        assert result["ok"] is True
        assert result["memories_saved"] == 4

        profile = await profile_router.get_profile()
        assert profile["bio"]["my_name"]["value"] == "My name is Brian"
        assert profile["preference"]["timezone"]["value"] == "My timezone is Asia/Taipei"
        assert profile["goal"]["current_goal"]["value"] == "Currently building: A poker assistant"
    finally:
        await db.close()


async def test_onboard_empty_saves_nothing(tmp_path, monkeypatch):
    db, pm = await _make_manager(tmp_path)
    monkeypatch.setattr(profile_router, "get_personal_memory", lambda: pm)
    try:
        result = await profile_router.onboard(profile_router.OnboardRequest())
        assert result["ok"] is True
        assert result["memories_saved"] == 0
    finally:
        await db.close()


async def test_completeness_scoring(tmp_path, monkeypatch):
    db, pm = await _make_manager(tmp_path)
    monkeypatch.setattr(profile_router, "get_personal_memory", lambda: pm)
    try:
        await pm.remember("bio", "my_name", "My name is Brian", confidence=0.95)
        await pm.remember("goal", "current_goal", "Build", confidence=0.9)

        result = await profile_router.get_completeness()
        assert result["score"] == 45  # bio 25 + goal 20
        assert result["percent"] == 45
        assert result["total_memories"] == 2
        assert result["breakdown"]["bio"]["met"] is True
        assert result["breakdown"]["project"]["met"] is False
    finally:
        await db.close()


async def test_completeness_full_profile(tmp_path, monkeypatch):
    db, pm = await _make_manager(tmp_path)
    monkeypatch.setattr(profile_router, "get_personal_memory", lambda: pm)
    try:
        categories = (
            "bio", "preference", "goal", "project", "tool",
            "style", "workflow", "rule", "context",
        )
        for category in categories:
            await pm.remember(category, f"key_{category}", f"value {category}", confidence=0.9)

        result = await profile_router.get_completeness()
        assert result["score"] == 100
    finally:
        await db.close()


async def test_learn_stores_memory(tmp_path, monkeypatch):
    db, pm = await _make_manager(tmp_path)
    monkeypatch.setattr(profile_router, "get_personal_memory", lambda: pm)
    try:
        req = profile_router.LearnRequest(
            content="I use VS Code daily", category="tool", source="ui"
        )
        result = await profile_router.learn(req)
        assert result["ok"] is True
        assert result["category"] == "tool"

        memory = await pm.get("tool", "i_use_vs_code_daily")
        assert memory is not None
        assert memory.value == "I use VS Code daily"
    finally:
        await db.close()


async def test_slugify():
    assert profile_router._slugify("I use VS Code daily") == "i_use_vs_code_daily"
    assert profile_router._slugify("Hello, world!") == "hello_world"
    assert profile_router._slugify("!!!") == "note"
    assert len(profile_router._slugify("x" * 200)) <= 80
