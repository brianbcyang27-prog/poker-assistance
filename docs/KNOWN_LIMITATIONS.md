# JARVIS Known Limitations

**Last updated:** 2025-07-18  
**Version:** 6.2.0

---

## Critical — Affects Reliability

### 1. Synchronous LLM Chat in Async Context

**File:** `jarvis/brain/llm.py` — `chat()` method  
**Issue:** The LLM client uses synchronous `httpx.Client` and `time.sleep()` for retry logic. When called from async code, this blocks the entire event loop during retries (potentially seconds per retry).  
**Impact:** Under load, all concurrent requests stall while one LLM call retries.  
**Fix:** Migrate to `httpx.AsyncClient` with `asyncio.sleep()` for retries.  
**Priority:** High

### 2. Synchronous SQLite in Async Methods

**File:** `jarvis/brain/memory/graph.py` and related modules  
**Issue:** Knowledge graph operations use the synchronous `sqlite3` module directly in `async def` methods. SQLite calls are blocking I/O that starve the event loop.  
**Impact:** Under concurrent load, knowledge graph queries block all other async operations.  
**Fix:** Migrate to `aiosqlite` for non-blocking database access.  
**Priority:** High

### 3. 43 Silent `except Exception: pass` Handlers

**Files:** Primarily in `jarvis/brain/` modules  
**Issue:** 43 exception handlers silently swallow errors with no logging or recovery. These are invisible failure modes in production.  
**Impact:** Bugs in these code paths are undetectable without adding logging to every handler.  
**Fix:** Add `logger.exception()` to each handler. Categorize as recoverable vs. fatal.  
**Priority:** High — should be addressed incrementally across 2-3 releases.

---

## Medium — Affects Maintainability

### 4. `system.py` Mega-Router

**File:** `jarvis/web/routers/system.py`  
**Issue:** Single router file contains 83+ endpoints covering authentication, configuration, system info, memory management, and more.  
**Impact:** Difficult to navigate, review, or refactor. High merge conflict risk.  
**Fix:** Decompose into domain-specific routers: `auth.py`, `config.py`, `system_info.py`, `memory_api.py`, etc.  
**Priority:** Medium

### 5. Duplicate WebSocket Connections

**Files:** Multiple frontend components  
**Issue:** Three separate JavaScript components each establish their own WebSocket connection to `/ws/agents`.  
**Impact:** Redundant connections waste server resources and create synchronization issues (each connection receives the same events independently).  
**Fix:** Consolidate into a single WebSocket connection with message multiplexing.  
**Priority:** Medium

### 6. No Frontend Test Infrastructure

**Issue:** All 223 tests are Python-only. The JavaScript changes in v6.2.0 (WebSocket fixes, listener leak fixes, destroy methods) have zero test coverage.  
**Impact:** JS regressions are undetectable by the test suite.  
**Fix:** Add a JS test framework (e.g., Vitest or Jest) and test critical components.  
**Priority:** Medium

---

## Low — Code Quality

### 7. Dead Code Remnants

**Status in v6.2.0:** Removed `command_center.py`, `orchestration/` module, and `test_orchestration.py`.  
**Remaining:** Other modules may contain unused functions/classes. Not audited beyond the obvious deletions.  
**Fix:** Run `vulture` or similar dead code detector.

### 8. Import Path Inconsistency

**Status in v6.2.0:** Fixed 6 broken imports in memory modules.  
**Remaining:** No automated enforcement of import path correctness. Future refactors may reintroduce the same issue.  
**Fix:** Add `import-linter` or `ruff` import rules to CI.

### 9. No Structured Error Responses

**Issue:** API error responses are inconsistent — some return `{"error": "..."}`, others return `{"detail": "..."}`, others return plain text.  
**Fix:** Define a standard error response schema and apply across all routers.

### 10. Version Bump Not Automated

**Issue:** Version is manually updated in both `jarvis/__init__.py` and `pyproject.toml`.  
**Fix:** Use a single source of truth (e.g., `pyproject.toml` with dynamic versioning via `setuptools-scm`).

---

## Fixed in v6.2.0 (Historical)

For reference, these limitations existed prior to v6.2.0 and were resolved:

| # | Limitation | Status |
|---|-----------|--------|
| 1 | Missing `app` export prevented startup | FIXED |
| 2 | 6 broken memory module imports | FIXED |
| 3 | Contradictory search validation | FIXED |
| 4 | Frontend dead `/api/memory/stats` references | FIXED |
| 5 | httpx.Client resource leak | FIXED |
| 6 | WebSocket destroy bug in command-map.js | FIXED |
| 7 | 4 frontend memory leaks (drag, stream, resize, canvas) | FIXED |
| 8 | Fire-and-forget background tasks | FIXED |
| 9 | Silent exception handlers in mission_executor | FIXED |
| 10 | FTS5 unhandled errors | FIXED |
| 11 | Dead code (command_center, orchestration) | REMOVED |
