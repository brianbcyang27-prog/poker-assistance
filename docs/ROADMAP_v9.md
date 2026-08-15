# JARVIS v9.0.0 — Roadmap to a Personal AI Operating System

> **Version:** 1.0.0
> **Date:** 2026-07-30
> **Status:** Active Planning
> **Source Documents:**
> - JARVIS_VISION_RESET.md (source of truth)
> - ARCHITECTURE_VALIDATION_REPORT.md (module audit)
> - SYSTEM_DEPENDENCY_MAP.md (dependency graphs)
> - PHASE0_PLAN.md (initial cleanup plan — superseded by this document)
> - **Background audits:** CLI/startup, security/permissions, reliability/checkpoints, logging/tests

---

## Preamble

### Mission

Build the world's first Personal AI Operating System — software that feels less like a chatbot and more like a quiet, intelligent presence that helps its user accomplish meaningful work every day.

### Principles

- **Never sacrifice architecture for speed.**
- **Never sacrifice reliability for features.**
- **Never sacrifice user experience for technical convenience.**
- Every decision should still make sense five years from now.
- When in doubt, choose the solution that will still feel modern in 2031.

### The Golden Rule

The Golden 3D Core (`jarvis-core.js` + `graph-3d.js`) is the identity of JARVIS. It must never be removed or replaced. Everything else may evolve. Build around it. Treat it as the heart of the operating system.

### Current State Summary (Pre-Foundation)

| Metric | Value |
|--------|-------|
| Total Python packages | 38 (~17 orphaned) |
| Total Python lines | ~51,310 (~10K dead) |
| Test files | 30 (+ conftest) |
| Collected tests | 821 (down from stale README claim of 1,162) |
| Kings/workers test coverage | **Zero** |
| Frontend JS files | 23 (4 dead) |
| Broken API contracts | 5 confirmed |
| Startup to usable | **Not instant** — blocking diagnostics, repeated LLM construction |
| Centralized logging | **None** — mixed stdlib + loguru, no config |
| Circuit breakers | **None** |
| Automatic rollback | **None** |
| Continuous health monitoring | **None** |
| Permissions | Boolean only (5 capabilities) — no trinary model |
| Orphaned packages | 11 Python + 4 legacy root modules |

---

## Phase A — Foundation

> **Goal:** JARVIS becomes stable, observable, secure, and maintainable. Dead code is removed. Architecture is audited. Testing catches regressions. The system can be trusted.

### A1 — Dead Code Removal

**Why:** The codebase has ~10K lines of dead code across 11 orphan packages, 4 legacy root modules, 4 dead CSS files, 4 dead JS files, and 1 unreachable template. This creates confusion, slows tooling, and increases cognitive load for every contributor.

**Tasks:**

1. Remove orphan Python packages (after dependency confirmation):
   `architecture_graph/`, `living_dashboard/`, `projects/`, `journal/`, `suggestions/`, `eng_intel/`, `codebase_index/`, `repo_intelligence/`, `refactoring/`, `planner/`, `memory/`
2. Remove legacy root modules: `/brain/`, `/config/`, `/memory/`, `/safety/`
3. Remove dead CSS: `design-tokens.css`, `animations.css`, `mission-panel.css`, `memory-panel.css`
4. Remove dead JS: `graph3d.js`, `mission-panel.js`, `memory-panel.js`, `debug-patch.js`
5. Remove unreachable template and route: `command-map.html`
6. Remove corresponding orphaned test files

**Dependencies:** None (independent — safe to do first)
**Effort:** ~4 hours
**Risks:** Low — all have been verified to have zero active production imports in the architecture audit
**Success Criteria:** `python -c "from jarvis.web.main import app"` succeeds. Server starts. All pages load. Zero files removed that had active dependencies.
**Verification:** Per-file grep confirmation → deletion → import test → server start → browse core pages

---

### A2 — Structured Logging

**Why:** Current logging is ad-hoc (every module calls `logging.getLogger(__name__)` or `loguru.logger` with no central config, no log rotation, no structured output). `loguru` is used in 14 files but not declared in dependencies. Debugging production issues is guesswork.

**Tasks:**

1. Choose a single logging framework (stdlib `logging` with structured format — removes loguru dependency risk)
2. Create `jarvis/core/logging.py` with centralized configuration:
   - Structured JSON output (timestamp, level, module, message, context)
   - File rotation (daily, 30-day retention)
   - Console output for CLI
3. Replace all `loguru` imports with centralized logger
4. Bootstrap at all entry points: `cli.py`, `run.py`, `__main__.py`

**Dependencies:** None
**Effort:** 3 hours
**Risks:** Low — purely additive until the final loguru migration step
**Success Criteria:** Every module logs through one configurable path. Logs are structured. Log rotation works.
**Verification:** Start server → check log file created with structured format → grep for loguru imports → confirm zero remaining

---

### A3 — Permission System (Trinary)

