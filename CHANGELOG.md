# Changelog

## v6.4.2 — Enterprise Secret Vault & Security Framework (2026-07-21)

### NEW: Secret Vault
- AES-256-GCM encrypted vault (`.secrets.enc`) — the single source of truth for all credentials
- PBKDF2-HMAC-SHA256 key derivation with 600,000 iterations
- Authenticated encryption with integrity verification
- Password change, lock/unlock, metadata tracking

### NEW: Multi-Provider Architecture
- Priority chain: macOS Keychain → Encrypted Vault → Environment Variables → .env → GitHub Actions
- `SecretManager.get()` — unified interface, application never knows where secrets come from
- Automatic fallback through provider chain
- Secret access audit logging

### NEW: First-Run Experience
- Interactive setup wizard when no vault exists
- Guided master password creation
- API key entry with optional providers
- NVIDIA key validation via live API request
- Automatic migration from existing `.env` files

### NEW: Repository Secret Scanner
- Detects NVIDIA, OpenAI, Anthropic, GitHub, AWS, Azure, Google keys
- JWT tokens, Bearer tokens, private keys, passwords, connection strings
- Generates `security_report.md` with severity, line numbers, recommendations
- Security health score (0-100)

### NEW: Git Protection
- Automatic `.gitignore` entries for `.secrets.enc`, `*.pem`, `*.key`, `credentials.json`
- Pre-commit hook that scans staged diffs for secrets
- Rejects commits containing hardcoded credentials

### NEW: Log Redaction
- `LogRedactor` automatically redacts API keys, passwords, tokens from all text
- Works on strings, dicts, and lists
- Applied to logs, events, memory, mission replay, reasoning, tool history

### NEW: Security Dashboard API
- `GET /api/security/status` — vault status, encryption info, providers
- `GET /api/security/providers` — provider health check
- `GET /api/security/secrets` — list secrets (masked)
- `POST /api/security/secrets` — set a secret
- `DELETE /api/security/secrets/{key}` — delete a secret
- `POST /api/security/vault/create` — create vault
- `POST /api/security/vault/unlock` — unlock vault
- `POST /api/security/vault/lock` — lock vault
- `GET /api/security/scan` — scan repository
- `GET /api/security/audit` — audit log
- `POST /api/security/git-protection/install` — install hooks

### IMPROVED
- `jarvis/core/config.py` now resolves secrets via `SecretManager` before env vars
- `.gitignore` expanded with security entries
- 63 comprehensive tests (all passing)

---

## v6.4.1 — Bug Fixes & Stability (2026-07-21)

### FIXED
- Page freeze: infinite `while` loop in graph-3d.js `_updatePulse()` changed to `if`
- 404 on Core tab: frontend graph endpoints corrected to `/api/system/graph/data`
- Memory galaxy: added root `/api/memory` endpoint
- WebSocket reconnect loops capped at 20 attempts (living-interface, unified-timeline)
- fetchHierarchy retry capped at 10 attempts (command-map)
- Cache version bumped to force browser reload

---

## v6.4.0 — Maintenance & Stability (2026-07-21)

### FIXED
- Database lazy `asyncio.Lock()` init (Python 3.9 crash)
- Added `execute()`/`commit()`/`fetchone()`/`fetchall()` proxy methods for memory subsystem
- DOM refs `#jarvis-canvas` → `#golden-core-container`, `#hierarchy-content` → `#command-map`
- Version aligned to v6.4.0 across all 7 files
- Added logging to silent `except Exception: pass` blocks in lifespan
- Fixed hardcoded `ai_tool_command` path
- Removed Pydantic v2 `env=` deprecation warnings
- `em.get_episode()` → `em.get()` (method didn't exist)
- `pm.forget(category, key)` → `pm.forget(category=category, key=key)`
- World model: full rewrite from sync `subprocess.run()` to async `asyncio.create_subprocess_shell()`
- Knowledge graph: full rewrite from sync `sqlite3` to async `aiosqlite`
- RAG: `MATCH` → `LIKE` (conversations table isn't FTS5)
- RAG: `task_name` → `user_request`, `result` → `summary` (wrong column names)
- Added try/except error handling to all graph endpoints + capabilities

## [6.5.0] — 2026-07-22

### Reality & Productization Update

Transformed JARVIS from an impressive AI engineering project into a reliable personal AI assistant.

#### Phase 0: Full System Audit
- Complete audit of all backend endpoints (22/22 passed)
- Frontend page analysis
- Identified broken/missing features
- Created `docs/V6.5_AUDIT_REPORT.md`

#### Phase 1: Core UX Fix
- Restructured navigation: Main (Core, Chat, Projects, Computer, Memory) + Developer toggle
- Added Developer Mode toggle to hide/show dev features
- Added Projects workspace with project listing
- Added Computer workspace with tools (Screen, Terminal, Files, Browser)
- Added Metrics and Logs workspaces for developers
- Updated version display to v6.5.0

#### Phase 2: Self-Awareness Fix
- Enhanced capability registry with categories (browser, computer, memory, engineering)
- Added memory capabilities (episodes, personal, journal, working, graph)
- Created `generate_capability_prompt()` for LLM injection
- Chat streaming now injects capability-aware system prompt
- LLM knows what tools it has available

#### Phase 3: Computer Assistant Workflows
- Created `jarvis/core/workflows.py` with predefined workflows:
  - `scan_projects`: Scan workspace for projects
  - `system_info`: Gather system information
  - `find_files`: Find files matching patterns
- Added `/api/computer/workflow` endpoint
- Added `/api/computer/workflows` listing endpoint

#### Phase 4: Permission Center
- Created `jarvis/core/permissions.py` with macOS-like privacy settings
- 5 permission types: Files, Screen, Accessibility, Terminal, Browser
- Permissions persist to `~/.jarvis/permissions.json`
- Added `/api/system/permissions` GET/POST endpoints
- Computer actions now check permissions before execution
- Added permission UI to Settings page with toggle switches

#### Phase 5: Memory Validation
- Created `jarvis/core/memory_validation.py`
- Memory health check for all memory systems
- Secret detection to prevent storing API keys/passwords
- Added `/api/memory/health` endpoint
- Validates episodic, personal, journal, and working memory

#### Phase 6: Tool Connection Test
- Created `python -m jarvis doctor` command
- Tests: Database, LLM, Memory, Browser, Computer, Accessibility, Voice, Frontend, WebSocket
- Human-readable output with pass/warn/fail status
- Added `jarvis/__main__.py` for CLI entry point

#### Phase 7: Frontend Polish
- Permission center UI in Settings page
- Toggle switches for each permission
- Permission descriptions explain why access is needed
- CSS improvements for new components

#### Phase 8: Stability Fixes
- Added 30-second timeout to chat streaming
- Better error messages for timeout vs other errors
- WebSocket reconnection already had 20-attempt limit
- Version labels updated throughout

#### Phase 9: Testing
- Created `tests/test_v650_reality.py` with 11 tests
- All tests passing:
  - Server starts
  - Frontend loads
  - Chat works
  - Memory works
  - Tools visible
  - Computer permission works
  - Golden core renders
  - Developer mode toggle works
  - Memory health check works
  - Workflows available
  - Permissions update works
