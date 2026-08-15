# JARVIS v10 — AI Operating System Master Plan

> **Version:** 1.0.0
> **Date:** 2026-08-01
> **Status:** Architecture Analysis + Incremental Implementation Roadmap
> **Source of Truth:** This document. Supersedes/extends `JARVIS_VISION_RESET.md`, `ROADMAP_v9.md`, `V9_ARCHITECTURE_CONTRACT.md`, `UI_REDESIGN_PLAN.md`.

---

## 0. The Vision

JARVIS is an AI Operating System, not a chat app.

- The user interacts with **one AI: JARVIS**. All workers are internal implementation details.
- Work is organized into **Domains** (departments), not poker cards.
- Every request flows through a **Global Pipeline** with mandatory review and fact-checking before anything reaches the user.
- The **Golden Core** is the permanent visual identity — it represents JARVIS state with living animation.
- **Voice is the primary interaction model**; typing remains fully supported.
- Large tasks auto-evolve into **Living Projects** that track themselves in real time.
- The UI is calm, dark-first, motion-rich, Apple/VisionOS/Raycast/Linear quality.

---

## 1. Current Architecture Analysis (v8.0.0 → v9 groundwork)

### 1.1 Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn, Jinja2, aiosqlite, Pydantic v2 |
| LLM | NVIDIA OpenAI-compatible API (httpx), Ollama fallback |
| Frontend | Vanilla JS/CSS (no build system), Three.js for Golden Core |
| Storage | SQLite `jarvis.db` + `memory_store/` + `~/.jarvis/` JSON |
| Realtime | SSE chat streaming + WebSocket `/ws/agents` event bus |
| Entry | `run.py`, `jarvis/launcher.py` (CLI), `jarvis/web/main.py` (app factory) |

### 1.2 What Already Exists (Reusable)

| v10 Need | Current Asset | Location |
|---|---|---|
| Agent hierarchy + orchestration | JARVIS → Kings → Workers, delegation, event emission | `jarvis/agents/` |
| Intent classification | `IntentClassifier` (regex) + conversation mode + response policy | `jarvis/brain/interaction/` |
| Domain review step | `ReviewPipeline` | `jarvis/brain/review.py` |
| Fact checking (seed) | ♦10 Fact Check worker | `jarvis/agents/workers/research.py` |
| Mission execution | DAG planner + MissionExecutor + mission/workspace managers | `jarvis/brain/dag_planner.py`, `mission_executor.py`, `jarvis/mission/`, `jarvis/workspace/` |
| Memory (5-layer) | Working/episodic/personal/journal/knowledge-graph + RAG + skills | `jarvis/brain/memory/`, `rag.py`, `skills.py` |
| Golden Core | `Graph3D` (Three.js bloom/particles), `JarvisCore` (SVG), state model | `web/static/js/graph-3d.js`, `jarvis-core.js`, `state-machine.js` |
| Voice capture/waveform | `AudioAnalyzer`, `VoiceExperience`, Web Speech STT | `web/static/js/audio-analyzer.js`, `voice-experience.js`, `voice.js` |
| TTS | macOS say / Piper / Kokoro / OpenAI / Coqui voice clone | `jarvis/web/services/tts.py`, `routers/voice.py` |
| Realtime status | WebSocket manager multiplexing `/ws/agents` | `web/static/js/ws-manager.js`, `routers/websocket.py` |
| Design system | `tokens.css` (source of truth) + `style.css`, dark-first, cyan/gold | `web/static/css/` |
| Capability registry + tri-state permissions | `CapabilityRegistry`, `PermissionSystem` | `jarvis/core/capabilities.py`, `permissions.py` |
| OS integration | Hotkeys, menubar, notifications, clipboard, watcher | `jarvis/os/` |
| Reliability | Retry/timeout, circuit breakers, health monitor, checkpoints | `jarvis/core/reliability.py`, `health_monitor.py`, `checkpoint.py` |
| Architecture profiles | Native + Hermes wrappers | `jarvis/architectures/` |
| 3D tooling seeds | Blender app profile, CAD/PCB/embedded providers | `jarvis/computer/applications/blender.py`, `jarvis/engineering/` |

### 1.3 What Is Obsolete / Legacy

| Item | Fate |
|---|---|
| Suit/Rank/card_id as the primary mental model | **Deprecated to alias** — internal compat shim only, removed from UI/prompts |
| Poker terminology in UI + agent prompts | Replaced with Domain vocabulary |
| Card badge visuals as navigation metaphor | Replaced by Domain views |
| Legacy root modules `agents/`, `tasks/`, `voice/`, `brain/`, `config/`, `memory/`, `safety/` | Already being deleted in v9 purge — finish the purge |
| Engineering workers registered twice (king class + `initialize_agents()`) | Fix — single registration path |
| Legacy mic recording/waveform in `app.js` | Remove; `voice-experience.js` is the owner |
| Hermes architecture (broken frontend bridge) | Preserved, not wired (v9 AD-4) |
| Duplicate Graph3D implementations | Already consolidated to `graph-3d.js` |

