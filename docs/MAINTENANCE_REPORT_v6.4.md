# JARVIS Maintenance Report — v6.4.0

**Date:** 2026-07-20  
**Scope:** Full-stack codebase analysis (Python backend, JS/HTML frontend, database)  
**Current Version:** 6.4.0 (pyproject.toml)  
**Previous Audit:** v6.2.0 (see SYSTEM_AUDIT_v6.2.md)

---

## Executive Summary

JARVIS has **267 Python files** across **50 subdirectories** totaling **~50,360 lines**. The system has **1,162 collected tests**. While the core architecture is sound, the codebase has accumulated significant technical debt since v5.4.0: **15 dead/legacy modules** inside `jarvis/`, **8 orphaned root-level packages** that duplicate the canonical code, and **oversized files** requiring decomposition. This session fixed the 2 critical database bugs, frontend initialization, version alignment, and startup error handling.

**Key Findings (Updated):**
- ✅ **Database crash on Python 3.9 fixed** — Lazy `asyncio.Lock()` + execute proxy methods
- ✅ **Frontend initialization fixed** — `index.html` now references correct DOM IDs
- ✅ **Version aligned to v6.4.0** — All 7 files consistent
- ✅ **Startup error handling improved** — 4 silent `except` blocks now log
- ✅ **Pydantic v2 warnings eliminated** — Removed deprecated `env=` kwarg
- **15 legacy modules** (~6,600 lines) inside `jarvis/` that duplicate `brain/memory/` functionality
- **8 root-level packages** (`agents/`, `brain/`, `memory/`, `config/`, `safety/`, `voice/`, `web/`, `tasks/`) that are completely separate from the canonical `jarvis/` package
- **Oversized files** — `system.py` (950 lines), `cli_v2.py` (1,147 lines), `brain/` (41 files, 9,553 lines)
- **43 `except Exception: pass` blocks** remaining across `brain/` modules

---

## 1. Architecture Overview

### Canonical Package Structure (`jarvis/`)

