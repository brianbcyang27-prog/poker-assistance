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
