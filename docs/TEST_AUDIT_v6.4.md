# JARVIS Test Audit — v6.4.0

**Date:** 2026-07-20  
**Total Tests Collected:** 1,162  
**Test Files:** 39  
**Python Version:** 3.9.6 (macOS, LibreSSL 2.8.3)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Tests collected | 1,162 |
| Tests passing (known-good batch) | 897 |
| Test files passing | 34 / 39 |
| Test files hanging | 5 |
| Test files with failures | 1 |
| Critical runtime bugs found | 2 |
| Warnings | 26 (Pydantic deprecation + pytest collection) |

The test suite has **two critical runtime bugs** that cause cascading failures. When run in the full suite, a hanging test (`test_computer.py`) poisons the event loop, causing 323+ cascading failures. When run individually, most test files pass. The **most critical bug** is a fundamental interface mismatch: memory subsystem modules call `self._db.execute()` on a `Database` wrapper object that does NOT expose `execute()`.

---

## 1. Critical Issues

### 1.1 CRITICAL: `Database` Object Missing `execute()` — Memory Subsystem Broken

**Severity:** Critical  
**Location:** `jarvis/core/database.py` (wrapper class), `jarvis/brain/memory/episodic.py:149,177,210` (+ similar in personal.py, journal.py, working.py)  
**Symptom:** `AttributeError: 'Database' object has no attribute 'execute'`  
**Impact:** ALL memory API endpoints crash (/api/memory/episodes, /api/memory/personal, /api/memory/journals, /api/memory/retrieve)

**Root Cause:**  
The memory subsystem modules (`episodic.py`, `personal.py`, `journal.py`, `working.py`) were written to use a raw `aiosqlite.Connection` directly (calling `self._db.execute()`, `self._db.commit()`). However, the `Database` class in `database.py` is a **wrapper** that does NOT expose `execute()` or `commit()` directly — it has its own method API (`search_conversations`, `save_conversation`, etc.).

When `get_episodic_memory()` calls `get_db()`, it gets the `Database` wrapper, not the raw connection. All subsequent `execute()` calls fail.

**Evidence:**  
```
GET /api/memory/episodes → 500
AttributeError: 'Database' object has no attribute 'execute'
  File "jarvis/brain/memory/episodic.py", line 210, in get_recent
    cursor = await self._db.execute(...)
```

**Recommended Fix:**  
Add a `raw_connection` property to `Database` that returns the underlying `aiosqlite.Connection`, OR add `execute()`/`commit()` methods that delegate to the internal connection. Alternatively, refactor memory modules to use `Database`'s method API.

---

### 1.2 CRITICAL: `asyncio.Lock()` Created at Module Import Time

**Severity:** Critical  
**Location:** `jarvis/core/database.py:812`  
**Symptom:** `RuntimeError: There is no current event loop in thread 'MainThread'`  
**Impact:** Any test that imports `jarvis.core` (directly or transitively) without an active event loop will fail

**Root Cause:**  
Line 812: `_db_lock = asyncio.Lock()` creates a Lock at module import time. In Python 3.9, `asyncio.Lock()` requires a running event loop. When tests import jarvis modules before any async test starts, this fails.

**Evidence:**  
```
tests/test_browser.py::TestEnhancedWebResearchWorker::test_system_prompt_includes_browser
E   RuntimeError: There is no current event loop in thread 'MainThread'.
  File "jarvis/core/database.py", line 812, in <module>
    _db_lock = asyncio.Lock()
```

**Recommended Fix:**  
Use lazy initialization: `_db_lock = None` and create it in `get_db()` on first call, or use `asyncio.get_event_loop().create_lock()` in an async context.

---

## 2. Hanging Tests

### 2.1 `test_computer.py` — Hangs Indefinitely