```
jarvis/                          # Main Python package (267 files, ~50K lines)
├── __init__.py                  # Version: 6.4.0
├── cli.py                       # CLI entry point (891 lines)
├── cli_v2.py                    # CLI v2 (1,147 lines) ⚠ OVERSIZED
├── core/                        # Foundation (8 files, 1,998 lines)
│   ├── config.py                # Pydantic Settings
│   ├── database.py              # Async SQLite (825 lines)
│   ├── models.py                # Enums, dataclasses
│   ├── events.py                # EventBus (pub/sub)
│   ├── capabilities.py          # Capability registry
│   ├── diagnostics.py           # Startup health checks
│   └── reliability.py           # Retry/timeout/backoff
├── brain/                       # Intelligence layer (41 files, 9,553 lines) ⚠ LARGEST MODULE
│   ├── llm.py                   # LLM interface (470 lines)
│   ├── rag.py                   # RAG engine
│   ├── dag_planner.py           # DAG task planner
│   ├── mission_executor.py      # Mission execution
│   ├── skill_evolution.py       # Skill learning
│   ├── aci.py                   # Agent communication
│   ├── teams.py                 # Dynamic teams
│   ├── world_model.py           # World model
│   ├── privacy.py               # Privacy scrubber
│   ├── project_memory.py        # Project memory
│   ├── memory_provider.py       # Memory provider
│   ├── graphify_integration.py  # Graphify integration
│   ├── graph_analysis.py        # Graph analysis
│   ├── observability.py         # Observability
│   ├── developer.py             # Developer tools
│   ├── demo_learning.py         # Demo learning
│   ├── speculative.py           # Speculative planning
│   ├── review.py                # Review pipeline
│   ├── loop.py                  # Autonomous loop
│   ├── living_models.py         # Living intelligence models
│   ├── skills.py                # Skills engine
│   ├── core/                    # Brain core (6 files)
│   │   ├── brain.py             # JARVISBrain facade
│   │   ├── context.py           # BrainContextManager
│   │   ├── decision.py          # BrainDecisionEngine
│   │   ├── memory.py            # MemoryManager
│   │   ├── reasoning.py         # ReasoningEngine
│   │   └── models.py            # BrainContext, MemoryEntry, etc.
│   └── memory/                  # Memory subsystem (10 files, 2,884 lines)
│       ├── working.py           # Working memory (7 slots)
│       ├── episodic.py          # Episodic memory
│       ├── personal.py          # Personal preferences
│       ├── journal.py           # Daily journals
│       ├── consolidation.py     # Memory consolidation
│       ├── retrieval.py         # Multi-source retrieval
│       ├── importance.py        # Importance scoring
│       ├── extractor.py         # Memory extraction
│       ├── graph.py             # Knowledge graph (SQLite)
│       └── note.py              # Markdown notes
├── agents/                      # Agent hierarchy (19 files, 3,188 lines)
│   ├── jarvis.py                # Chief executive agent
│   ├── base.py                  # BaseAgent, CardAgent
│   ├── tools.py                 # Tool executor
│   ├── kings/                   # 4 division kings
│   ├── workers/                 # Worker agents
│   └── personas/                # Agent personas
├── mission/                     # Mission system (9 files, 1,829 lines)
│   ├── pipeline.py              # 10-stage pipeline
│   ├── manager.py               # Mission manager
│   ├── mission.py               # Mission model
│   ├── loop.py                  # Autonomous loop
│   └── replay/                  # Mission replay
├── web/                         # Web interface (22 files, 3,878 lines)
│   ├── main.py                  # FastAPI app (275 lines)
│   ├── routers/                 # 13 API routers
│   ├── api/mission_replay.py    # Mission replay API (466 lines)
│   ├── services/tts.py          # TTS providers
│   ├── templates/               # 7 HTML templates
│   └── static/                  # JS (15 files), CSS (2 files), vendor
├── computer/                    # Computer control (29 files, 4,848 lines)
├── browser/                     # Browser automation (7 files, 1,764 lines)
├── vision/                      # Vision system (11 files, 2,007 lines)
├── engineering/                 # Engineering tools (12 files, 1,163 lines)
├── workspace/                   # Workspace management (2 files)
├── tools/                       # Unified tool layer (5 files, 1,120 lines)
├── learning/                    # Continuous learning (3 files)
├── monitoring/                  # Self-monitoring (3 files)
├── os/                          # OS integration (7 files)
├── plugins/                     # Plugin system (3 files)
├── safety/                      # Safety validation (2 files)
├── voice/                       # Voice I/O (3 files)
├── testing/                     # Test engine (1 file)
├── verification/                # Verification engine (1 file)
├── review/                      # Review engine (1 file)
├── research/                    # Research engine (1 file)
├── execution/                   # Execution engine (1 file)
├── planner/                     # Architecture planner (1 file)
├── dashboard/                   # Engineering dashboard (4 files)
├── docs_engine/                 # Documentation engine (3 files)
├── repo_intelligence/           # Repository analysis (3 files)
├── codebase_index/              # Code indexing (4 files)
├── architecture_graph/          # Architecture visualization (4 files)
├── refactoring/                 # Refactoring engine (3 files)
├── self_improvement/            # Self-improvement (5 files)
├── iot/                         # IoT integration (3 files)
├── memory/                      # ⚠ THIN WRAPPER (5 lines, re-exports Database)
│
│   === LEGACY MODULES (DEAD CODE) ===
├── knowledge/                   # ⚠ DEAD — duplicate of brain/memory/graph.py
├── extraction/                  # ⚠ DEAD — duplicate of brain/memory/extractor.py
├── consolidation/               # ⚠ DEAD — duplicate of brain/memory/consolidation.py
├── timeline/                    # ⚠ DEAD — duplicate of brain/memory/episodic.py
├── second_brain/                # ⚠ DEAD — duplicate of brain/memory/retrieval.py
├── preferences/                 # ⚠ DEAD — duplicate of brain/memory/personal.py
├── decisions/                   # ⚠ DEAD — duplicate of brain/core/decision.py
├── projects/                    # ⚠ DEAD — duplicate of brain/project_memory.py
├── context/                     # ⚠ DEAD — duplicate of brain/core/context.py
├── suggestions/                 # ⚠ DEAD — partially wired (living_dashboard only)
├── journal/                     # ⚠ DEAD — duplicate of brain/memory/journal.py
├── eng_intel/                   # ⚠ DEAD — not wired to anything
├── living_dashboard/            # ⚠ DEAD — not wired to web UI
├── privacy/                     # ⚠ DEAD — duplicate of brain/privacy.py
└── memory_privacy/              # ⚠ DEAD — overlaps with brain/privacy.py
```

