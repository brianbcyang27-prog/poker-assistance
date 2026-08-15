# Architecture Validation Report

> **Version:** 1.0.0
> **Date:** 2026-07-30
> **Base:** JARVIS Vision Reset — `JARVIS_VISION_RESET.md`
> **Status:** Pre-Phase 0 Analysis

---

## Classification Legend

| Label | Meaning |
|-------|---------|
| **KEEP** | Already aligns with vision. Clean up only. |
| **REFACTOR** | Valuable, but needs redesign to align with vision. |
| **MERGE** | Duplicate functionality — consolidate into one module. |
| **REPLACE** | A better architecture exists elsewhere in the codebase or the vision. |
| **REMOVE** | Dead, orphaned, or obsolete. No active production dependencies. |

---

## Backend Packages

### `jarvis/core/` (12 files) — **KEEP**
- **Purpose**: Config, database, events, diagnostics, models, capabilities, permissions, checkpoint, workflows, reliability, memory validation.
- **Vision Alignment**: 90% — This is the strongest foundation in the codebase. Async SQLite, event bus, startup diagnostics, and capability registry are all aligned with the vision of a reliable, self-diagnosing system.
- **Technical Debt**: No versioned migration framework (uses `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ADD COLUMN`). Global singleton pattern. Many bare `except` clauses.
- **Dependencies**: `aiosqlite`, `pydantic_settings`, `httpx`, `cryptography`
- **Depended By**: All memory managers, chat, agents, workspace, diagnostics, doctor, voice
- **Migration Strategy**: Preserve as-is. Add versioned migrations. Replace global singleton with proper DI if needed.
- **Effort**: Low (migration framework only)

### `jarvis/brain/` (25 entries, 40 files) — **REFACTOR**
- **Purpose**: LLM client, RAG, ACI agent communication, memory system (working/episodic/personal/journal), DAG planner, mission executor, skill evolution, model router, privacy, world model.
- **Vision Alignment**: 75% — The layered memory system and ACI protocol are aligned with the vision. But memory integration is fragmented, prompt construction is ad-hoc, and the "living models" / "world model" features are partially implemented.
- **Technical Debt**: Memory API contracts don't match router expectations. RAG uses heuristic keyword scoring, no embeddings. ACI has no persistence or locking. LLM has duplicated sync/async paths.
- **Dependencies**: `core/database.py`, `core/config.py`, external LLM APIs
- **Depended By**: `web/routers/chat.py`, `web/routers/memory.py`, `web/routers/system.py`, `agents/jarvis.py`
- **Migration Strategy**: 
  1. Fix memory-router contract mismatches (working memory `set` vs `update`, `remember_mode` values)
  2. Unify prompt construction through `brain/core/context.py`
  3. Add embedding support to RAG
  4. Consolidate memory providers
- **Effort**: High (but foundational)

### `jarvis/brain/memory/` (11 files) — **REFACTOR → KEEP**
- **Purpose**: Working, episodic, personal, journal, consolidation, extraction, importance scoring, graph, notes, retrieval.
- **Vision Alignment**: 85% — The layered approach is correct. But it's poorly wired to the rest of the system.
- **Migration**: Fix API mismatches, unify with `knowledge/` graph.

### `jarvis/brain/core/` (7 files) — **KEEP (with activation)**
- **Purpose**: Brain context, memory, reasoning, decision facade.
- **Vision Alignment**: 80% — `context.py` is the intended unified context builder, but it's not wired as the default LLM prompt path.
- **Migration**: Wire `context.py` into the primary LLM chat path.

### `jarvis/agents/` (19 files incl. subpackages) — **REFACTOR**
- **Purpose**: Agent hierarchy — BaseAgent, JarvisAgent, 4 Kings, 23 Workers, Personas.
- **Vision Alignment**: 85% — The card-suit hierarchy is genuinely innovative and aligned with the vision. Workers are well-structured. But several have broken tool syntax.
- **Technical Debt**: `BaseWorker` expects `[TOOL: ...]` syntax, but Research workers use `[BROWSER: ...]`. Self-review is self-scoring, not independent. No direct test coverage for kings/workers.
- **Dependencies**: `brain/llm.py`, `brain/dag_planner.py`, `core/models.py`, `core/events.py`
- **Depended By**: `web/main.py`, `web/routers/chat.py`
- **Migration Strategy**: Fix tool syntax mismatches. Add independent review step. Add test coverage.
- **Effort**: Medium