**Why:** The v9 vision requires every capability to support Always Allow / Ask Every Time / Deny. Current system is boolean-only (enabled/disabled) for 5 capabilities. Computer and browser have risk-based engines but no per-capability trinary persistence. User cannot configure clipboard, notifications, voice, or camera permissions.

**Tasks:**

1. Design capability/permission model:
   - Capabilities: terminal, files, browser, clipboard, notifications, voice, camera, screen, accessibility, network, automation, system_settings
   - Each capability: `allow` | `ask` | `deny` (persisted)
   - Each capability: optional `require_confirmation` for dangerous actions
2. Update `core/permissions.py`:
   - Add tri-state storage in `~/.jarvis/permissions.json`
   - Add migration path from old boolean model
3. Wire `computer/permissions.py` and `browser/security.py` to consult the new trinary policy first, fall back to risk-based engine
4. Update `/api/settings/permissions` to expose tri-state values
5. Update `web/static/js/app.js` and `base.html` to render tri-state UI (toggle with 3 states or dropdown per capability)
6. Add missing capabilities: clipboard, notifications, voice, camera

**Dependencies:** None (built on existing `core/permissions.py`)
**Effort:** 6 hours
**Risks:** Medium — changes to permission enforcement could block legitimate operations. Must test each capability.
**Success Criteria:** User can set Allow/Ask/Deny for each capability in Settings. Computer/browser actions respect the policy. No regression in existing permission checks.
**Verification:** Set permission → execute action → confirm correct gate → change permission → confirm new gate → repeat for all 12 capabilities

---

### A4 — Reliability Infrastructure

**Why:** Current reliability primitives exist but are incomplete. There is no circuit breaker pattern, no automatic rollback, no continuous health monitoring, and no durable restart recovery. For a daily-driver OS, these are non-negotiable.

**Tasks:**

1. **Circuit breakers** — Implement in `core/reliability.py`:
   - Per-module circuit breaker with configurable thresholds (failure count, timeout, half-open retry interval)
   - Wire into: LLM client, browser, vision, computer control, mission pipeline
   - Provide breaker state through health API
2. **Checkpoint integrity** — Update `core/checkpoint.py`:
   - Add SHA-256 checksum to each checkpoint
   - Add verification step before restore
   - Add transactional index save (write to temp, rename)
   - Fix potential ID collision (`time.time()*1000` → UUID)
3. **Continuous health monitoring** — Build `core/health_monitor.py`:
   - Periodic checks (every 30s) for: database, LLM, agents, memory, websocket
   - Publish state changes via event bus
   - Expose through `/api/system/health` (already exists, enrich it)
   - Auto-repair hooks for known failure modes
4. **Mission/workflow durability** — Wire checkpointing into mission pipeline:
   - Auto-checkpoint at each mission stage transition
   - On restart: detect incomplete missions, offer to resume or rollback
   - Store mission state in SQLite (not JSON files)

**Dependencies:** A2 (logging) — circuit breakers need structured logging
**Effort:** 10 hours
**Risks:** Medium — circuit breakers could mask transient failures if tuned wrong. Start conservative.
**Success Criteria:** After startup, health monitor reports green for all subsystems within 30s. Circuit breaker opens after N consecutive failures, auto-recovers. Mission survives process restart. Checkpoint import runs and verifies integrity.
**Verification:** Kill LLM connection → confirm circuit opens → restore → confirm circuit closes → restart while mission active → confirm resume prompt appears

---

### A5 — Testing Foundation

**Why:** 821 tests exist but there are critical gaps. Kings, workers, and JarvisAgent have zero direct test coverage. There's no coverage configuration, no test categorization, and no CI pipeline. Dead code tests (orphan packages) inflate the count.

**Tasks:**

1. Add coverage configuration:
   - `pytest-cov` with thresholds (aim: 60% initial, 80% by Phase C)
   - `.coveragerc` excluding orphan packages, dead code, vendor code
2. Add critical-path tests:
   - Agent hierarchy: kings (4 files), workers (6 files), JarvisAgent
   - Permission system: all 12 capabilities, tri-state, persistence
   - Checkpoint system: create/verify/restore/rollback/integrity
   - Startup: latency, deferred loading, health check
3. Remove test files for orphaned packages (aligned with A1)
4. Add test markers: `unit`, `integration`, `slow`, `native` (requires OS APIs)
5. Update README test counts to match reality

**Dependencies:** A1 (dead code removal — removes orphan tests), A2 (logging — testability), A3 (permissions — tests it), A4 (reliability — tests it)
**Effort:** 8 hours
**Risks:** Low — additive only
**Success Criteria:** `pytest --cov=jarvis --cov-report=term` reports ≥60% coverage. All kings/workers have basic creation and dispatch tests. Permission system has trinary enforcement tests.
**Verification:** Run test suite before and after — confirm critical gaps filled, orphan tests removed, coverage threshold met

---

## Phase B — Core Architecture Consolidation

> **Goal:** Every responsibility has exactly one owner. One memory system, one mission system, one tool system, one event bus, one context builder. Contradictory architectures are unified.

