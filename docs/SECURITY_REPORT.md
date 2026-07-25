# JARVIS Security Report

> Generated: v8.0.0
> Scope: Full API surface (223 endpoints), frontend, configuration

---

## Executive Summary

JARVIS has **8 critical**, **7 high**, and **6 medium** security vulnerabilities. The most severe issue is the complete absence of authentication — every endpoint, including shell execution, vault management, and firmware upload, is accessible to anyone who can reach the server.

**Risk Level: HIGH** — Do not expose to untrusted networks.

---

## Critical Vulnerabilities

### S1: No Authentication (ALL endpoints)

**Severity:** CRITICAL
**Impact:** Complete system compromise

Every single API endpoint is accessible without authentication. This includes:

- `/api/computer/action` — Shell command execution
- `/api/computer/shutdown` — System shutdown
- `/api/security/vault/*` — Encrypted vault management
- `/api/security/secrets` — Secret storage
- `/api/voice/providers/*/install` — Package installation
- `/api/engineering/firmware/upload` — Firmware flashing
- `/api/settings` — Configuration modification
- `/ws/agents` — Real-time system events

**Recommendation:** Add bearer token or API key authentication middleware on all `/api/` routes.

---

### S2: Shell Execution Without Auth

**Severity:** CRITICAL
**Location:** `computer.py:67`
**Endpoint:** `POST /api/computer/action`

The `shell_execute` action runs arbitrary OS commands. Even with the permission-center check, there is no user authentication — anyone can grant themselves permissions.

**Impact:** Remote code execution, data exfiltration, system compromise.

**Recommendation:** Require authentication before any computer action.

---

### S3: Package Installation Without Auth

**Severity:** CRITICAL
**Location:** `voice.py:167`
**Endpoint:** `POST /api/voice/providers/{provider_id}/install`

Executes `pip3 install` commands. While currently only hardcoded values, the `check_command` fields are executed with `shell=True` (lines 135-136).

**Impact:** Arbitrary code execution via malicious package names.

**Recommendation:** Require authentication, validate provider IDs against allowlist.

---

### S4: Vault Access Without Auth

**Severity:** CRITICAL
**Location:** `security.py`
**Endpoints:** `POST /api/security/vault/*`

Anyone can create, unlock, lock, or change the vault password. The vault password is sent in plaintext over HTTP.

**Impact:** Complete compromise of encrypted secrets.

**Recommendation:** Require authentication for all vault operations.

---

### S5: Secrets Management Without Auth

**Severity:** CRITICAL
**Location:** `security.py`
**Endpoints:** `GET/POST/DELETE /api/security/secrets`

GET lists all secrets (masked), POST sets a secret, DELETE removes one. No authentication barrier.

**Impact:** Secret theft, modification, or deletion.

**Recommendation:** Require authentication for all secret operations.

---

### S6: WebSocket Without Auth

**Severity:** CRITICAL
**Location:** `websocket.py`
**Endpoint:** `WS /ws/agents`

Any client can connect and receive real-time system events, agent states, and conversation data. No origin check.

**Impact:** Information leakage, potential for injection attacks.

**Recommendation:** Add token authentication and origin validation.

---

### S7: Firmware Upload Without Auth

**Severity:** CRITICAL
**Location:** `engineering.py`
**Endpoint:** `POST /api/engineering/firmware/upload`

Can flash arbitrary firmware to connected hardware devices.

**Impact:** Hardware damage, device compromise, physical safety risks.

**Recommendation:** Require authentication, validate firmware signatures.

---

### S8: Path Traversal in File Export

**Severity:** CRITICAL
**Location:** `engineering.py`
**Endpoints:** `POST /api/engineering/cad/export`, `POST /api/engineering/pcb/export`

The `path` parameter is user-controlled and passed directly to file export functions.

**Impact:** Arbitrary file write, system compromise.

**Recommendation:** Validate that resolved paths stay within allowed directories.

---

## High Vulnerabilities

### S9: Command Injection

**Severity:** HIGH
**Location:** `voice.py:135-136`

`subprocess.run(info["check_command"], shell=True, ...)` — The `check_command` values from `KNOWN_PROVIDERS` are executed with `shell=True`. While currently hardcoded, if the dict is ever extended with user input, this becomes exploitable.

**Recommendation:** Use `asyncio.create_subprocess_exec` with list arguments (no shell).

---

### S10: Path Traversal in Audio Serving

**Severity:** HIGH
**Location:** `voice.py:302-317`

`serve_audio` uses `Path("audio_cache") / filename` where `filename` is a URL path parameter. A crafted filename like `../../etc/passwd` could serve arbitrary files.

**Recommendation:** Validate that the resolved path stays within `audio_cache/`.

---

### S11: Arbitrary Config Mutation