### `jarvis/agents/kings/` (5 files) — **KEEP**
- **Purpose**: EngineeringKing, PersonalKing, ResearchKing, SystemKing — division managers.
- **Vision Alignment**: 90%

### `jarvis/agents/workers/` (6 files) — **REFACTOR**
- **Purpose**: 23 specialized worker agents.
- **Technical Debt**: Tool syntax mismatches. No direct tests.
- **Migration**: Fix `[BROWSER:]` → `[TOOL:]`. Add test coverage.

### `jarvis/architectures/` (7 files) — **REFACTOR → REPLACE**
- **Purpose**: Pluggable architecture registry with JARVIS Native and Hermes implementations.
- **Vision Alignment**: 40% — Overengineered for current needs. The two-architecture system (Native + Hermes) adds complexity without clear user value. Hermes architecture is incomplete.
- **Technical Debt**: Hermes memory endpoint is broken (called from frontend, no backend). Architecture switching is not user-facing.
- **Migration**: Simplify to single architecture. Remove Hermes or defer to post-v1.0.
- **Effort**: Medium

### `jarvis/architecture_graph/` (4 files) — **REMOVE**
- **Purpose**: Repository architecture graphing and analysis.
- **Vision Alignment**: 10% — Standalone tool, no active production imports. Superseded by `architectures/` and `brain/graph_analysis.py`.
- **Dependencies**: None from outside this package.
- **Migration**: Delete after confirming no references. All imports are self-only + tests.
- **Effort**: Low

### `jarvis/workspace/` (2 files) — **REFACTOR**
- **Purpose**: Mission/workspace state manager, task/timeline/stage tracking.
- **Vision Alignment**: 60% — The concept of workspace state is needed, but it overlaps heavily with `mission/` package.
- **Technical Debt**: WorkspaceManager uses `Workspace` model from `core/models.py` but partial wiring.
- **Migration**: Merge with `mission/` into unified system.

### `jarvis/mission/` (9 files) — **MERGE INTO workspace/**
- **Purpose**: Mission pipeline, manager, DAG execution, replay.
- **Vision Alignment**: 70% — The 10-stage pipeline concept is the core of the vision's Autonomous Engineering pillar. But the implementation overlaps with `workspace/` and `brain/mission_executor.py`.
- **Active Imports**: `jarvis/tools/unified.py`, `jarvis/web/api/mission_replay.py`
- **Migration**: Consolidate pipeline/manager/executor into one clear path. Merge with workspace/.

### `jarvis/tools/` (6 files) — **REFACTOR**
- **Purpose**: Unified tool layer, registry, agent tools, models, result.
- **Vision Alignment**: 70% — The unified facade concept is correct, but it exists alongside legacy `agents/tools.py`. Some methods reference backends that don't exist.
- **Technical Debt**: `EngineeringKnowledgeManager` imported but not exported from `engineering/knowledge.py`. Computer controller vs ComputerManager duality.
- **Migration**: Eliminate `agents/tools.py`. Fix broken backend references. Align with ComputerManager/browser/vision APIs.
- **Effort**: Medium

### `jarvis/computer/` (29 files) — **REFACTOR**
- **Purpose**: OS/UI control with permissions, sandbox, accessibility, app profiles.
- **Vision Alignment**: 80% — Comprehensive and well-structured. But controller vs manager duality is confusing.
- **Technical Debt**: `computer/controller.py` is used by `BaseWorker`, `computer/manager.py` is the permission-gated version. `/api/computer/actions` returns static, incomplete list.
- **Migration**: Unify controller and manager. Update actions endpoint to reflect actual supported actions.
- **Effort**: Medium

