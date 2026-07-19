# JARVIS Changelog

## v6.1.0 — System Integration & Engineering Workspace (2026-07-19)

> JARVIS becomes one unified operating system.

### Unified Workspace
- Merged `Workspace` (SQLite) and `Mission` (JSON) into a single persistent model with 24 fields
- Workspace now tracks: research findings, tool candidates, architecture plans, execution results, verification, reviews, memory records, timeline events, stage history, errors
- Database schema upgraded with 16 new columns (migration-safe for existing DBs)
- WorkspaceManager: create, get, search, add_task, update_task, add_timeline_event, record_stage, add_error, complete, search

### Cross-Agent Collaboration
- Workers can now request help from peers via event bus (`worker.help_request` / `worker.help_response`)
- Workers share results automatically (`worker.result_shared`)
- Workers can broadcast discoveries (`worker.broadcast.*`)
- King delegation passes previous worker results as context to subsequent workers
- Workers receive peer context in their LLM prompts

### Unified Mission Timeline
- New `UnifiedTimeline` JS component (`unified-timeline.js`)
- Connects to existing WebSocket at `/ws/agents`
- 200-event ring buffer with auto-scroll
- Filterable by event type, searchable, exportable as JSON
- Toggle panel on right side of screen

### Developer Dashboard
- New `/dashboard` route with full developer dashboard
- 7 panels: System Health, Active Workspaces, Worker Status, Live Event Stream, Memory Stats, API Performance, Tool Usage
- Auto-refresh every 10 seconds
- WebSocket live event feed
- Responsive grid layout

### Reliability Improvements
- New `jarvis.core.reliability` module with centralized config
- `ReliabilityConfig`: 18 configurable timeout/retry/concurrency settings
- `retry_with_backoff`: async decorator with exponential backoff
- `timeout_guard`: async context manager with timeout
- `safe_execute`: coroutine runner with timeout and default value
- LLM module now uses reliability config for timeouts and retries
- HTTP 5xx and connection errors trigger automatic retry with backoff

### API Additions
- `GET /api/workspace/search?q=query` — search workspaces
- `GET /api/workspace/{id}/timeline` — unified timeline for a workspace
- `POST /api/workspace/{id}/timeline` — add timeline event
- `POST /api/workspace/{id}/stage` — record pipeline stage
- `POST /api/workspace/{id}/complete` — mark workspace complete

### System Polish
- Version bumped to v6.1.0
- Updated navigation with Dashboard link
- Updated MASTER_ROADMAP.md
- All 208+ tests passing

---

## v6.0.2 — Resource Leak Fixes & Rate Limiting (2026-07-19)

- Full codebase resource audit (56 issues)
- Database: busy_timeout, 8 indexes, LIMIT guards, singleton Lock
- WebSocket: 30s heartbeat, dead-client cleanup, task tracking
- Frontend: GPU cleanup, stored listener references
- Rate limiting: global middleware + per-endpoint decorators

## v6.0.1 — Browser Cache Fix (2026-07-19)

- Cache-busting on all 23 static assets
- No-cache middleware for development
- Defensive pulsePool guard

## v6.0.0 — Visual & Design System Rewrite (2026-07-19)

- Complete UI rewrite
- Gold particle sphere (Graph3D)
- Workspace-based UI
- Agent Command Map, Knowledge Graph, Memory Galaxy