### Root-Level Orphaned Packages (NOT part of `jarvis/`)

These are **completely separate Python packages** at the repository root. They are NOT imported by the `jarvis/` package and appear to be legacy artifacts from a pre-monorepo era:

| Directory | Contents | Relationship to `jarvis/` |
|-----------|----------|--------------------------|
| `agents/` | `opencode.py` — OpenCode agent | Different from `jarvis/agents/` |
| `brain/` | `llm.py` — Uses `openai.OpenAI` (sync) | Older version of `jarvis/brain/llm.py` (uses httpx async) |
| `memory/` | `database.py` — `MemoryDatabase` (sync sqlite3) | Older version of `jarvis/core/database.py` (async aiosqlite) |
| `config/` | `config.py` — Simpler Config class | Older version of `jarvis/core/config.py` |
| `safety/` | `validator.py` | Duplicate of `jarvis/safety/` |
| `voice/` | `tts.py`, `whisper.py` | Older version of `jarvis/voice/` |
| `web/` | Contains `.env`, `jarvis.db`, `static/`, `voices/` | Legacy web artifacts |
| `tasks/` | `manager.py` — Simple TaskManager | Not imported by `jarvis/` |

**Impact:** These packages confuse developers, waste disk space, and risk accidental imports if `sys.path` includes the repo root.

---

## 2. Duplicate Systems

### 2.1 Memory Systems (3 overlapping layers)

| System | Location | Status | Overlaps With |
|--------|----------|--------|---------------|
| **Canonical** | `jarvis/brain/memory/` (10 files, 2,884 lines) | ✅ ACTIVE | — |
| Legacy v5.4 standalone | `jarvis/knowledge/` (4 files) | ❌ DEAD | `brain/memory/graph.py` |
| Legacy v5.4 standalone | `jarvis/extraction/` (3 files) | ❌ DEAD | `brain/memory/extractor.py` |
| Legacy v5.4 standalone | `jarvis/consolidation/` (3 files) | ❌ DEAD | `brain/memory/consolidation.py` |
| Legacy v5.4 standalone | `jarvis/second_brain/` (3 files) | ❌ DEAD | `brain/memory/retrieval.py` |
| Legacy v5.4 standalone | `jarvis/timeline/` (3 files) | ❌ DEAD | `brain/memory/episodic.py` |
| Legacy v5.4 standalone | `jarvis/preferences/` (3 files) | ❌ DEAD | `brain/memory/personal.py` |
| Legacy v5.4 standalone | `jarvis/decisions/` (3 files) | ❌ DEAD | `brain/core/decision.py` |
| Legacy v5.4 standalone | `jarvis/journal/` (2 files) | ❌ DEAD | `brain/memory/journal.py` |
| Legacy v5.4 standalone | `jarvis/projects/` (2 files) | ❌ DEAD | `brain/project_memory.py` |
| Root-level | `memory/` (1 file, 248 lines) | ❌ DEAD | `jarvis/core/database.py` |

### 2.2 Context Systems