### B1 — Memory System Unification

**Why:** Memory is split across `brain/memory/` (working, episodic, personal, journal, consolidation, importance, extraction, graph) and `knowledge/` (graph, models, relationships). `knowledge/` is imported by `brain/core/memory.py` but should be part of the unified memory layer. API contracts between memory routers and backend have mismatches.

**Tasks:**

1. Merge `knowledge/` (graph, models, relationships) into `brain/memory/graph.py`
2. Fix API contract mismatches:
   - `working_memory.set()` vs `update()` — align naming
   - `remember_mode` values — align between `brain/memory/` and API
3. Unify memory retrieval path: all queries go through `brain/memory/retrieval.py`
4. Add memory health endpoint verification (exists but under-validated)

**Dependencies:** A1 (removes orphan packages that might be confused with memory)
**Effort:** 4 hours
**Risks:** Low-medium — knowledge graph import changes affect brain/core/memory.py. Must update import paths.
**Success Criteria:** All memory operations work through one path. No duplicate graph model classes. API returns consistent shapes.
**Verification:** Run memory tests → create/read/update/delete through all memory types → check API responses match documented shapes

---

### B2 — Mission/Workspace Unification

**Why:** Mission execution is split across `mission/` (pipeline, manager, loop, replay), `workspace/` (workspace manager), and `brain/mission_executor.py`. Three overlapping systems create confusion about where mission state lives and how to execute multi-step tasks.

**Tasks:**

1. Merge workspace state into mission manager:
   - `workspace/manager.py` state moves into `mission/manager.py`
   - Models consolidate into one `Mission` model
2. Merge `brain/mission_executor.py` into `mission/pipeline.py`
3. Replace file-based mission persistence with SQLite-backed storage (coordinated with A4 durability)
4. Update API routes that reference workspace to point to mission manager

**Dependencies:** A4 (reliability — checkpoint durability) for SQLite-backed missions
**Effort:** 6 hours
**Risks:** Medium — workspace API consumers (frontend, agents) need migration
**Success Criteria:** Mission create/execute/save/load/resume works through one manager. Workspace API returns results from mission manager. No code imports both `mission/` and `workspace/` separately.
**Verification:** Create mission → execute stages → save → restart → resume → verify state consistent

---

### B3 — Tool System Unification

**Why:** Tool execution is split between `tools/` (unified, registry, models) and `agents/tools.py` (ToolExecutor). Workers have tool syntax mismatches (Research workers use `[BROWSER:]` instead of `[TOOL:]`).

**Tasks:**

1. Deprecate `agents/tools.py` — route all tool execution through `tools/unified.py`
2. Fix Research worker tool syntax: `[BROWSER:]` → `[TOOL:]`
3. Rationalize tool registry: ensure all 23 workers register their tools consistently
4. Add tool execution timeout via `core/reliability.py` circuit breaker

**Dependencies:** A4 (circuit breakers), A2 (logging — tool execution)
**Effort:** 4 hours
**Risks:** Low — `tools/unified.py` is already the newer system. `agents/tools.py` was the predecessor.
**Success Criteria:** All workers execute through unified tool layer. No worker uses non-standard tool syntax. Tool timeouts trigger proper error handling.
**Verification:** Test each king → worker → tool path → confirm no agents/tools.py imports remain → confirm circuit breaker behavior on tool timeout

---

## Phase C — Daily Driver Experience

> **Goal:** JARVIS becomes enjoyable to use every day. Startup is instant. Voice works immediately. The system survives crashes. The user trusts it.

### C1 — Instant Startup

**Why:** Current flow: `jarvis` → blocking dependency checks → subprocess uvicorn → sequential diagnostics (up to 30s with repeated LLM construction) → health check (10s timeout) → ready. A daily driver must feel instant.

**Tasks:**

1. **Fix CLI launch** — `jarvis` command must return immediately:
   - Split CLI from server: `jarvis` prints "JARVIS starting..." and backgrounds the server
   - or: `jarvis` opens a CLI interface immediately, server starts in background
