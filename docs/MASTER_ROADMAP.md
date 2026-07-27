# JARVIS — Master Roadmap & Long-Term Vision

> **Single source of truth for the future of JARVIS.**
> This document is maintained automatically after every release.
> Last updated: v8.0.0

---

## Table of Contents

1. [Project Vision](#1--project-vision)
2. [Core Principles](#2--core-principles)
3. [Current Architecture](#3--current-architecture)
4. [Module Reference](#4--module-reference)
5. [Version History](#5--version-history)
6. [Future Roadmap](#6--future-roadmap)
7. [Design Philosophy](#7--design-philosophy)
8. [Animation Philosophy](#8--animation-philosophy)
9. [Engineering Principles](#9--engineering-principles)
10. [Security Philosophy](#10--security-philosophy)
11. [Testing Philosophy](#11--testing-philosophy)
12. [Coding Standards](#12--coding-standards)
13. [Documentation Standards](#13--documentation-standards)
14. [Performance Goals](#14--performance-goals)
15. [Long-Term Vision](#15--long-term-vision)
16. [Technical Debt](#16--technical-debt)
17. [Known Issues](#17--known-issues)
18. [Future Milestones](#18--future-milestones)

---

## 1 — Project Vision

### What is JARVIS?

JARVIS is **not a chatbot**.

JARVIS is a **personal AI operating system** — a unified platform that combines multi-agent intelligence, long-term memory, autonomous execution, computer control, and engineering tools into a single coherent system.

The name stands for something larger than any single feature. JARVIS is the convergence of:

- **Intelligence** — Multi-agent architecture with specialized workers
- **Memory** — Episodic, working, personal, and graph-based memory systems
- **Autonomy** — Self-directed mission execution with verification
- **Control** — Computer, browser, IoT, and voice interaction
- **Trust** — Transparent tool execution with evidence-based results

### Identity

JARVIS is a **premium personal AI operating system**.

Every decision must improve one or more of these:

- Trust
- Reliability
- Usability
- Beauty
- Speed
- Consistency
- Intelligence
- Transparency

Do NOT optimize for feature count. Optimize for daily usability.

---

## 2 — Core Principles

### Design Principles

1. **Clarity** — Every element has a purpose
2. **Deference** — Content is the focus, not chrome
3. **Depth** — Visual hierarchy through layering
4. **Simplicity** — Complexity hidden, not removed
5. **Consistency** — Same patterns everywhere
6. **Meaningful Animation** — Every motion communicates state
7. **Immediate Feedback** — Every action has a visible response
8. **User Confidence** — The system feels reliable and predictable

### Engineering Principles

1. **Evidence First** — Never claim success without verification
2. **Fail Gracefully** — Every error has a recovery path
3. **Async by Default** — Never block the event loop
4. **Defensive Coding** — Assume everything can fail
5. **Structured Data** — Every tool returns typed results
6. **Observable** — Every action is logged and traceable
7. **Secure** — Defense in depth, least privilege
8. **Testable** — Every feature has a test path

### The Golden Rule

> **The Golden 3D Neural Core must remain and never be removed.**

It is the heart of JARVIS. Never remove it again. Instead, improve it.

---

## 3 — Current Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    JARVIS Web Interface                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │  Home   │  │  Chat   │  │ Memory  │  │Projects │ ...   │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘       │
│       │            │            │            │              │
│  ┌────┴────────────┴────────────┴────────────┴────┐        │
│  │              FastAPI Router Layer               │        │
│  │  /api/chat  /api/memory  /api/workspace  ...   │        │
│  └────────────────────┬───────────────────────────┘        │
│                       │                                     │
│  ┌────────────────────┴───────────────────────────┐        │
│  │              Brain Core (LLM + Agents)          │        │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐      │        │
│  │  │ King │  │ King │  │ King │  │ King │      │        │
│  │  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘      │        │
│  │     │         │         │         │            │        │
│  │  ┌──┴───┐  ┌──┴───┐  ┌──┴───┐  ┌──┴───┐      │        │
│  │  │Worker│  │Worker│  │Worker│  │Worker│      │        │
│  │  └──────┘  └──────┘  └──────┘  └──────┘      │        │
│  └────────────────────────────────────────────────┘        │
│                                                             │
│  ┌────────────────────────────────────────────────┐        │
│  │              Memory Systems                     │        │
│  │  Working │ Episodic │ Personal │ Graph │ RAG   │        │
│  └────────────────────────────────────────────────┘        │
│                                                             │
│  ┌────────────────────────────────────────────────┐        │
│  │              Tool Layer                         │        │
│  │  Browser │ Terminal │ Vision │ Voice │ IoT     │        │
│  └────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.9.6+, FastAPI, uvicorn |
| Database | SQLite (aiosqlite, WAL mode) |
| LLM | NVIDIA API (Llama 3.1), OpenAI-compatible |
| Frontend | Vanilla JS (no build tools), HTML5, CSS3 |
| 3D | Three.js (Neural Core, Knowledge Graph, Memory Galaxy) |
| Voice | Kokoro TTS, Whisper STT |
| WebSocket | Native WebSocket API |

### Key Metrics

| Metric | Value |
|--------|-------|
| Python files | 346 |
| JavaScript files | 25 custom + 7 vendor |
| CSS files | 2 (4,686 lines) |
| HTML templates | 7 |
| API endpoints | 223 (222 HTTP + 1 WebSocket) |
| Test files | 42 |
| Test lines | 12,677 |
| Total codebase | ~50,000+ lines |

---

## 4 — Module Reference

### Core (`jarvis/core/`)

| Module | Purpose | Lines |
|--------|---------|-------|
| database.py | Async SQLite with WAL mode | 938 |
| capabilities.py | Capability registry and prompts | 273 |
| reliability.py | Timeout, retry, backoff patterns | 242 |
| events.py | Event bus for cross-component messaging | 214 |
| models.py | Pydantic data models | 195 |
| diagnostics.py | System health diagnostics | 191 |
| workflows.py | Workflow orchestration | 159 |
| permissions.py | Permission system | 123 |
| config.py | Configuration management | 104 |

### Brain (`jarvis/brain/`)

| Module | Purpose | Lines |
|--------|---------|-------|
| llm.py | Async LLM interface (achat, achat_stream) | 571 |
| mission_executor.py | Mission planning and execution | 332 |
| dag_planner.py | DAG-based task planning | 320 |
| model_router.py | Model selection and routing | 275 |
| aci.py | Agent Communication Interface | 261 |
| skills.py | Skill management | 154 |
| world_model.py | Digital twin / world understanding | 197 |

### Memory (`jarvis/brain/memory/`)

| Module | Purpose | Lines |
|--------|---------|-------|
| retrieval.py | Memory retrieval and ranking | 421 |
| episodic.py | Episode storage and recall | 393 |
| consolidation.py | Memory consolidation (short→long) | 340 |
| working.py | Working memory (active context) | 318 |
| journal.py | Daily journal system | 309 |
| personal.py | Personal facts and preferences | 300 |
| graph.py | Knowledge graph (custom, NOT codebase-memory-mcp) | 234 |
| importance.py | Memory importance scoring | 202 |
| extractor.py | Memory extraction from text | 159 |

### Web (`jarvis/web/`)

| Module | Purpose | Lines |
|--------|---------|-------|
| main.py | App factory, middleware, lifespan | 304 |
| routers/system.py | System/brain/graph API (mega-router) | 1,013 |
| routers/voice.py | Voice/TTS/STT/clone API | 474 |
| routers/websocket.py | WebSocket agent status stream | 360 |
| routers/engineering.py | Hardware engineering tools | 318 |
| routers/memory.py | Memory system API | 282 |
| routers/chat.py | Chat and session management | 249 |
| routers/workspace.py | Workspace/mission tracking | 190 |
| routers/security.py | Security/vault API | 189 |

### Frontend (`jarvis/web/static/`)

| File | Purpose | Lines |
|------|---------|-------|
| js/app.js | Main application logic | 2,354 |
| js/graph-3d.js | 3D knowledge graph visualization | 994 |
| js/command-map.js | Command center visualization | 985 |
| js/unified-timeline.js | Mission timeline rendering | 749 |
| js/living-interface.js | AI presence and living UI | 417 |
| js/knowledge-graph.js | Knowledge graph UI | 414 |
| js/memory-galaxy.js | Memory visualization | 347 |
| css/style.css | Main design system | 4,136 |
| css/command-map.css | Command center styles | 550 |

---

## 5 — Version History

### v8.0.0 — Production Readiness Overhaul

> Stability, Reliability, Real usefulness, Premium UI/UX — the quality gate.

**Phase 1 — Security:**
- Created `jarvis/web/auth.py` with AuthManager + AuthMiddleware
- Token-based auth (API key in header, session cookie for web UI)
- Localhost auto-trusted, login/logout/status/api-key endpoints
- Session persistence with 24-hour expiry

**Phase 2 — Stability:**
- CSS cleanup: 121 lines of duplicate selectors removed
- Deduplicated computer-card, project-card, metric-card, scrollbar CSS

**Phase 3 — Reliability:**
- Created `jarvis/core/checkpoint.py` with CheckpointManager
- File checkpoints (before/after snapshots), mission checkpoints, undo/restore
- Created `jarvis/web/routers/checkpoints.py` with 6 API endpoints
- Added context compaction (`_compact_context`) to LLM class
- Added permission GET/POST API endpoints

**Phase 4 — UI/UX:**
- Tool card CSS: expandable cards with name, status, duration, output preview
- Task status indicators: visual progress for long-running operations
- Empty state styling: elegant fallbacks when data is unavailable
- JS functions: `createToolCard`, `toggleToolCard`, `updateToolCard`, `createTaskStatus`, `updateTaskStatus`

**Phase 5 — Performance:**
- Async TTS: `agenerate()` method on VoiceEngine with `asyncio.to_thread`
- Chat endpoint now uses non-blocking TTS generation

**Phase 6 — Testing:**
- 13 tests passing for auth, checkpoint, permission systems
- Test file: `tests/test_v8_core.py`

**Overall Score:** 5.2 → 6.2/10 (target: 8.0)

### v7.9.1 — Bug Fixes + Projects Button

> Session management fixes and new project creation.

- Added `POST /api/chat/sessions` endpoint for creating new sessions
- Added `startNewChat()` function (was undefined, called by command palette)
- Wired `new-chat-btn` click handler in chat sidebar
- Added "New Project" button to Projects workspace header
- Fixed `loadProjects()` to handle both array and object API responses

### v7.9.0 — Settings Redesign + Chat Fix

> Two-column settings sidebar, chat input spacing fix.

- Settings overlay redesigned with two-column sidebar layout
- 6 navigation categories, search bar, toggle switches
- Collapsible voice sub-panels, responsive breakpoints
- Chat input pinned to viewport bottom (`position: fixed`)
- Added padding to chat messages container

### v7.8.0 — Command Palette + Digital Twin

> Keyboard-first navigation + persistent AI presence.

- Created `command-palette.js` with ⌘K fuzzy search
- Commands: navigate, chat, tools, system actions
- Keyboard navigation (↑↓ Enter Esc), category grouping
- Created `digital-twin.js` with state-driven mini avatar
- SVG energy ring with live drain/charge animation
- State pulse animations (thinking, speaking, listening)

### v7.7.0 — Workspace System

> Persistent per-workspace state with sessionStorage.

- Created `workspace-manager.js`
- Per-workspace state persistence (scroll, inputs, settings)
- SessionStorage hydration on workspace switch
- Hooked into `switchWorkspace()` lifecycle

### v7.6.0 — Premium Vision Experience

> Screen and camera capture with AI analysis.

- Created `vision-experience.js`
- Screen capture via getDisplayMedia
- Camera capture via getUserMedia
- Frame analysis via `/api/chat` endpoint
- Vision workspace (rebuilt from Computer)

### v7.5.0 — Mission Timeline + Tool Cards

> Visual execution tracking with expandable tool cards.

- Created `mission-timeline.js`
- Timeline panel in chat sidebar
- Tool card CSS with status indicators
- Wired `tool_calls` SSE to timeline rendering

### v7.4.0 — Premium Voice Experience

> Streaming STT/TTS with waveform visualization.

- Created `voice-experience.js`
- Streaming speech recognition
- Audio waveform visualization
- Voice state machine (idle, listening, thinking, speaking)

### v7.3.0 — Reliability Foundation

> Async LLM, async SQLite, logging overhaul.

- Async LLM (`achat()`, `achat_stream()`)
- Async SQLite (aiosqlite, WAL mode)
- Logging to 43+ silent `except: pass` handlers
- WebSocket consolidation (`ws-manager.js`)
- JS test infrastructure (Jest + `ws-manager.test.js`)

### v7.2.0 — UI Audit & Workspace Planning

> Comprehensive UX audit, workspace redesigns.

- Created `docs/UI_UX_AUDIT_v7.md` — scored current UI 4.3/10
- Redesigned all 6 workspaces to premium quality
- Research, Memory, Projects, Computer, Metrics, Logs

### v7.1.0 — Premium Chat Experience

> Collapsible thinking blocks, tool summaries, streaming.

- Collapsible thinking blocks
- Tool call summary footer
- Streaming token display
- Premium glass sidebar
- Background canvas animation

### v7.0.0 — Experience Revolution

> Foundation for premium OS experience.

- Unified navigation (Home, Chat, Memory, Projects, Settings)
- Premium glass design tokens
- Single chat experience
- AI presence (real system state messages)
- Loading screen with Golden Core
- Settings overlay

### v6.1.0 — System Integration & Engineering Workspace

> JARVIS becomes one unified operating system.

- Unified Workspace + Mission model
- Cross-Agent Collaboration
- Peer Context Passing
- Unified Mission Timeline
- Developer Dashboard
- Reliability Config
- LLM Retry with exponential backoff
- Workspace Search & Timeline APIs

---

## 6 — Future Roadmap

### Phase 1 — Security Hardening (v8.1)

> Authentication, authorization, and input validation.

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Auth middleware | Bearer token or API key on all `/api/` routes | Critical | ⬜ |
| CORS middleware | `CORSMiddleware` for cross-origin control | High | ⬜ |
| Input validation | Pydantic models for all `dict` body params | High | ⬜ |
| Path traversal fix | Validate file paths stay within allowed dirs | Critical | ⬜ |
| File size limits | Upload size caps on voice/engineering endpoints | High | ⬜ |
| HTTP status codes | Fix error-in-200-OK patterns | Medium | ⬜ |

### Phase 2 — Error Handling Overhaul (v8.2)

> Every endpoint has structured error handling.

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Global exception handler | `@app.exception_handler` for 500, 404, etc. | High | ⬜ |
| Per-endpoint try/except | Add to 120+ unprotected endpoints | High | ⬜ |
| Structured error responses | `{"error": "...", "code": "..."}` format | Medium | ⬜ |
| Frontend error toasts | Show API errors in UI, not silent catches | Medium | ⬜ |
| Request logging | Access logging with request IDs | Low | ⬜ |

### Phase 3 — Frontend Cleanup (v8.3)

> XSS prevention, accessibility, performance.

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| XSS sanitization | Add DOMPurify or escape all innerHTML | High | ⬜ |
| prefers-reduced-motion | Disable animations for motion-sensitive users | High | ⬜ |
| Focus management | Focus traps in modals, visible focus states | Medium | ⬜ |
| CSS variable bleed | Fix command-map.css :root override | Medium | ⬜ |
| transition:all → specific | Convert 35+ `transition: all` to specific properties | Medium | ⬜ |
| Responsive breakpoints | Add breakpoints for command-map, fix ordering | Low | ⬜ |

### Phase 4 — Performance Audit (v8.4)

> Memory leaks, layout shifts, startup time.

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Memory leak audit | Verify all setInterval/requestAnimationFrame cleanup | Medium | ⬜ |
| Layout shift audit | Add dimensions to images/skeletons | Medium | ⬜ |
| Startup time | Measure and optimize initial load | Medium | ⬜ |
| Bundle size | Audit JS payload (8,544 lines unminified) | Low | ⬜ |
| CSS modularization | Split 4,136-line style.css | Low | ⬜ |

### Phase 5 — system.py Decomposition (v8.5)

> Break the 1,013-line mega-router into focused modules.

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Split system.py | Create routers: graph.py, evolution.py, aci.py, dag.py, teams.py, demos.py, dev.py, graphify.py | High | ⬜ |
| Add Pydantic models | Replace raw `dict` params with typed models | High | ⬜ |
| Error handling | Add try/except to all new router endpoints | High | ⬜ |

### Phase 6 — Testing & Documentation (v8.6)

> Fill test gaps, update all documentation.

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| API integration tests | Test all 223 endpoints | High | ⬜ |
| Frontend component tests | Test JS components | Medium | ⬜ |
| Accessibility audit | WCAG 2.1 AA compliance check | Medium | ⬜ |
| UI_GUIDELINES.md | Design system documentation | Medium | ⬜ |
| ANIMATION_GUIDELINES.md | Motion principles and patterns | Low | ⬜ |
| SECURITY_REPORT.md | Updated after hardening | High | ⬜ |

### Phase 7 — Permission Center (v9.0)

> Complete permission system with profiles.

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Permission UI | Settings page with per-tool controls | High | ⬜ |
| Profiles | Safe, Balanced, Developer, Fully Autonomous | High | ⬜ |
| Import/Export | Permission profiles as JSON | Medium | ⬜ |
| Integration | Connect to ComputerManager, BrowserManager, Tool Layer | High | ⬜ |

### Phase 8 — Voice & Vision Polish (v9.1)

> Premium voice and vision experiences.

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Interruptible TTS | Stop speaking on user input | High | ⬜ |
| Voice Activity Detection | Auto-start/stop based on audio levels | Medium | ⬜ |
| OCR improvements | Better text recognition | Medium | ⬜ |
| Screenshot understanding | Before/after comparison | Medium | ⬜ |

---

## 7 — Design Philosophy

### Apple HIG Principles

The entire UI/UX must follow **Apple's Human Interface Guidelines**.

That DOES NOT mean copying Apple's appearance.

It means following Apple's principles:

- **Clarity** — Text is legible, icons are understandable, decorations are subtle
- **Deference** — The UI helps users focus on content, not chrome
- **Depth** — Visual layers and realistic motion convey hierarchy
- **Simplicity** — Every word, pixel, and feature earns its place
- **Consistency** — Same patterns, same behaviors, everywhere

### Visual Identity

- **Dark-first** — Deep blacks (#080c14) with cyan accent (#00dcff)
- **Glassmorphism** — `backdrop-filter: blur(40px) saturate(1.4)`
- **Golden 3D Neural Core** — Visual centerpiece, never removed
- **Premium typography** — Inter, SF Pro, system fonts
- **Meaningful icons** — SVG, consistent stroke width

### What JARVIS Should Feel Like

The user should immediately feel:

> "This feels like a real operating system."

Not a dashboard. Not an admin panel. Not a chatbot wrapper.

An **operating system** that happens to be powered by AI.

---

## 8 — Animation Philosophy

### Principles

1. **Purposeful** — Every animation communicates state
2. **Smooth** — 60fps minimum, spring easings
3. **Brief** — 200-400ms for most transitions
4. **Consistent** — Same timing for same type of action
5. **Respectful** — Honors `prefers-reduced-motion`

### Animation Taxonomy

| Type | Duration | Easing | Use Case |
|------|----------|--------|----------|
| Micro | 100-200ms | ease-out | Button press, toggle |
| Standard | 200-300ms | ease-in-out | Panel open, tab switch |
| Complex | 300-500ms | spring | Workspace transition |
| Emphasis | 400-700ms | spring(0.3) | Loading, state change |

### Custom Easings

```css
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
--ease-smooth: cubic-bezier(0.25, 0.1, 0.25, 1);
```

### The Neural Core

The Golden 3D Neural Core reacts to system state:

| State | Animation |
|-------|-----------|
| Idle | Slow pulse, gentle float |
| Thinking | Rapid pulse, particles flowing inward |
| Speaking | Rhythmic expansion, outward particles |
| Listening | Gentle rotation, microphone glow |
| Working | Orbits spinning, connections forming |
| Success | Green flash, particle burst |
| Error | Red pulse, contraction |
| Sleep | Slow breathing, dim glow |

---

## 9 — Engineering Principles

### Code Quality

- **Python 3.9.6+** — Type hints, async/await, f-strings
- **No global state** — Dependency injection where possible
- **Structured errors** — Custom exception classes
- **Logging** — Use `logging` module, never `print()` in production
- **Type safety** — Pydantic models for all API boundaries

### Async Patterns

```python
# Good: Async all the way down
async def handler():
    db = await get_db()
    result = await db.execute("SELECT ...")
    
# Bad: Blocking calls in async context
async def handler():
    result = subprocess.run(...)  # BLOCKS EVENT LOOP
```

### Error Handling

```python
# Good: Structured error response
@router.get("/items/{item_id}")
async def get_item(item_id: str):
    try:
        item = await db.get_item(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get item {item_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal error")

# Bad: Silent failure
@router.get("/items/{item_id}")
async def get_item(item_id: str):
    try:
        return await db.get_item(item_id)
    except Exception:
        pass  # WHAT WENT WRONG? WHO KNOWS!
```

### Tool Execution

Every tool must return structured data:

```python
{
    "success": True,
    "verified": True,
    "duration_ms": 847,
    "stdout": "...",
    "stderr": "",
    "exit_code": 0,
    "artifacts": ["file.txt"],
    "verification": "File exists at /path/to/file.txt"
}
```

The AI must never hallucinate success. If verification is impossible, state:

> "I could not verify the result."

---

## 10 — Security Philosophy

### Principles

1. **Defense in Depth** — Multiple layers of protection
2. **Least Privilege** — Minimum required permissions
3. **Zero Trust** — Verify everything, trust nothing
4. **Secure by Default** — Safe defaults, opt-in risk
5. **Transparent** — User can see and control all permissions

### Security Layers

```
┌─────────────────────────────────┐
│  Layer 1: Authentication        │  Who are you?
├─────────────────────────────────┤
│  Layer 2: Authorization         │  What can you do?
├─────────────────────────────────┤
│  Layer 3: Input Validation      │  Is this data safe?
├─────────────────────────────────┤
│  Layer 4: Rate Limiting         │  Are you overloading us?
├─────────────────────────────────┤
│  Layer 5: Output Sanitization   │  Is our response safe?
├─────────────────────────────────┤
│  Layer 6: Audit Logging         │  What did you do?
└─────────────────────────────────┘
```

### Current Status

| Layer | Status |
|-------|--------|
| Authentication | ❌ Missing |
| Authorization | ❌ Missing |
| Input Validation | ⚠️ Partial (Pydantic on some endpoints) |
| Rate Limiting | ✅ Global POST/PUT/PATCH limiter |
| Output Sanitization | ⚠️ Partial (some innerHTML unsanitized) |
| Audit Logging | ❌ Missing |

### Vault System

JARVIS includes an encrypted vault for secrets:

- AES-256-GCM encryption
- PBKDF2 key derivation
- Master password protection
- Secrets stored encrypted at rest

**Current Issue:** The vault is accessible without authentication. Anyone who can reach the server can create, unlock, or modify the vault.

---

## 11 — Testing Philosophy

### Principles

1. **Test What Matters** — Focus on critical paths
2. **Fast Feedback** — Tests should run in seconds
3. **Deterministic** — No flaky tests
4. **Readable** — Test names describe behavior
5. **Comprehensive** — Happy path, edge cases, errors

### Test Pyramid

```
        ╱╲
       ╱  ╲      E2E Tests (5%)
      ╱    ╲     - Full user workflows
     ╱──────╲
    ╱        ╲   Integration Tests (25%)
   ╱          ╲  - API endpoints, database
  ╱────────────╲
 ╱              ╲ Unit Tests (70%)
╱────────────────╲ - Business logic, utilities
```

### Current Coverage

| Area | Tests | Lines | Status |
|------|-------|-------|--------|
| Vision | 614 | test_vision.py | ✅ |
| Mission | 564 | test_mission.py | ✅ |
| Knowledge Graph | 551 | test_knowledge_graph.py | ✅ |
| Accessibility | 539 | test_accessibility.py | ✅ |
| Security | 521 | test_security.py | ✅ |
| WebSocket | JS | ws-manager.test.js | ✅ |
| **Total** | **42 files** | **12,677 lines** | ✅ |

---

## 12 — Coding Standards

### Python

- **Style**: PEP 8, enforced by `ruff`
- **Line length**: 100 characters max
- **Imports**: `isort` compatible grouping
- **Types**: Type hints on all function signatures
- **Docstrings**: Google style for public functions
- **Async**: `async def` for all I/O-bound functions

### JavaScript

- **Style**: Modern ES2020+, no transpilation
- **Modules**: `<script>` tags (no bundler)
- **DOM**: `querySelector` / `getElementById` with null checks
- **Async**: `async/await` for all fetch calls
- **Error handling**: Always catch, never silent swallow
- **Naming**: camelCase for variables/functions, PascalCase for classes

### CSS

- **Methodology**: BEM-inspired naming
- **Custom Properties**: All colors, spacing, timing via `--var`
- **Responsive**: Mobile-first with `min-width` breakpoints
- **Animations**: `transform` and `opacity` only (GPU-accelerated)
- **No `!important`**: Unless absolutely necessary (max 7 per file)

---

## 13 — Documentation Standards

### Required Documents

| Document | Purpose | Update Frequency |
|----------|---------|-----------------|
| MASTER_ROADMAP.md | Single source of truth | Every release |
| CHANGELOG.md | Version-by-version changes | Every release |
| SYSTEM_ARCHITECTURE.md | Technical architecture | Major versions |
| UI_GUIDELINES.md | Design system docs | Design changes |
| API_REFERENCE.md | Endpoint documentation | API changes |

### Code Documentation

- **Module docstrings**: Every `.py` file
- **Function docstrings**: All public functions
- **JSDoc comments**: Complex JS functions
- **CSS comments**: Section headers, non-obvious rules
- **Inline comments**: Why, not what

---

## 14 — Performance Goals

### Targets

| Metric | Target | Current |
|--------|--------|---------|
| First Contentful Paint | < 1.5s | Unknown |
| Largest Contentful Paint | < 2.5s | Unknown |
| Time to Interactive | < 3.5s | Unknown |
| Cumulative Layout Shift | < 0.1 | Unknown |
| API P95 Latency | < 500ms | Unknown |
| Memory Usage | < 200MB | Unknown |
| JS Bundle Size | < 500KB | ~200KB (unminified) |

### Measurement

- Chrome DevTools Performance tab
- Lighthouse audit
- `performance.mark()` / `performance.measure()` in JS
- Python `time.perf_counter()` for API timing

---

## 15 — Long-Term Vision

### Year 1: Personal AI OS

- [ ] Complete security hardening
- [ ] Permission center with profiles
- [ ] Voice and vision polish
- [ ] Performance optimization
- [ ] Mobile responsive

### Year 2: Autonomous Agent

- [ ] Long-running task execution
- [ ] Proactive suggestions
- [ ] Cross-session learning
- [ ] Multi-user support
- [ ] Plugin system

### Year 3: World Model

- [ ] Full digital twin
- [ ] Predictive modeling
- [ ] Cross-device orchestration
- [ ] Enterprise features
- [ ] API marketplace

---

## 16 — Technical Debt

### Critical

| Debt | Impact | Effort | Priority |
|------|--------|--------|----------|
| No authentication | Security vulnerability | High | P0 |
| system.py mega-router (1,013 lines) | Maintainability | Medium | P1 |
| 120+ endpoints missing error handling | Reliability | Medium | P1 |
| Version drift (__init__.py vs pyproject.toml) | Confusion | Low | P1 |

### High

| Debt | Impact | Effort | Priority |
|------|--------|--------|----------|
| Raw `dict` body params (25+ endpoints) | Type safety | Medium | P2 |
| `transition: all` overuse (35+) | Performance | Low | P2 |
| innerHTML without sanitization | XSS risk | Medium | P2 |
| No `prefers-reduced-motion` | Accessibility | Low | P2 |
| command-map.css `:root` bleed | Visual bugs | Low | P2 |
| Silent `catch (_) {}` blocks (13+) | Debugging | Low | P2 |

### Medium

| Debt | Impact | Effort | Priority |
|------|--------|--------|----------|
| No CORS middleware | Cross-origin issues | Low | P3 |
| Subprocess blocking in voice.py | Event loop blocking | Low | P3 |
| 4,136-line monolithic CSS | Maintainability | High | P3 |
| 2,354-line monolithic JS | Maintainability | High | P3 |
| No ES modules | Code organization | High | P3 |
| requirements.txt incomplete | Dependency confusion | Low | P3 |

---

## 17 — Known Issues

### Active Bugs

1. **Chat session 500 error** — `POST /api/chat/sessions/{id}` had no handler (fixed in v7.9.1)
2. **`startNewChat()` undefined** — Called by command palette but never defined (fixed in v7.9.1)
3. **Projects "New Project" button missing** — No way to create projects from UI (fixed in v7.9.1)
4. **Version drift** — `__init__.py` says 7.9.1, `pyproject.toml` says 6.4.2 (fixed in v8.0.0)

### Limitations

1. **No mobile responsive** — UI designed for desktop/large screens
2. **No dark/light toggle** — Dark-only by design (intentional)
3. **No offline support** — Requires server connection
4. **No multi-user** — Single-user system
5. **No plugin system** — All features built-in

---

## 18 — Future Milestones

### v8.1 — Security Hardening

**Target:** All endpoints authenticated, input validated, paths secured.

### v8.2 — Error Handling Overhaul

**Target:** Zero unhandled exceptions, structured error responses everywhere.

### v8.3 — Frontend Cleanup

**Target:** XSS-safe, accessible, performant.

### v8.4 — Performance Audit

**Target:** Sub-second load, smooth animations, low memory.

### v8.5 — system.py Decomposition

**Target:** Mega-router split into 8+ focused routers.

### v8.6 — Testing & Documentation

**Target:** All endpoints tested, all docs updated.

### v9.0 — Permission Center

**Target:** Complete permission system with profiles.

### v9.1 — Voice & Vision Polish

**Target:** Interruptible TTS, VAD, improved OCR.

---

## Quality Gate

Before considering any release complete, ask:

1. Would Apple ship this interaction?
2. Does this reduce friction?
3. Does this improve user trust?
4. Is the animation meaningful?
5. Is the UI consistent?
6. Is every successful action verified with evidence?
7. Can a new user understand this without documentation?
8. Does this feel like one operating system instead of many webpages?

If the answer to any question is "No", redesign it before shipping.