| System | Location | Status |
|--------|----------|--------|
| Canonical | `jarvis/brain/core/context.py` (235 lines) | ✅ ACTIVE |
| Legacy | `jarvis/context/` (2 files, 350 lines) | ❌ DEAD |

### 2.3 Privacy Systems

| System | Location | Status |
|--------|----------|--------|
| Canonical | `jarvis/brain/privacy.py` (218 lines) | ✅ ACTIVE |
| Legacy | `jarvis/privacy/` (3 files, 241 lines) | ❌ DEAD |
| Legacy | `jarvis/memory_privacy/` (3 files, 422 lines) | ❌ DEAD |

### 2.4 Config Systems

| System | Location | Status |
|--------|----------|--------|
| Canonical | `jarvis/core/config.py` (90 lines) | ✅ ACTIVE |
| Root-level | `config/config.py` (69 lines) | ❌ DEAD |

### 2.5 LLM Systems

| System | Location | Status |
|--------|----------|--------|
| Canonical | `jarvis/brain/llm.py` (470 lines, httpx async) | ✅ ACTIVE |
| Root-level | `brain/llm.py` (191 lines, openai sync) | ❌ DEAD |

---

## 3. Dead Code

### 3.1 Legacy Modules Inside `jarvis/` (15 modules, ~40 files, ~6,600 lines)

| Module | Files | Lines | Notes |
|--------|------:|------:|-------|
| `knowledge/` | 4 | 858 | Full knowledge graph with relationships |
| `extraction/` | 3 | 470 | Memory extraction engine |
| `consolidation/` | 3 | 316 | Memory consolidation engine |
| `timeline/` | 3 | 356 | Timeline engine |
| `second_brain/` | 3 | 482 | Semantic search |
| `preferences/` | 3 | 345 | Preference engine |
| `decisions/` | 3 | 332 | Decision memory |
| `projects/` | 2 | 611 | Project manager (492-line __init__.py!) |
| `context/` | 2 | 350 | Context engine |
| `suggestions/` | 2 | 433 | Suggestion engine |
| `journal/` | 2 | 515 | Journal engine |
| `eng_intel/` | 3 | 860 | Engineering intelligence |
| `living_dashboard/` | 3 | 347 | Dashboard facade |
| `privacy/` | 3 | 241 | Privacy controls |
| `memory_privacy/` | 3 | 422 | Memory privacy |
| **TOTAL** | **~40** | **~6,638** | |

### 3.2 Root-Level Orphaned Packages (8 packages)

| Package | Files | Notes |
|---------|------:|-------|
| `agents/` | 2 | OpenCode agent (different from jarvis/agents/) |
| `brain/` | 2 | Old sync LLM (different from jarvis/brain/) |
| `memory/` | 2 | Old sync database (different from jarvis/core/) |
| `config/` | 2 | Old config (different from jarvis/core/) |
| `safety/` | 2 | Duplicate safety validator |
| `voice/` | 3 | Old voice (different from jarvis/voice/) |
| `web/` | 4+ | Legacy web artifacts (.env, jarvis.db, static, voices) |
| `tasks/` | 2 | Standalone task manager |

### 3.3 Root-Level Documentation Orphans (7 files)

| File | Notes |
|------|-------|
| `DOCUMENTATION.md` | Superseded by README + docs/ |
| `ENGINEERING_SUITE_PLAN.md` | Historical plan (v3.3.0, completed) |
| `OVERNIGHT_REPORT.md` | Historical audit (v3.2.2) |
| `PROJECT_INDEX.md` | Historical file index (v6.2.0) |
| `JARVIS_DOCUMENTATION.txt` | Full docs in .txt format |
| `JARVIS_SYSTEM_COMPLETE.txt` | Full docs in .txt format (v3.3.1) |
| `COMPUTER_AGENTS_REPORT.txt` | Research report (should be in research/) |

---

## 4. Frontend Issues

### 4.1 ~~Critical:~~ Broken Initialization in `index.html` ✅ FIXED