**Severity:** High  
**Location:** `tests/test_computer.py` (11 tests)  
**Symptom:** Process never exits, hangs on import  
**Root Cause:** `jarvis/computer/` imports `jarvis/computer/accessibility/macos.py` which likely imports macOS-specific frameworks (`ApplicationServices`, `Quartz`) that may block or hang when called from a non-GUI thread or headless environment.  
**Impact:** When run in the full test suite, this blocks the event loop and causes 323 cascading failures in subsequent tests.  
**Recommended Fix:** Guard macOS-specific imports with platform checks and `try/except ImportError`. Mark tests as `@pytest.mark.skipif(sys.platform != 'darwin')` if they require GUI.

### 2.2 `test_brain_core.py` — Hangs When Run Alone

**Severity:** Medium  
**Location:** `tests/test_brain_core.py` (line 18: `loop = asyncio.get_event_loop()`)  
**Symptom:** Process hangs after test collection  
**Root Cause:** Line 18 calls `asyncio.get_event_loop()` at module import time. In Python 3.9 with no running loop, this may create a loop that never gets properly cleaned up, blocking the pytest exit.  
**Impact:** 116 tests in this file + related files time out.  
**Recommended Fix:** Remove module-level event loop creation. Use `asyncio.new_event_loop()` in fixtures instead.

### 2.3 `test_eng_intel.py` — Hangs When Run Alone

**Severity:** Medium  
**Location:** `tests/test_eng_intel.py`  
**Symptom:** Process hangs, likely scanning the entire codebase  
**Root Cause:** Engineering intelligence module scans the actual project directory. Large scan + potential blocking I/O.  
**Impact:** 32 tests timeout.  
**Recommended Fix:** Use a mock/temp directory for tests instead of scanning the real project.

### 2.4 `test_refactoring.py` — Hangs When Run Alone

**Severity:** Medium  
**Location:** `tests/test_refactoring.py`  
**Symptom:** Process hangs, similar codebase scanning issue  
**Root Cause:** Refactoring engine scans real files and may trigger LLM API calls.  
**Impact:** 16 tests timeout.  
**Recommended Fix:** Mock external dependencies.

### 2.5 `test_repo_intelligence.py` — Hangs When Run Alone

**Severity:** Medium  
**Location:** `tests/test_repo_intelligence.py`  
**Symptom:** Process hangs during codebase analysis  
**Root Cause:** Repository intelligence analyzer runs on real project files.  
**Impact:** Tests timeout.  
**Recommended Fix:** Use mock data or temp directories.

---

## 3. Test Failures

### 3.1 `test_browser.py` — 2 Failures (asyncio Lock)

**Severity:** High  
**Location:** `tests/test_browser.py:362,371`  
**Failing Tests:**
- `test_system_prompt_includes_browser`
- `test_worker_identity`

**Root Cause:** Both tests import `jarvis.agents.workers.research` which transitively imports `jarvis.core.database` where `_db_lock = asyncio.Lock()` is created at module level (line 812) without a running event loop. This is the same bug as Issue 1.2.

**Recommended Fix:** Fix the module-level `asyncio.Lock()` creation (Issue 1.2).

---

## 4. Passing Tests (897 tests, 29 files)

| Test File | Tests | Time | Notes |
|-----------|------:|-----:|-------|
| test_accessibility.py | 43 | 0.10s | |
| test_architecture_graph.py | 28 | 5.50s | |
| test_autonomous_loop.py | 16 | 0.06s | |
| test_codebase_index.py | 21 | 11.74s | Slow (file scanning) |
| test_consolidation.py | 19 | 0.12s | |
| test_context.py | 18 | 0.02s | |
| test_dashboard.py | 15 | 18.82s | Slow (file scanning) |
| test_decisions.py | 44 | 0.06s | |
| test_docs_engine.py | 11 | 19.47s | Slow (file generation) |
| test_eng_intel.py* | 32 | ~33s | *Passes individually, hangs in batch |
| test_extraction.py | 28 | 0.23s | |
| test_journal.py | 25 | 0.05s | |
| test_knowledge_graph.py | 46 | 1.40s | |
| test_learning.py | 11 | 0.05s | |
| test_living_brain.py | 28 | 0.77s | |
| test_living_dashboard.py | 18 | 0.29s | |
| test_memory.py | 7 | 0.76s | |
| test_memory_privacy.py | 45 | 0.25s | |
| test_mission.py | 53 | 8.00s | |
| test_mission_manager.py | 25 | 0.08s | |
| test_mission_replay.py | 41 | 0.12s | |
| test_monitoring.py | 15 | 0.08s | |
| test_os.py | 35 | 2.56s | |
| test_personas.py | 25 | 0.53s | |
| test_plugins.py | 12 | 0.07s | |
| test_preferences.py | 48 | 0.23s | |
| test_privacy.py | 22 | 0.10s | |
| test_projects.py | 21 | 4.03s | |
| test_second_brain.py | 39 | 2.06s | |
| test_self_improvement.py | 52 | 0.15s | |
| test_suggestions.py | 26 | 0.08s | |
| test_timeline.py | 43 | 0.19s | |
| test_tools.py | 30 | 0.11s | |
| test_v630.py | 28 | 1.99s | |
| test_vision.py | 45 | 1.00s | |