2. **Fix bug** `launcher.check_dependencies` calls `importlib.import_name()` (doesn't exist):
   - Replace with `importlib.import_module()`
3. **Lazy LLM construction** — The single biggest startup bottleneck:
   - `LLM.__init__()` runs `ollama list` with 5s timeout
   - This is called 5+ times during startup (diagnostics + JARVIS + 4 kings)
   - Solution: make LLM construction lazy (connect on first use, not on init)
   - Solution: cache the Ollama check result
4. **Deferred server initialization:**
   - Move diagnostics from blocking startup to background task
   - Server starts accepting requests immediately, diagnostics stream in
   - Architecture initialization (Native/Hermes) becomes lazy
   - Voice engine loads on first voice request, not at startup
5. **Parallel startup path:**
   - Current: sequential diagnostics (port → db → LLM → agents → disk → api_key)
   - New: independent checks run in parallel
   - Report results as they complete (event-driven, not polling)

**Dependencies:** A2 (logging), A4 (health monitoring — replaces blocking diagnostics)
**Effort:** 8 hours
**Risks:** Medium — lazy LLM could introduce latency on first message. Must be transparent to user.
**Success Criteria:** `jarvis` returns control within 1 second. Server is accepting requests within 2 seconds. Diagnostics complete in background within 10 seconds. First chat works correctly (lazy LLM connects transparently).
**Verification:** Time `jarvis` from enter to prompt → measure "ready to accept requests" latency → send first message → confirm response time acceptable

---

### C2 — Background Server / Daemon

**Why:** JARVIS should always be running. The user shouldn't think about starting it.

**Tasks:**

1. Implement daemon mode:
   - `jarvis --daemon` or `jarvis &` starts background server
   - `jarvis` (no args) reconnects to running server
   - macOS launchd plist for auto-start on login
2. Add menubar integration (uses existing `os/menubar.py`):
   - Menubar icon shows server status
   - Quick actions: Open Dashboard, Settings, Stop, Restart
3. Add system tray notifications for important events

**Dependencies:** C1 (instant startup)
**Effort:** 4 hours
**Risks:** Low
**Success Criteria:** `jarvis` starts server in background. Menubar icon appears. Closing terminal doesn't stop server. Second `jarvis` reconnects.
**Verification:** Open terminal → `jarvis` → close terminal → open new terminal → `jarvis` → see "connected to running server"

---

### C3 — Crash Recovery & Restart Resume

**Why:** If JARVIS crashes, the user should not lose state. Missions, memory, and ongoing operations should survive.

**Tasks:**

1. **Process supervision:**
   - Auto-restart on crash (launchd / systemd / simple watchdog)
   - Graceful shutdown on SIGTERM
2. **State persistence:**
   - Mission state in SQLite (from B2)
   - Session state persisted on each message
   - Checkpoint auto-save at mission stage boundaries (from A4)
3. **Restart detection:**
   - On startup, detect incomplete missions
   - Prompt user: "Resume mission X?"
   - Or auto-resume based on preference
4. **Graceful degradation:**
   - If LLM unavailable → offer offline mode with local model fallback
   - If browser crashes → retry with circuit breaker
   - If database corrupt → restore from checkpoint

**Dependencies:** A4 (checkpoints, health monitoring), B2 (mission unification), C1 (startup)
**Effort:** 6 hours
**Risks:** Low — builds on existing checkpoint infrastructure
**Success Criteria:** Kill server → restart → incomplete missions detected → resume works → no data loss
**Verification:** Start mission → `kill -9` server process → restart → confirm "resume mission" prompt → resume → verify mission state intact

---

## Phase D — Living Projects

> **Goal:** Projects become living entities that continuously evolve. Each project stores vision, goals, architecture, progress, confidence, momentum, risks, research, documentation, and autonomously suggests next actions.

### D1 — Project Data Model

**Why:** Current `projects/` (orphan) and `workspace/` have no concept of a persistent, evolving project. This is the core of the v9 vision.

**Tasks:**

1. Design the Living Project data model:
   - Identity: name, id, created, last_active
   - Vision: mission statement, goals, success criteria
   - State: roadmap, milestones, progress %, confidence score, momentum
   - Knowledge: architecture docs, decisions, research, meeting notes, ideas
   - Health: risks, technical debt, code quality, suggested next actions
   - Timeline: completed work, remaining work, dependencies
2. Store in SQLite (not JSON files) with versioned schema
3. Create `jarvis/projects/project_manager.py` as the single owner

**Dependencies:** B2 (mission/workspace unification — project is the higher-level container)
**Effort:** 6 hours
**Risks:** Low — greenfield design
**Success Criteria:** Create project → set vision → add goals → update progress → query confidence → suggest next action. All persisted across restart.
**Verification:** API: create/read/update/list projects → restart → confirm persistence → update confidence → confirm momentum calculated

---

### D2 — Autonomous Project Updates

**Why:** Projects should not require manual maintenance. After each completed task, JARVIS should automatically update progress, confidence, and suggest next steps.

**Tasks:**

1. Wire project manager into mission pipeline:
   - On mission complete → update project progress
   - On stage complete → recalculate confidence score
   - Periodically: review open questions, suggest next tasks
2. Add autonomous research integration:
   - When project is idle: search GitHub, docs, for relevant updates
   - Auto-organize discoveries into project knowledge
   - Flag important findings for user review (never interrupt unnecessarily)
3. Create project health dashboard endpoint

**Dependencies:** D1 (data model), B2 (mission integration)
**Effort:** 6 hours
**Risks:** Medium — autonomous research could be noisy. Must have clear source attribution and confidence signaling.
**Success Criteria:** Complete a mission → project automatically updates progress, recalculates confidence, suggests next task. Idle project: research runs, discoveries are queued for user review.
**Verification:** Create project with mission → execute mission → verify project.state updated → wait for research cycle → verify discoveries recorded

---

## Phase E — Apple-Level UI/UX

> **Goal:** Complete frontend redesign based on cognitive load, motion psychology, and Apple HIG. The interface should feel calm, not cluttered. The Golden Core is the identity — everything else may evolve.

### E1 — Design System & Psychology Research

**Why:** The vision demands software that "feels like Apple." This requires intentional study of design principles, not cosmetic changes.

**Tasks:**

1. Research and document:
   - Apple Human Interface Guidelines
   - Apple Design Principles (deference, clarity, depth)
   - Cognitive load theory for interface design
   - Visual scanning patterns (F-pattern, Z-pattern)
   - Motion psychology (timing, easing, purpose)
   - Information density and white space
   - Typography hierarchy and readability
   - Color psychology and accessibility
2. Create design token system (variables, not the dead `design-tokens.css`):
   - Colors: semantic palette (not product-named)
   - Typography: type scale, weight, leading
   - Spacing: 4px/8px grid system
   - Motion: duration, easing curves
   - Shadows: elevation system
   - Dark mode first, light mode as variant
3. Create component library in `web/static/js/components/`:
   - Card, Button, Input, Modal, Toggle, Dropdown, Badge, Toast
   - All accessible (WCAG 2.2 AA minimum)
   - All responsive

**Dependencies:** A1 (remove dead CSS/JS — clean slate for redesign)
**Effort:** 10 hours (research + implementation)
**Risks:** Low — additive, doesn't break existing UI until we swap templates
**Success Criteria:** Design token system is documented and used by all new components. Component library handles hover/focus/active/disabled/error states. Color palette meets WCAG AA contrast.
**Verification:** Visual review of each component in dark/light mode → axe-core accessibility audit → contrast ratio check

---

### E2 — Dashboard Redesign

**Why:** The current `base.html` SPA serves 3 routes with inconsistent visual treatment. The v9 dashboard should be the home screen of the operating system.

**Tasks:**

1. **Redesign the home page** (`/`):
   - Golden Core prominently displayed (non-negotiable)
   - Command palette (⌘K) accessible immediately
   - Intelligent suggestions based on context
   - Visual state: idle, listening, thinking, speaking, working
   - Weather/date/time greeting
   - Most recent project or memory shown
2. **Redesign the dashboard** (`/dashboard`):
   - Workspace view: active missions, project status, system health
   - Agent hierarchy shown as elegant card-suit visualization
   - Memory view: recent episodes, personal facts, journal
   - Settings accessible but not prominent
3. **Refactor `app.js`** — Remove 16 dead functions, clean event listener accumulation
4. **Replace 5 dead CSS files** with the new design token system (single `style.css`)
5. **Consolidate JS modules** — Keep 16 active files, remove 4 dead, deduplicate `graph3d.js`

**Dependencies:** E1 (design system)
**Effort:** 16 hours
**Risks:** Medium — redesign touches every frontend file. Must preserve all existing functionality.
**Success Criteria:** Home page renders with Golden Core. All existing features work (chat, agents, memory, workspace). Console has zero errors. Lighthouse performance score ≥ 90.
**Verification:** Browse every route → test every feature (chat, voice, memory, agents, computer control, settings) → check console → Lighthouse audit

---

### E3 — Motion & Animation System

**Why:** Purposeful motion makes software feel alive. The vision requires understanding motion psychology, not decoration.

**Tasks:**

1. Design motion language:
   - Transitions: fade, slide, scale (purpose-driven)
   - Micro-interactions: button press, toggle, hover
   - Loading: skeleton screens, progress indication
   - State transitions: idle → thinking → responding
2. Implement using CSS transitions + Web Animations API:
   - No heavy animation library — native performance
   - 60 FPS target (use `will-change`, `transform`, `opacity` only)
   - Respect `prefers-reduced-motion`
3. Animate the Golden Core transitions:
   - State changes: idle glow → active pulse → thinking orbit
   - Sync with audio visualization when voice is active

**Dependencies:** E2 (dashboard — the canvas for motion)
**Effort:** 8 hours
**Risks:** Low — additive, progressive enhancement
**Success Criteria:** All interactions have purposeful motion. 60 FPS on integrated GPU. `prefers-reduced-motion` disables all animations.
**Verification:** Profile with Chrome DevTools Performance tab → verify 60 FPS → enable reduced motion → confirm motion disabled

---

## Phase F — Daily Intelligence

> **Goal:** JARVIS provides a morning briefing, daily summaries, and continuous intelligence. Voice narration + beautiful visual cards. Everything has a source.

### F1 — Morning Briefing System

**Why:** The vision: "When I arrive home, JARVIS should ask: 'Would you like today's briefing?'" This is the flagship intelligence feature.

**Tasks:**

1. Create `jarvis/intelligence/briefing.py`:
   - Gather: weather (API), calendar (iCal), unread email (IMAP/Gmail API), news (RSS), project status, research discoveries, system health
   - Score importance per item
   - Generate natural language summary
   - Generate visual card data (title, summary, source, action link)
2. Create briefing API endpoint: `GET /api/intelligence/briefing`
3. Create briefing frontend component:
   - Beautiful visual cards with source attribution
   - Click to expand for details
   - Voice narration using existing TTS
   - "Good morning" greeting with user name
4. Create trigger conditions:
   - On JARVIS startup (if not seen in 8+ hours)
   - On user command: "briefing" or "what's new"
   - Scheduled: daily at configurable time

**Dependencies:** C1 (instant startup — briefing can be deferred), D2 (project status)
**Effort:** 10 hours
**Risks:** Medium — third-party API integrations (weather, calendar, email) need auth and graceful failure
**Success Criteria:** "Good morning, Brian" greeting. Weather, calendar events, news, project status, and research discoveries shown as cards. Voice reads summary. Each card has a source link.
**Verification:** Start JARVIS after 8+ hours → auto-trigger briefing → verify all sections populated → click cards → verify detail views

---

### F2 — Continuous Intelligence

**Why:** Beyond the morning briefing, JARVIS should provide intelligence throughout the day.

**Tasks:**

1. **Daily summary** — End-of-day summary of what was accomplished:
   - Missions completed
   - Projects progressed
   - New research discovered
   - System health report
2. **Project alerts** — When project conditions change:
   - New dependency available
   - Security vulnerability found
   - Architecture concern detected
   - Suggested next task ready
3. **Intelligence feed** — Scrollable feed of intelligence cards:
   - Filterable by type (project, research, system, calendar)
   - Searchable
   - Notification-aware (don't show already-seen items twice)

**Dependencies:** F1 (briefing infrastructure), D2 (autonomous research)
**Effort:** 6 hours
**Risks:** Low — builds on briefing infrastructure
**Success Criteria:** Daily summary generates at end of day. Project alerts appear when conditions change. Intelligence feed shows all items with read/unread state.
**Verification:** Complete missions → check daily summary → trigger project condition → verify alert appears → mark as read → verify doesn't reappear

---

## Phase G — Architecture Profiles

> **Goal:** Users can switch between orchestration strategies (Native, Hermes, Coding, Research, Planning, Experimental) through Settings without changing the rest of the system.

### G1 — Architecture Profile Maturation

**Why:** The existing `architectures/` system has two implementations (Native + Hermes) but both are incomplete. Rather than removing it (as the initial Phase 0 plan suggested), mature it into the vision's architecture profile system.

**Tasks:**

1. Keep and simplify the architecture registry
2. Define profile interface:
   - `strengths: list[str]`
   - `weaknesses: list[str]`
   - `recommended_use_cases: list[str]`
   - `orchestrate(mission) -> Pipeline` — the core dispatch method
3. Mature Native architecture (default):
   - Card-suit king/worker dispatch (already works)
   - DAG-based mission execution
   - Memory-aware context building
4. Build Hermes profile as optional alternative:
   - Simplified agent hierarchy
   - Different memory prioritization
   - Experimental features flagged
5. Wire architecture selection into Settings UI:
   - Dropdown in Settings
   - Per-project architecture override
   - Architecture shows strengths/weaknesses in UI

**Dependencies:** B2 (mission pipeline — architecture outputs missions)
**Effort:** 8 hours
**Risks:** Low — the architecture abstraction already exists, just needs completion
**Success Criteria:** Switch architecture in Settings → start mission → confirm different orchestration behavior → switch back → confirm Native behavior restored
**Verification:** Set architecture in Settings → run same prompt under Native vs Hermes → observe different agent dispatch → verify both complete correctly

---

## Phase H — Polish

> **Goal:** Performance, accessibility, documentation, and final quality gates. v9.0.0 release.

### H1 — Performance Optimization

**Tasks:**
- Profile startup time (target: CLI < 1s, server < 2s)
- Profile memory usage (target: < 200MB idle)
- Profile API latency (target: p95 < 100ms for non-LLM endpoints)
- Add battery-aware mode (reduce polling, animation quality, background ops)
- Lazy-load every non-essential module
- Optimize WebSocket traffic (batch events, compress)
- Add caching layer for repeated queries

### H2 — Accessibility

**Tasks:**
- WCAG 2.2 AA audit of every page
- Keyboard navigation for all features
- Screen reader support (ARIA labels, live regions)
- Focus management (modal traps, skip links)
- Color contrast verification
- Reduced motion support
- Text sizing support

### H3 — Security Hardening

**Tasks:**
- Input validation audit across all 16 routers
- SQL injection audit (parameterized queries already used, verify)
- Path traversal audit for file operations
- CORS configuration review
- Rate limiting audit
- Dependency vulnerability scan
- Permission bypass audit

### H4 — Documentation & Release

**Tasks:**
- Update README to v9.0.0
- Complete API reference documentation
- Architecture documentation reflecting consolidated systems
- User guide: how to use JARVIS as a daily OS
- Developer guide: how to extend JARVIS
- CHANGELOG for v9.0.0
- Release checklist (build → test → document → version → tag)

---

## Summary: Phase Dependencies

```
Phase A (Foundation)
  ├── A1 Dead Code Removal ────────────────── (independent)
  ├── A2 Structured Logging ───────────────── (independent)
  ├── A3 Permission System ───────────────── (independent)
  └── A4 Reliability ─────────────────────── (needs A2)
      └── A5 Testing ─────────────────────── (needs A1-A4)

Phase B (Core Architecture)
  ├── B1 Memory Unification ──────────────── (needs A1)
  ├── B2 Mission/Workspace Unification ───── (needs A4)
  └── B3 Tool Unification ────────────────── (needs A2, A4)

Phase C (Daily Driver)
  ├── C1 Instant Startup ─────────────────── (needs A2, A4)
  ├── C2 Background Server ───────────────── (needs C1)
  └── C3 Crash Recovery ──────────────────── (needs A4, B2, C1)

Phase D (Living Projects)
  ├── D1 Project Data Model ──────────────── (needs B2)
  └── D2 Autonomous Updates ──────────────── (needs D1, B2)

Phase E (Apple-Level UI/UX)
  ├── E1 Design System ───────────────────── (needs A1)
  ├── E2 Dashboard Redesign ──────────────── (needs E1)
  └── E3 Motion System ───────────────────── (needs E2)

Phase F (Daily Intelligence)
  ├── F1 Morning Briefing ────────────────── (needs C1, D2)
  └── F2 Continuous Intelligence ─────────── (needs F1, D2)

Phase G (Architecture Profiles)
  └── G1 Profile Maturation ──────────────── (needs B2)

Phase H (Polish)
  ├── H1 Performance ─────────────────────── (needs all above)
  ├── H2 Accessibility ───────────────────── (needs E2)
  ├── H3 Security ────────────────────────── (needs A3)
  └── H4 Documentation ──────────────────── (needs everything)
```

---

## Recommended Execution Order (Gantt)

```
Week 1-2:  A1 ───────────────────  ████████░░░░░░░░░░░░░░░░░░░░
           A2 ───────────────────  ████████░░░░░░░░░░░░░░░░░░░░
           A3 ───────────────────  ████████████░░░░░░░░░░░░░░░░░
           A4 ───────────────────  ░░████████████░░░░░░░░░░░░░░░
           A5 ───────────────────  ░░░░░░████████░░░░░░░░░░░░░░

Week 3-4:  B1 ───────────────────  ░░░░░░░░░░████░░░░░░░░░░░░░░
           B2 ───────────────────  ░░░░░░░░░░██████░░░░░░░░░░░░
           B3 ───────────────────  ░░░░░░░░░░░░██████░░░░░░░░░░
           C1 ───────────────────  ░░░░░░░░░░░░░░████████░░░░░░
           C2 ───────────────────  ░░░░░░░░░░░░░░░░████░░░░░░░░
           C3 ───────────────────  ░░░░░░░░░░░░░░░░░█████░░░░░░

Week 5-6:  D1 ───────────────────  ░░░░░░░░░░░░░░░░░░██████░░░░
           D2 ───────────────────  ░░░░░░░░░░░░░░░░░░░██████░░░░
           E1 ───────────────────  ░░░░░░░░░░░░░░░░░░░░████░░░░
           E2 ───────────────────  ░░░░░░░░░░░░░░░░░░░░░███████

Week 7-8:  E3 ───────────────────  ░░░░░░░░░░░░░░░░░░░░░░░░████
           F1 ───────────────────  ░░░░░░░░░░░░░░░░░░░░░░░░████
           F2 ───────────────────  ░░░░░░░░░░░░░░░░░░░░░░░░░░██
           G1 ───────────────────  ░░░░░░░░░░░░░░░░░░░░░░░░░░██

Week 9-10: H1-H4 ────────────────  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░████████
           Release v9.0.0 ───────  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░████
```

---

## Verification Gates (Phase Exit Criteria)

Each phase must pass its gate before the next phase begins:

### Gate A — Foundation Complete
- [ ] Zero orphan packages in `jarvis/`
- [ ] All code logs through centralized structured logger
- [ ] Permission system: tri-state for 12 capabilities, UI settings work
- [ ] Circuit breakers implemented for LLM, browser, vision, computer
- [ ] Continuous health monitor running, accessible via API
- [ ] Checkpoints have integrity verification
- [ ] Test suite runs with ≥60% coverage
- [ ] Server starts without errors

### Gate B — Architecture Clean
- [ ] One memory system (no knowledge/ duplicate)
- [ ] One mission/workspace system (SQLite-backed)
- [ ] One tool system (no agents/tools.py)
- [ ] All worker tool syntax unified
- [ ] No circular imports between core modules

### Gate C — Daily Ready
- [ ] `jarvis` returns control within 1 second
- [ ] Server accepts requests within 2 seconds
- [ ] Voice works on first request
- [ ] Server auto-restarts on crash
- [ ] Incomplete missions survive restart with resume prompt
- [ ] Graceful degradation for LLM/browser/database failures

### Gate D — Living Projects
- [ ] Create/read/update/list projects via API
- [ ] Projects auto-update on mission completion
- [ ] Confidence score and momentum calculated
- [ ] Autonomous research runs and queues discoveries

### Gate E — UI/UX Complete
- [ ] Design token system documented and applied
- [ ] Component library implemented (all states)
- [ ] Home page with Golden Core
- [ ] Dashboard with all features
- [ ] No console errors
- [ ] Lighthouse performance ≥ 90
- [ ] WCAG 2.2 AA on all pages

### Gate F — Intelligence
- [ ] Morning briefing generates with weather/calendar/news/projects
- [ ] Voice narration works
- [ ] Interactive cards with source attribution
- [ ] Daily summary generates
- [ ] Project alerts fire correctly

### Gate G — Architecture Profiles
- [ ] Native profile works as default
- [ ] Switching profiles in Settings changes orchestration
- [ ] Architecture shows strengths/weaknesses in UI

### Gate H — Release Ready
- [ ] All performance targets met
- [ ] Accessibility audit passes
- [ ] Security audit passes
- [ ] README, API docs, user guide, dev guide updated
- [ ] Version bumped to 9.0.0
- [ ] Release tagged

---

## Risk Register

| Risk | Phase | Likelihood | Impact | Mitigation |
|------|-------|-----------|--------|------------|
| Permission system breaks existing computer/browser actions | A3 | Medium | High | Thorough testing of each capability. Feature flags for migration. |
| Lazy LLM introduces first-message latency | C1 | Medium | Medium | Show "connecting..." state. Warm up in background on startup. |
| Architecture profile swappability is harder than expected | G1 | High | Medium | Start with Native only. Make the interface clean but defer Hermes. |
| Living Projects concept is too vague to implement | D1 | Medium | High | Start with concrete data model. Validate with real mission data. |
| Dashboard redesign breaks user workflows | E2 | Medium | High | Run old/new in parallel. Feature-flag the redesign. Allow fallback. |
| Morning Briefing requires too many API integrations | F1 | High | Low | Use public APIs only. Cache aggressively. Graceful degradation per source. |
| Autonomous research generates noise | D2 | High | Medium | Always ask before surfacing. Confidence-threshold filtering. |
| Scope creep delays v9.0.0 release | All | High | High | Phases are sequential with strict gates. No gate = no next phase. |

---

## Architecture Decisions Log

### AD-1: One logging framework (stdlib)
**Decision:** Standardize on stdlib `logging` with structured JSON format. Remove `loguru`.
**Rationale:** `loguru` is used in only 14 of 68 modules. Adding a dependency for 20% usage is not worth it. Stdlib is zero-dependency, well-understood, and compatible with all cloud logging platforms.
**Tradeoff:** Loses loguru's nicer API (`.bind()`, `.opt()`). Mitigated by structured JSON formatter.

### AD-2: Trinary permission as overlay on risk engine
**Decision:** Add tri-state (allow/ask/deny) as the outer permission gate. Keep `computer/permissions.py` and `browser/security.py` risk engines as the inner gate (what level of confirmation/notification).
**Rationale:** The existing risk engines are well-designed. Users want per-capability policies, not per-action. The tri-state layer provides the user-facing policy, the risk engine handles the action-level nuance.
**Tradeoff:** Two permission checks per action. The risk engine check is cheap (in-memory).

### AD-3: SQLite for project/checkpoint persistence (not JSON files)
**Decision:** Migrate mission state, checkpoint index, and project data from JSON files to SQLite.
**Rationale:** JSON files are not transactional, not queryable, and prone to corruption. SQLite provides ACID, easy querying, and migration path.
**Tradeoff:** More complex setup. But SQLite is already the database layer — no new dependency.

### AD-4: Native architecture first, Hermes deferred
**Decision:** The Native (card-suit king/worker) architecture is the default. Hermes is built only after Native is stable.
**Rationale:** The card-suit hierarchy is genuinely innovative and already works. Hermes is incomplete with no clear benefit proven. Ship what works.
**Tradeoff:** Architecture profiles won't be fully tested until post-v9.0.0 if Hermes is deferred to v9.1.

### AD-5: Golden Core preserved, dashboard redesigned around it
**Decision:** The 3D neural core (`graph-3d.js` + `jarvis-core.js`) is the visual centerpiece. The dashboard reflow treats it as the primary visual element.
**Rationale:** The Golden Core is the identity. Removing or de-emphasizing it betrays the JARVIS brand.
**Tradeoff:** Design flexibility is constrained by the Core's visual requirements. This is intentional.

---

## Final Note

This roadmap replaces `PHASE0_PLAN.md` as the authoritative execution plan.

The old Phase 0 (cleanup) is absorbed into Phase A (Foundation) — but with the mindset shift from "deleting dead code" to "building a stable base."

Every phase ends with a usable, stable system. At any point, shipping what's built is better than shipping nothing.

The goal is not perfection. The goal is a Personal AI Operating System that someone can install, type `jarvis`, and immediately feel like they're using software that was designed — not assembled.