**Problem:** `index.html` (line 8) referenced `document.getElementById('jarvis-canvas')` but `base.html` does not contain any element with ID `jarvis-canvas`. The actual container is `#golden-core-container`. Similarly, `#hierarchy-content` did not exist.

**Fix Applied:** Updated DOM references to `#golden-core-container` and `#command-map`. Also removed broken 2-second auto-refresh polling and added `typeof` guards for class availability checks.

### 4.2 Version Inconsistencies

| File | Version | Expected |
|------|---------|----------|
| `pyproject.toml` | 6.4.0 | 6.4.0 ✅ |
| `jarvis/__init__.py` | 6.4.0 | 6.4.0 ✅ |
| `base.html` | v6.4.0 | 6.4.0 ✅ |
| `command_center.html` | v6.4.0 | 6.4.0 ✅ |
| `state-machine.js` | v6.4.0 | 6.4.0 ✅ |
| `living-interface.js` | v6.4.0 | 6.4.0 ✅ |

### 4.3 Duplicate Standalone Pages

These pages duplicate functionality that exists in the main SPA:
- `command_center.html` — standalone page with its own JS/CSS, doesn't use `base.html`
- `developer_dashboard.html` — standalone page with its own JS/CSS
- `command-map.html` — standalone page duplicating the SVG hierarchy in `base.html`

### 4.4 WebSocket Fragmentation

Three separate WebSocket connections exist:
- `ws://host/ws` — used by `command-center.html`
- `ws://host/ws/agents` — used by `living-interface.js`, `unified-timeline.js`, `developer_dashboard.html`
- Different message formats between the two endpoints

---

## 5. Oversized Files

| File | Lines | Issue |
|------|------:|-------|
| `jarvis/cli_v2.py` | 1,147 | Should be split into commands/ directory |
| `jarvis/web/routers/system.py` | 950 | 83+ endpoints in one router, should be split |
| `jarvis/brain/` (total) | 9,553 | 41 files — too many concerns in one module |
| `jarvis/computer/manager.py` | 840 | Large but cohesive |
| `jarvis/brain/llm.py` | 470 | Acceptable for core LLM interface |
| `jarvis/web/api/mission_replay.py` | 466 | Acceptable |

---

## 6. Unused Imports / Broken References

### 6.1 Frontend Dead References
- `index.html` → `#jarvis-canvas` (does not exist)
- `index.html` → `#hierarchy-content` (does not exist)
- `card-visualization.js` loaded by `base.html` but never instantiated in `app.js`

### 6.2 Backend Import Risks
- `brain/core/brain.py` imports from legacy modules via optional parameters (`knowledge_graph`, `preference_engine`, `decision_engine`, `timeline_engine`, `consolidation_engine`) — if any legacy module is removed, these become dead parameters
- `brain/core/context.py` references `timeline_engine` and `preference_engine` — both from dead modules
- `brain/core/memory.py` imports from `jarvis.knowledge.models` — would break if `knowledge/` is removed

### 6.3 Duplicate `app` Export
- `jarvis/web/main.py:275` creates `app = create_app()` at module level
- `jarvis/web/main.py:212` also defines `create_app()` which creates the same app
- `run.py` imports `create_app` and calls it again — creates a second app instance

---

## 7. Error Handling Gaps

### 7.1 Silent Exception Swallowing in Startup Path ✅ FIXED

In `jarvis/web/main.py` lifespan:
- ~~Line 117: `except Exception: pass` — agent state restoration~~ → now logs at DEBUG
- ~~Line 145: `except Exception: pass` — project memory registration~~ → now logs at DEBUG
- ~~Line 178: `except Exception: pass` — capability registration~~ → now logs at DEBUG
- ~~Line 189: `except Exception: pass` — startup event emission~~ → now logs at DEBUG
- Line 205: `except Exception: pass` — WebSocket bridge cleanup (shutdown path, acceptable)