**Severity:** HIGH
**Location:** `settings.py:55-69`

Any POST to `/api/settings` can modify `nvidia_api_key`, `host`, `port`, and other settings, persisted to `.env`.

**Impact:** API key theft, server redirection, configuration corruption.

**Recommendation:** Require authentication, validate config values.

---

### S12: `.env` File Overwrite

**Severity:** HIGH
**Location:** `voice.py:279-299`

`_save_tts_provider_to_env` rewrites the entire `.env` file. A bug could corrupt all environment configuration.

**Recommendation:** Use atomic file writes, backup before overwrite.

---

### S13: Shutdown Without Auth

**Severity:** HIGH
**Location:** `computer.py:69`

Anyone can shut down the computer controller.

**Recommendation:** Require authentication.

---

### S14: SSE Stream Without Rate Limiting

**Severity:** HIGH
**Location:** `chat.py:130`

`/api/chat/stream` has no rate limiting. An attacker could open many long-lived SSE connections to exhaust server resources.

**Recommendation:** Add connection limits per IP.

---

### S15: Unbounded File Uploads

**Severity:** HIGH
**Location:** `voice.py:38-39`, `voice.py:378-379`

`upload_voice_sample` and `create_clone_profile` read full uploaded files into memory with no size limit. Large file uploads could exhaust memory.

**Recommendation:** Add file size limits (e.g., 10MB for audio).

---

## Medium Vulnerabilities

### S16: Raw Dict Body Params

**Severity:** MEDIUM
**Location:** `system.py` (20+ endpoints)

~20+ endpoints accept `body: dict` directly with no schema validation. Vulnerable to injection or unexpected data.

**Recommendation:** Replace with Pydantic models.

---

### S17: No Input Sanitization

**Severity:** MEDIUM
**Location:** Multiple endpoints

Workspace IDs, mission IDs, device IDs, card IDs, and session IDs are passed through without validation beyond FastAPI's type checking.

**Recommendation:** Add format validation (alphanumeric, length limits).

---

### S18: Environment Variable Exposure

**Severity:** MEDIUM
**Location:** `system.py:914-918`

`dev_env` returns "sanitized" environment variables, but the sanitization logic is not visible. If insufficient, API keys could be leaked.

**Recommendation:** Audit sanitization, remove from production.

---

### S19: API Key in Settings Response

**Severity:** MEDIUM
**Location:** `settings.py:13`

`nvidia_api_key` is returned in the GET `/api/settings` response body.

**Recommendation:** Mask API keys in responses.

---

### S20: No CORS Middleware

**Severity:** MEDIUM
**Location:** `main.py`

No `CORSMiddleware` configured. If any frontend is served from a different origin, requests will be blocked by browsers (or worse, be open to CSRF).

**Recommendation:** Add `CORSMiddleware` with appropriate origins.

---

### S21: HTTP Only (No TLS)

**Severity:** MEDIUM
**Location:** `main.py:297`

The server runs on HTTP. All data including vault passwords, API keys, and chat messages travel in plaintext.

**Recommendation:** Add TLS termination (reverse proxy or direct).

---

## Low Vulnerabilities

### S22: MD5 for Filenames

**Severity:** LOW
**Location:** `chat.py:106`

MD5 is cryptographically broken, though here it is only used for filename generation (not security).

**Recommendation:** Use SHA-256 or UUID.

---

### S23: No Disk Cleanup on Voice Delete

**Severity:** LOW
**Location:** `voice.py:62-67`

`delete_voice_sample` removes the DB record but does not delete the file from disk.

**Recommendation:** Delete file before DB record.

---

### S24: Global Mutable State

**Severity:** LOW
**Location:** `main.py:25-26`

`jarvis` and `workspace_manager` are module-level globals mutated by the lifespan function. Thread-safety concerns if multiple workers.

**Recommendation:** Use dependency injection.

---

## Recommendations Priority Order

1. **Add authentication middleware** — All `/api/` routes
2. **Fix path traversal** — File export and audio serving
3. **Add CORS middleware** — Control cross-origin access
4. **Block dangerous endpoints** — Computer, vault, firmware, settings
5. **Fix shell injection** — Use `create_subprocess_exec`
6. **Add file size limits** — Voice uploads
7. **Fix error-in-200-OK patterns** — Use proper HTTP status codes
8. **Add input validation** — Pydantic models for all body params
9. **Add TLS** — encrypt all traffic
10. **Add audit logging** — Track all sensitive operations

---

## Conclusion

JARVIS has a solid security foundation (vault, permissions module) but lacks the gate to reach it. The absence of authentication is the single most critical issue. Once authentication is added, the risk profile drops significantly. The path traversal and shell injection issues are also high priority.

**Risk Level:** HIGH — Internal/LAN use only until authentication is added.