### 1.4 Critical Gaps for v10

1. **Domains**: only 4 divisions; need 6 (Engineering, Education, Research, 3D Studio, Finance, Personal). Education and 3D Studio are new; Finance is a worker to be elevated; System becomes internal services.
2. **Global Pipeline**: intent classification exists but no task estimation, no formal domain selection, no per-domain review gate, no shared global fact checker.
3. **Golden Core states**: 16 loose states exist; need 8 canonical states with smooth interpolated transitions + particle reactions + waveform.
4. **Voice-first**: push-to-talk partial; backend Whisper STT exists but is NOT wired to any web endpoint; no always-listening hook.
5. **Living Projects**: workspace/mission exist but no auto-estimation, no self-updating project entity, no project dashboard.
6. **UI shell**: still 6-workspace app-centric nav; needs domain-centric shell + project cards.

---

## 2. Target Architecture — v10

### 2.1 The Single Face

```
                    ┌─────────────────┐
                    │      USER       │
                    └────────┬────────┘
                             │  text / voice
                    ┌────────▼────────┐
                    │     JARVIS      │  ← the ONLY AI the user sees
                    └────────┬────────┘
```

### 2.2 Global Pipeline

```
User
  ↓
JARVIS  (single face)
  ↓
Intent Classification        ← exists (brain/interaction), extend to LLM-assisted
  ↓
Task Estimation (NEW)        ← size / runtime / domains / workers / complexity
  ├─ small ──────────────► immediate execution
  └─ large ──────────────► create Living Project
  ↓
Domain Selection (NEW)       ← DomainRouter: picks Domain Master(s)
  ↓
Domain Master                ← dispatch within domain
  ↓
Workers                      ← execute, emit events (existing)
  ↓
Domain Review (NEW gate)     ← per-domain quality review (extend brain/review.py)
  ↓
Global Fact Checker (NEW)    ← shared across ALL domains (formalize ♦10 → shared service)
  ↓
JARVIS Response              ← synthesized, evidenced, single voice
  ↓
User
```

**Rule:** Nothing reaches the user without passing Domain Review + Global Fact Checker.

### 2.3 Domains

| v10 Domain | Source | Domain Master | Workers |
|---|---|---|---|
| **Engineering** | ♠ Engineering King | `EngineeringMaster` | 13 existing engineering workers |
| **Education** | 🆕 NEW | `EducationMaster` | Tutor, Curriculum, Assessment, Explainer |
| **Research** | ♦ Research King | `ResearchMaster` | WebResearch, Documentation (+ Fact Checker → global) |
| **3D Studio** | 🆕 NEW (Blender profile + CAD providers exist) | `StudioMaster` | Modeling, Rendering, Animation, Fabrication |
| **Finance** | ♥ FinanceWorker (elevated) | `FinanceMaster` | Budget, Expense, Investments, Tax |
| **Personal** | ♥ Personal King | `PersonalMaster` | Calendar, Email, Tasks, Scheduling |
| **System** | ♣ System King | **internal** — becomes JARVIS Core Services (Files/Terminal/Apps become tools, not a user domain) |

### 2.4 Golden Core — 8 Canonical States

| State | Visual Language |
|---|---|
| `idle` | Slow cyan pulse, drifting particles |
| `listening` | Bright core, particles converge, waveform |
| `thinking` | Blue shift, slow rotation, spiral particles |
| `planning` | Gold accent, expanding rings |
| `researching` | Teal sweep, orbiting nodes |
| `working` | Green tint, outward pulse + worker stream |
| `speaking` | Gold waveform, outward rings |
| `completed` | Bright burst, particles disperse upward |

Transitions are **interpolated**, never abrupt. Existing 16 states map onto these 8 as sub-states.

### 2.5 Living Projects

Every large task auto-creates a Living Project that self-tracks:

```
Progress ████████░░░░  63%
Domains  ● Engineering ● Research ● Education
Workers  Backend · Frontend · Research · Testing
Current  "Implementing authentication"
Confidence  94%
ETA         12 minutes
Timeline    ✓ Planning ✓ Research ✓ Architecture ● Implementation ○ Testing ○ Verification ○ Delivery
```

Auto-update wiring: mission event → progress recalc → confidence recalc → next-best-action regeneration.

---

## 3. Migration Paths

### 3.1 Naming Migration (compat-first)

1. Keep `Suit`, `Rank`, `card_id`, `King`, `Worker` classes **as deprecated aliases** during migration — zero breakage.
2. Introduce `Domain` (enum), `DomainMaster`, `member_id` alongside.
3. API v2 endpoints expose domains; v1 endpoints remain.
4. Remove poker naming from UI + prompts last (after all backend code is domain-native).