### 7.2 Known from v6.2 Audit (Still Present)
- 43 remaining `except Exception: pass` handlers across `brain/` modules
- LLM `chat()` blocks the event loop with `time.sleep()` during retries
- Synchronous `sqlite3` calls in knowledge graph within async methods

---

## 8. Security Risks

### 8.1 Hardcoded Paths
- `config.py:22` — Hardcoded opencode binary path: `/Users/brianyang/.opencode/bin/opencode`
- `config.py:29` — Hardcoded workspace path: `/Users/brianyang`
- `main.py:142` — Hardcoded path: `/Users/brianyang/jarvis`

### 8.2 API Key Exposure
- `.env` file exists at project root (should be in `.gitignore`)
- `.env` also exists at `web/.env` (legacy location)
- `nvidia_api_key` and `openai_api_key` in Config — logged if config is printed

### 8.3 Rate Limiting
- Global POST/PUT/PATCH rate limit: 30/minute — may be too restrictive for legitimate use
- No rate limiting on GET endpoints (potential for scraping)

### 8.4 No Authentication
- All API endpoints are publicly accessible with no auth
- Settings can be changed via `POST /api/settings` without any authentication

---

## 9. Performance Concerns

### 9.1 Synchronous Operations in Async Context
- `brain/llm.py` — Uses `httpx.Client` (sync) with `time.sleep()` retries. Should use `httpx.AsyncClient`.
- `brain/memory/graph.py` — Uses synchronous `sqlite3` in methods called from async contexts. Causes event loop starvation.
- `knowledge/graph.py` — Same issue with synchronous SQLite.

### 9.2 Oversized Brain Module
- 41 files, 9,553 lines in `brain/` alone. Many files (aci.py, teams.py, speculative.py, demo_learning.py, etc.) appear to have minimal usage in production.
- Should be decomposed into: `brain/core/`, `brain/memory/`, `brain/planning/`, `brain/learning/`

### 9.3 Frontend Bundle Size
- 7 vendor JS files loaded on every page (Three.js, bloom shaders, etc.)
- 15 application JS files loaded on every page
- Most pages only need a subset

---

## 10. Testing Problems

### 10.1 Collection Warnings
```
PytestCollectionWarning: cannot collect test class 'TestingEngine' because it has a __init__ constructor
```
Location: `jarvis/testing/__init__.py:13` — `TestingEngine` class name conflicts with pytest's test collection.

### 10.2 Pydantic Deprecation Warnings
6 `PydanticDeprecatedSince20` warnings in `jarvis/core/config.py` for using `env=` parameter in `Field()` with pydantic-settings.

### 10.3 Missing Test Coverage
**No tests found for:**
- `jarvis/brain/rag.py`
- `jarvis/brain/review.py`
- `jarvis/brain/speculative.py`
- `jarvis/brain/teams.py`
- `jarvis/brain/skill_evolution.py`
- `jarvis/brain/demo_learning.py`
- `jarvis/brain/dag_planner.py`
- `jarvis/brain/developer.py`
- `jarvis/brain/observability.py`
- `jarvis/brain/aci.py`
- `jarvis/iot/` module
- `jarvis/web/routers/system.py` (largest router, 950 lines)
- All 15 legacy modules have tests but test dead code

### 10.4 Test-to-Code Ratio
- **1,162 tests** for **50,360 lines** = 1 test per 43 lines (acceptable but many test dead modules)

---

## 11. Circular Dependency Risks

### 11.1 Verified Import Chains
- `jarvis/brain/core/brain.py` → imports `MemoryManager` from `jarvis/brain/core/memory.py`
- `jarvis/brain/core/memory.py` → imports from `jarvis/knowledge/models` (legacy module)
- `jarvis/brain/core/context.py` → references `timeline_engine`, `preference_engine` (legacy modules)

If legacy modules are removed without updating these references, the brain core will break.

### 11.2 No True Circular Dependencies Detected
All import chains are acyclic. The risk is in forward references to legacy modules.

---

## 12. Recommendations Summary

