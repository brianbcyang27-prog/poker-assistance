# JARVIS — Changelog

All notable changes to JARVIS will be documented in this file.

---

## v8.0.0 — Native Intelligence (2026-07-26)

Native launcher, premium UI redesign, polished AI operating system. See root CHANGELOG.md for full details.

---

## v8.0.0 — Production Readiness Overhaul (2026-07-26)

> Stability, Reliability, Real usefulness, Premium UI/UX — the quality gate.

### Security
- `jarvis/web/auth.py` — AuthManager + AuthMiddleware with token auth
- Session cookies for web UI, API key headers for programmatic access
- Localhost auto-trust, login/logout/status/api-key endpoints
- Session persistence with 24-hour expiry

### Stability
- CSS cleanup: 121 lines of duplicate selectors removed
- Deduplicated computer-card, project-card, metric-card, scrollbar CSS

### Reliability
- `jarvis/core/checkpoint.py` — CheckpointManager with file/mission checkpoints
- `jarvis/web/routers/checkpoints.py` — 6 API endpoints for checkpoint CRUD
- Context compaction (`_compact_context`) in LLM class
- Permission GET/POST API endpoints

### UI/UX
- Tool card CSS: expandable cards with name, status, duration, output preview
- Task status indicators: visual progress for long-running operations
- Empty state styling: elegant fallbacks when data is unavailable
- JS functions: `createToolCard`, `toggleToolCard`, `updateToolCard`, `createTaskStatus`

### Performance
- Async TTS: `agenerate()` method on VoiceEngine with `asyncio.to_thread`
- Chat endpoint now uses non-blocking TTS generation

### Testing
- 13 tests passing for auth, checkpoint, permission systems
- Test file: `tests/test_v8_core.py`

---

## v7.6.0 — Premium Vision Experience (2026-07-26)

> Screen and camera capture with AI analysis.

- Created `vision-experience.js`
- Screen capture via getDisplayMedia
- Camera capture via getUserMedia
- Frame analysis via `/api/chat` endpoint
- Vision workspace (rebuilt from Computer)
- Docs: COMPETITIVE_ANALYSIS.md, UI_UX_REVIEW.md, RELIABILITY_REVIEW.md

### Reliability Fixes (8 critical)
- `jarvis/computer/mouse.py` — `_run_subprocess()` with 10s timeout, `shlex.quote`
- `jarvis/brain/llm.py` — `_history_lock`, exception logging, fixed `close()`
- `jarvis/web/routers/chat.py` — 120s request timeout, SSE error handling
- `jarvis/web/routers/websocket.py` — Event bridge error callback, `_bridge_tasks` set
- `jarvis/mission/manager.py` — Atomic file writes (temp + rename)

---

## v7.5.0 — Mission Timeline + Tool Cards (2026-07-26)

> Visual execution tracking with expandable tool cards.

- Created `mission-timeline.js`
- Timeline panel in chat sidebar
- Tool card CSS with status indicators
- Wired `tool_calls` SSE to timeline rendering

---

## v7.4.0 — Premium Voice Experience (2026-07-26)

> Streaming STT/TTS with waveform visualization.

- Created `voice-experience.js`
- Streaming speech recognition
- Audio waveform visualization
- Voice state machine (idle, listening, thinking, speaking)

---

## v7.3.0 — Reliability Foundation (2026-07-26)

> Async LLM, async SQLite, logging overhaul.

- Async LLM (`achat()`, `achat_stream()`)
- Async SQLite (aiosqlite, WAL mode)
- Logging to 43+ silent `except: pass` handlers
- WebSocket consolidation (`ws-manager.js`)
- JS test infrastructure (Jest + `ws-manager.test.js`)

---

## v7.2.0 — UI Audit & Workspace Planning (2026-07-26)

> Comprehensive UX audit, workspace redesigns.

- Created `docs/UI_UX_AUDIT_v7.md`
- Scored current UI 4.3/10

---

## v7.1.0 — Foundation

> Core architecture and multi-agent system.

- Multi-agent architecture with 4 Kings + 19 workers
- 5-layer memory system
- Computer control (mouse, keyboard, screen, browser)
- Web dashboard with 5 workspaces
- Voice I/O (STT + TTS providers)
- Mission engine with autonomous execution
- Permission system with 5 permissions

---

## v7.0.0 — Initial Release

> JARVIS v7 — Personal AI Operating System.

- FastAPI backend with async architecture
- SQLite for persistence
- WebSocket for real-time updates
- 23 specialized agents
- Knowledge graph integration