### 3.2 Domain Creation

- New domains are new classes under `jarvis/agents/domains/` (or `jarvis/domains/`) registered through the same capability registry. System king is re-registered as internal services.

### 3.3 Pipeline Overlay

- `DomainRouter` wraps existing king dispatch — no rewrite of worker execution.
- `DomainReview` extends `brain/review.py` with per-domain thresholds.
- `FactChecker` is extracted from the Research worker into a shared singleton service.

### 3.4 Frontend

- Keep `tokens.css` + `graph-3d.js` as-is (identity anchors).
- Rebuild nav shell around Domains + Projects; reuse existing component system (LivingInterface, MissionDAG, CommandPalette, VoiceExperience).

---

## 4. Incremental Milestones

> Every milestone ends with a **functional application** and a **green test suite**.

### M0 — Stabilize Baseline (commit v9 groundwork)
- [ ] Run full test suite; fix regressions from in-flight v9 purge
- [ ] Finish dead-code purge (legacy root modules, dead templates/JS/CSS)
- [ ] Fix engineering worker double-registration
- [ ] `ruff check` + `ruff format` clean
- [ ] Commit a green v9 baseline
- **Exit:** `pytest` green, server starts, all pages load, clean git tree.

### M1 — Domain Model (backend)
- [ ] `Domain` enum + `DomainMaster` + `member_id` with compat aliases
- [ ] Add Education domain (master + 4 workers)
- [ ] Add 3D Studio domain (master + 4 workers, reusing Blender/CAD assets)
- [ ] Elevate Finance worker → Finance domain (master + 4 workers)
- [ ] Re-register System king as internal JARVIS Core Services
- [ ] API: `/api/domains` + `/api/domains/{id}`; keep `/api/agents` for compat
- [ ] Tests for all domain masters + new workers
- **Exit:** 6 domains live, old endpoints still work, coverage on domains added.

### M2 — Global Pipeline
- [ ] Task Estimator (size/runtime/domains/workers/complexity; small→immediate, large→project)
- [ ] DomainRouter (formal domain selection)
- [ ] Domain Review gate per domain
- [ ] Global Fact Checker shared service
- [ ] Pipeline event emission for realtime UI
- [ ] Tests: estimation accuracy, router selection, review + fact-check gates
- **Exit:** every chat response flows through the full pipeline; pipeline visible in UI.

### M3 — Golden Core + Motion
- [ ] 8 canonical states mapped onto `state-machine.js`
- [ ] Interpolated transitions + particle reactions per state
- [ ] Waveform integrated into listening/speaking states
- [ ] Contextual task label on core
- [ ] `prefers-reduced-motion` respected
- **Exit:** Golden Core visibly communicates all 8 states with smooth animation.

### M4 — Living Projects
- [ ] Project data model (SQLite) + ProjectManager (single owner)
- [ ] Auto-estimation triggers project creation
- [ ] Auto-update: progress/confidence/phase/ETA on every mission event
- [ ] Project Dashboard UI (pulse cards, real-time via existing WS)
- [ ] Tests: estimation, lifecycle, persistence across restart
- **Exit:** large task → project auto-created → dashboard updates in real time.

### M5 — Voice First
- [ ] Push-to-talk UX polish (hold-to-talk on Golden Core)
- [ ] Wire backend Whisper STT to web endpoint (currently unwired)
- [ ] Listening/speaking animations wired to Golden Core states
- [ ] Always-listening mode hook (future: wake word)
- [ ] Tests: STT endpoint, TTS timing
- **Exit:** voice is the primary interaction; typing works identically.

### M6 — Domain UI Shell + Hardening
- [ ] Navigation: Home + 6 Domains + Projects
- [ ] Domain views (master + worker cards, real-time status)
- [ ] Living Project cards with pulse + NBA
- [ ] Settings polish (domain config, voice, appearance)
- [ ] Accessibility (WCAG 2.1 AA), performance (Lighthouse ≥ 90), docs
- **Exit:** premium OS feel; all features accessible; docs updated to v10.

---

## 5. Evidence Requirements

- Every milestone: `pytest` green (report counts), `ruff` clean, server boots, core pages load.
- New subsystems ship with unit tests (estimation, router, review gates, project lifecycle).
- No milestone skips verification. No "success without evidence."

---

## 6. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Rename breaks prompts/workers that hardcode card_ids | High | High | Compat aliases until M6; grep for card_id usages per step |
| New domains (Education/3D Studio/Finance) are thin | Medium | Medium | Reuse existing assets (Blender profile, CAD providers, FinanceWorker); workers can share tools |
| Pipeline adds latency | Medium | Medium | Estimation is heuristic-first; review/fact-check parallelizable |
| Frontend rebuild regression | Medium | High | Component system reused; no rewrite of Golden Core |
| Voice STT wiring fragile | Medium | Medium | Keep Web Speech API as fallback |