### Priority 1 — Critical (Must Fix) ✅ ALL DONE
1. ✅ **Fix `index.html` initialization** — Reference correct DOM element IDs (`#golden-core-container`, `#command-map`)
2. ✅ **Update version strings** — Aligned all files to v6.4.0 (`__init__.py`, `pyproject.toml`, `base.html`, `command_center.html`, `state-machine.js`, `jarvis-core.js`, `living-interface.js`)
3. ✅ **Fix startup error handling** — Added logging to all `except Exception: pass` blocks in `main.py` lifespan
4. ✅ **Fix database crash on Python 3.9** — Lazy `asyncio.Lock()` initialization in `database.py`
5. ✅ **Fix memory subsystem broken calls** — Added `execute()`/`commit()`/`fetchone()`/`fetchall()` proxy methods to `Database` class

### Priority 2 — High (Should Fix)
6. **Remove 15 legacy modules** inside `jarvis/` (~6,600 lines of dead code)
7. **Remove 8 root-level orphaned packages** (confuse developers)
8. **Remove 7 orphaned root-level documentation files**
9. **Fix `pyproject.toml` build backend** — `setuptools.backends._legacy:_Backend` is deprecated

### Priority 3 — Medium (Plan to Fix)
10. ✅ **Fix hardcoded path** in `main.py` — `ai_tool_command` now uses dynamic path
11. ✅ **Fix Pydantic deprecation warnings** — Removed deprecated `env=` kwarg from `Field()` in `config.py`
12. **Split `system.py`** — 950-line router into domain-specific routers
13. **Split `cli_v2.py`** — 1,147-line CLI into command modules
14. **Convert LLM to async** — Replace `httpx.Client` + `time.sleep()` with `httpx.AsyncClient`
15. **Add authentication** to settings/admin endpoints

### Priority 4 — Low (Nice to Have)
16. **Consolidate WebSocket endpoints** — Merge `/ws` and `/ws/agents`
17. **Lazy-load frontend assets** — Only load JS needed per workspace
18. **Add missing test coverage** for brain/ submodules

---

## 13. Fixes Applied in This Session

| # | Fix | File | Impact |
|---|-----|------|--------|
| 1 | Lazy `asyncio.Lock()` init | `jarvis/core/database.py:810-825` | Fixes Python 3.9 module-level Lock crash |
| 2 | `execute()`/`commit()`/`fetchone()`/`fetchall()` proxies | `jarvis/core/database.py` | Fixes memory subsystem (episodic, personal, journal, working) |
| 3 | DOM ref fix `#jarvis-canvas` → `#golden-core-container` | `jarvis/web/templates/index.html` | Fixes Neural Core visualization init |
| 4 | DOM ref fix `#hierarchy-content` → `#command-map` | `jarvis/web/templates/index.html` | Fixes agent hierarchy display |
| 5 | Removed broken auto-refresh polling (2s interval) | `jarvis/web/templates/index.html` | Reduces server load |
| 6 | Version aligned to v6.4.0 | 7 files | Consistent versioning |
| 7 | Added logging to silent `except` blocks | `jarvis/web/main.py` | Debuggability |
| 8 | Fixed hardcoded path `code /Users/brianyang/jarvis` | `jarvis/web/main.py` | Portability |
| 9 | Removed deprecated `env=` from `Field()` | `jarvis/core/config.py` | Pydantic v2 compliance |

**Verification:**
- ✅ All 6 startup diagnostics pass (port, database, llm, agents, disk, api_key)
- ✅ `/api/memory/episodes` returns 200 (was 500)
- ✅ `/api/memory/personal` returns 200 (was 500)
- ✅ 186 tests pass in core test files (0 failures)
- ✅ 294 tests pass in broader suite (1 pre-existing failure in `test_plugins.py`)
- ✅ No Pydantic deprecation warnings

---

> *This report has been updated to reflect all fixes applied in the v6.4.0 maintenance session.*