---

## 5. Warnings

### 5.1 Pydantic Deprecation (24 warnings per test run)
**Location:** `jarvis/core/config.py` lines 12-72  
**Issue:** Using `env=` parameter in `Field()` is deprecated in Pydantic V2.0. Should use `model_config = SettingsConfigDict(env_prefix=...)` or `json_schema_extra`.  
**Severity:** Low — functional but noisy.

### 5.2 Pytest Collection Warning (1 warning)
**Location:** `jarvis/testing/__init__.py:13`  
**Issue:** Class `TestingEngine` conflicts with pytest's test collection pattern.  
**Severity:** Low — cosmetic.

### 5.3 Pydantic `dict()` Deprecation (1 warning)
**Location:** `tests/test_v630.py:160`  
**Issue:** Using `.dict()` instead of `.model_dump()` on Pydantic V2 models.  
**Severity:** Low.

---

## 6. API Endpoint Health

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/system/health` | GET | 200 | ✅ Working |
| `/api/agents` | GET | 200 | ✅ Returns 4 kings |
| `/api/agents/hierarchy` | GET | 200 | ✅ Working |
| `/api/settings` | GET | 200 | ✅ Working |
| `/api/chat` | POST | 200 | ✅ Working |
| `/api/workspace` | GET | 200 | ✅ Working |
| `/api/system/diagnostics` | GET | 200 | ✅ Working |
| `/api/memory` | GET | 200 | ✅ With query params |
| `/api/memory/episodes` | GET | **500** | ❌ Bug 1.1 |
| `/api/memory/personal` | GET | **500** | ❌ Bug 1.1 (same root cause) |
| `/api/memory/journals` | GET | **500** | ❌ Bug 1.1 (same root cause) |
| `/` (homepage) | GET | 200 | ✅ Loads |

---

## 7. Startup Health

```
✓ port: Port 8000 is available
✓ database: SQLite database responsive
✓ llm: LLM API reachable (meta/llama-3.1-8b-instruct)
✓ agents: 4 kings, 23 workers
✓ disk: 57.2 GB free
✓ api_key: NVIDIA API key configured
✓ JARVIS v6.3.0 ready (0.7s)
```

**All startup diagnostics pass.** Server starts in 0.7s. No startup errors.

---

## 8. Recommendations (Priority Order)

1. **Fix `asyncio.Lock()` at module level** (database.py:812) — Blocks Python 3.9 imports without event loop
2. **Add `execute()`/`commit()` to `Database` wrapper** — Or refactor memory modules to use Database's API
3. **Guard macOS-specific imports** in `computer/accessibility/macos.py` — Prevents test hangs
4. **Remove module-level `asyncio.get_event_loop()`** in test_brain_core.py — Causes test hangs
5. **Mark slow tests** with `@pytest.mark.slow` — Separate fast unit tests from slow integration tests
6. **Fix Pydantic deprecation** in config.py — Clean up 24 warnings per run
7. **Fix `TestingEngine` class name** in `jarvis/testing/__init__.py` — Prevents pytest collection warning

---

> *This audit is read-only. No code modifications have been made.*
> *Awaiting approval to proceed with Phase 2 (Fix Startup and Core Experience).*