### `jarvis/browser/` (7 files) — **KEEP**
- **Purpose**: Secure browser automation with Playwright.
- **Vision Alignment**: 90% — Well-structured, security-gated.
- **Effort**: Low

### `jarvis/voice/` (4 files) — **KEEP**
- **Purpose**: Speech I/O, TTS, STT.
- **Vision Alignment**: 85% — Solid foundation for the voice features in the vision.
- **Note**: `/api/voice/generate` endpoint is called from frontend but missing from backend.

### `jarvis/vision/` (11 files) — **KEEP**
- **Purpose**: Screen capture, vision analysis, object detection, grounding.
- **Vision Alignment**: 85% — Needed for computer control and multimodal features.
- **Effort**: Low

### `jarvis/security/` (12 files) — **KEEP**
- **Purpose**: Secret vault, encryption, scanning, audit, redaction, git protection.
- **Vision Alignment**: 90% — Comprehensive security layer. No `jarvis/safety/` package exists; security fills this role.

### `jarvis/os/` (8 files) — **REFACTOR**
- **Purpose**: System-level integration: notifications, clipboard, hotkeys, menubar, file watcher.
- **Vision Alignment**: 95% — Directly aligns with the vision's Daily Life Integration pillar (ambient awareness, menubar, notifications). Valuable but needs consistency pass.
- **Effort**: Low

### `jarvis/iot/` (3 files) — **KEEP**
- **Purpose**: ESP32/Arduino device manager.
- **Vision Alignment**: 70% — Niche but valuable for the full OS vision.
- **Effort**: Low

### `jarvis/plugins/` (3 files) — **KEEP (scaffold)**
- **Purpose**: Plugin manager, manifest, type system.
- **Vision Alignment**: 60% — Scaffold exists but not fully wired. Needed for Phase 9.
- **Effort**: Low (leave for now)

### `jarvis/vision/` (11 files) — **KEEP**
- Already covered above.

---

## Orphaned / Duplicate Packages (REMOVE or MERGE)

These packages have **no active production imports** (only self-imports and test files).

| Package | Files | Lines | Recommendation | Rationale |
|---------|-------|-------|----------------|-----------|
| `architecture_graph/` | 4 | ~680 | **REMOVE** | Superseded by `architectures/` + `brain/graph_analysis.py` |
| `living_dashboard/` | 3 | ~270 | **REMOVE** | Dead package; not imported by web app |
| `projects/` | 2 | ~540 | **REMOVE** | Dead; only self-imports + tests |
| `journal/` | 2 | ~410 | **REMOVE** | Superseded by `brain/memory/journal.py` |
| `suggestions/` | 2 | ~390 | **REMOVE** | Dead; only self-imports + tests |
| `eng_intel/` | 3 | ~670 | **REMOVE** | Dead; only self-imports + tests |
| `codebase_index/` | 4 | ~750 | **REMOVE** | Superseded by `repo_intelligence/` (also dead, but newer) |
| `repo_intelligence/` | 3 | ~985 | **REMOVE** | Dead; only self-imports + tests |
| `refactoring/` | 3 | ~710 | **REMOVE** | Dead; only self-imports + tests |
| `planner/` | 1 | ~50 | **REMOVE** | Empty scaffold |
| `memory/` (root) | 1 | ~1 | **REMOVE** | Empty stub |

### Legacy Top-Level Modules (REMOVE)
| Path | Files | Lines | Rationale |
|------|-------|-------|-----------|
| `/brain/` (legacy) | 5 | ~300 | Superseded by `jarvis/brain/` |
| `/config/` (legacy) | 2 | ~150 | Superseded by `jarvis/core/config.py` |
| `/memory/` (legacy) | 2 | ~200 | Superseded by `jarvis/brain/memory/` |
| `/safety/` (legacy) | 2 | ~100 | Superseded by `jarvis/security/` |

---

## Active Overlapping Systems (MERGE)

| System A | System B | Recommendation |
|----------|----------|----------------|
| `mission/` (pipeline, manager, loop) | `workspace/` (manager) + `brain/mission_executor.py` | **MERGE** into one unified mission/workspace system |
| `tools/unified.py` | `agents/tools.py` (ToolExecutor) | **MERGE** into `tools/unified.py`, remove legacy |
| `computer/manager.py` | `computer/controller.py` | **MERGE** into `computer/manager.py` with permissions |
| `brain/memory/` (graph, notes) | `knowledge/` (graph, relationships) | **MERGE** into `brain/memory/` |
| `brain/memory/journal.py` | `journal/` (root) | **REMOVE** root `journal/`, keep `brain/memory/journal.py` |
| `brain/` (living_models, world_model) | `world.py` router | **REFACTOR** — align world model usage |

---

## Frontend Assets

### JS Files (23 total)

| File | Classification | Rationale |
|------|---------------|-----------|
| `app.js` | **REFACTOR** | Main SPA controller — 16 dead functions (17.4%), event listener accumulation |
| `state-machine.js` | **KEEP** | Core state model |
| `ws-manager.js` | **KEEP** | WebSocket client |
| `living-interface.js` | **KEEP** | Realtime HUD |
| `audio-analyzer.js` | **KEEP** | Audio visualization |
| `workspace-manager.js` | **KEEP** | Workspace state |
| `command-palette.js` | **KEEP** | ⌘K palette |
| `chat-background.js` | **KEEP** | 3D chat backdrop |
| `voice.js` | **KEEP** | Speech recognition |
| `voice-experience.js` | **KEEP** | Premium voice UI |
| `vision-experience.js` | **KEEP** | Vision capture UI |
| `computer-control.js` | **KEEP** | Computer control panel |
| `digital-twin.js` | **KEEP** | State avatar |
| `explainability.js` | **KEEP** | Explanation overlay |
| `graph-3d.js` | **KEEP** | Active 3D neural core |
| `jarvis-core.js` | **KEEP** | SVG arc-reactor |
| `graph3d.js` | **REMOVE** | Legacy duplicate of graph-3d.js |
| `mission-dag.js` | **REFACTOR** | Calls missing `/api/system/dag` |
| `mission-timeline.js` | **KEEP** | Execution timeline |
| `mission-panel.js` | **REMOVE** | Dead/unused |
| `memory-panel.js` | **REMOVE** | Dead (calls missing Hermes API) |
| `debug-patch.js` | **REMOVE** | Debug-only patcher |
| `ws-manager.test.js` | **KEEP** | Unit test (not runtime) |

### CSS Files (5 total)

| File | Classification | Rationale |
|------|---------------|-----------|
| `style.css` | **REFACTOR** | Only active stylesheet (6457 lines), monolithic, contains duplicate token definitions |
| `design-tokens.css` | **REMOVE** | Dead — content largely duplicated in style.css |
| `animations.css` | **REMOVE** | Dead — not referenced |
| `mission-panel.css` | **REMOVE** | Dead — not referenced |
| `memory-panel.css` | **REMOVE** | Dead — not referenced |

### HTML Templates (3 total)

| Template | Classification | Rationale |
|----------|---------------|-----------|
| `base.html` | **REFACTOR** | Main SPA shell — needs redesign per vision. Currently serves 3 routes. |
| `developer_dashboard.html` | **KEEP** | Admin dashboard |
| `command-map.html` | **REMOVE** | Unreachable template, references missing assets |

---

## API Endpoints

### Broken Frontend-Backend Contracts

| Frontend Call (in JS) | Backend Route | Status |
|------------------------|---------------|--------|
| `GET /api/sessions` | Should be `GET /api/chat/sessions` | **MISMATCH** — frontend uses old path |
| `GET /api/system/dag` | No backend route exists | **MISSING** |
| `GET /api/architectures/hermes/memory` | No backend route exists | **MISSING** |
| `POST /api/voice/generate` | No backend route (clone generate exists) | **MISSING** |
| `GET /api/computer/actions` | Returns static incomplete list | **OUT OF SYNC** |

### Router Status

| Router | Status | Notes |
|--------|--------|-------|
| `chat.py` | **KEEP** | Active, used by frontend |
| `agents.py` | **KEEP** | Active |
| `workspace.py` | **KEEP** | Active but inconsistent shapes |
| `memory.py` | **REFACTOR** | Contract mismatches with backend |
| `voice.py` | **KEEP** | Active, missing `/generate` |
| `pages.py` | **REFACTOR** | Dead routes (`/command-map`, `/history`) |
| `computer.py` | **REFACTOR** | Static action list out of sync |
| `system.py` | **KEEP** | Largest router, many endpoints |
| `websocket.py` | **KEEP** | Core real-time bridge |
| `settings.py` | **KEEP** | Active |
| `auth.py` | **KEEP** | Auth flow |
| `security.py` | **KEEP** | Backend-only (security management) |
| `iot.py` | **KEEP** | Backend-only (IoT management) |
| `engineering.py` | **KEEP** | Backend-only (CAD/PCB/etc.) |
| `world.py` | **KEEP** | Backend-only (world model) |
| `checkpoints.py` | **KEEP** | Backend-only (checkpoints) |
| `mission_replay.py` | **KEEP** | Backend-only (replay) |

---

## Summary: Estimated Cleanup Impact

| Action | Count | Est. Lines Removed | Est. Effort |
|--------|-------|-------------------|-------------|
| **REMOVE** orphaned Python packages | 11 | ~5,400 | 2h |
| **REMOVE** legacy top-level modules | 4 | ~750 | 30min |
| **REMOVE** dead CSS files | 4 | ~2,327 | 15min |
| **REMOVE** dead JS files | 4 | ~1,800 | 15min |
| **REMOVE** dead HTML templates | 1 | ~50 | 5min |
| **REMOVE** duplicate JS | 1 | ~500 | 5min |
| **MERGE** overlapping systems | 5 groups | N/A | 4h |
| **REFACTOR** core modules | 10 modules | N/A | 16h |
| **FIX** broken frontend-backend contracts | 5 mismatches | N/A | 2h |
| **Total Phase 0** | | **~10,800 lines removed** | **~10h** |

---

## Vision Alignment Heatmap

```
                    Current    Target
core/               ██████░░  ████████
brain/              ████░░░░  ████████
agents/             ██████░░  ████████
web/                ██░░░░░░  ████████
mission/            ████░░░░  ████████
workspace/          ████░░░░  ████████
computer/           ██████░░  ████████
browser/            ███████░  ████████
voice/              ██████░░  ████████
vision/             ██████░░  ████████
security/           ███████░  ████████
os/                 ████░░░░  ████████
architectures/      ██░░░░░░  █░░░░░░░
plugins/            ██░░░░░░  ██████░░
iot/                ██████░░  ████████
tools/              ████░░░░  ████████
```

*"Current" = alignment with today's codebase quality vs. what's needed for the vision*

---

## Appendix: Test Coverage Gaps

| Module | Direct Tests | Coverage Signal |
|--------|-------------|-----------------|
| `agents/kings/` | None | ❌ Critical gap |
| `agents/workers/` | None | ❌ Critical gap |
| `agents/jarvis.py` | None | ❌ Critical gap |
| `workspace/manager.py` | None | ❌ Critical gap |
| `brain/mission_executor.py` | None | ❌ Critical gap |
| `tools/unified.py` | None | ❌ Critical gap |
| `tools/registry.py` | `tests/test_tools.py` | ✅ Good |
| `computer/manager.py` | `tests/test_computer.py` | ⚠️ Partial |
| `browser/manager.py` | `tests/test_browser.py` | ✅ Good |
| `security/` | `tests/test_security.py` | ✅ Good |
| `mission/manager.py` | `tests/test_mission_manager.py` | ✅ Good |
| `core/database.py` | Implicit via others | ⚠️ Indirect |
