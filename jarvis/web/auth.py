"""Authentication middleware for JARVIS v8.0.0.

Simple token auth:
- API key in X-API-Key header for programmatic access
- Session cookie for web UI
- Localhost auto-trusted (no auth required on 127.0.0.1)
"""

import json
import logging
import secrets
import time
from pathlib import Path

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("jarvis.auth")

# Paths that never require auth
PUBLIC_PATHS = {
    "/",
    "/api/health",
    "/api/auth/login",
    "/api/auth/status",
    "/static",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# Paths that require auth
PROTECTED_PREFIXES = (
    "/api/",
    "/ws",
)


def _is_local(request: Request) -> bool:
    """Check if request is from localhost."""
    host = request.client.host if request.client else ""
    return host in ("127.0.0.1", "::1", "localhost")


def _is_public(path: str) -> bool:
    """Check if path is public (no auth needed)."""
    if path in PUBLIC_PATHS:
        return True
    for prefix in ("/static", "/docs", "/openapi", "/redoc"):
        if path.startswith(prefix):
            return True
    return False


class AuthManager:
    """Manages authentication tokens and sessions."""

    def __init__(self):
        self._config_path = Path.home() / ".jarvis" / "auth.json"
        self._api_keys: dict[str, dict] = {}  # key_hash -> {name, created, last_used}
        self._sessions: dict[str, dict] = {}  # session_id -> {created, last_used, ip}
        self._api_key: str | None = None  # The raw API key (shown once on setup)
        self._load()

    def _load(self):
        """Load auth config from disk."""
        try:
            if self._config_path.exists():
                data = json.loads(self._config_path.read_text())
                self._api_keys = data.get("api_keys", {})
                self._api_key = data.get("raw_api_key")
        except Exception as e:
            logger.debug("Failed to load auth config: %s", e)

    def _save(self):
        """Save auth config to disk."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "api_keys": self._api_keys,
                "raw_api_key": self._api_key,
            }
            self._config_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning("Failed to save auth config: %s", e)

    def setup(self) -> str:
        """Generate initial API key if none exists. Returns the raw key."""
        if self._api_key:
            return self._api_key

        key = "jrv_" + secrets.token_hex(32)
        self._api_key = key
        key_hash = secrets.token_hex(32)
        self._api_keys[key_hash] = {
            "name": "default",
            "created": time.time(),
            "last_used": 0,
        }
        self._save()
        logger.info("Generated new API key: %s...", key[:12])
        return key

    def verify_api_key(self, key: str) -> bool:
        """Verify an API key."""
        if not key:
            return False
        # For simplicity, compare directly (in production, use hash)
        return key == self._api_key

    def create_session(self, ip: str = "") -> str:
        """Create a new session. Returns session ID."""
        session_id = secrets.token_hex(16)
        self._sessions[session_id] = {
            "created": time.time(),
            "last_used": time.time(),
            "ip": ip,
        }
        self._save()
        return session_id

    def verify_session(self, session_id: str) -> bool:
        """Verify a session exists and is valid."""
        if not session_id:
            return False
        session = self._sessions.get(session_id)
        if not session:
            return False
        # Sessions expire after 24 hours
        if time.time() - session["created"] > 86400:
            del self._sessions[session_id]
            self._save()
            return False
        session["last_used"] = time.time()
        return True

    def get_api_key(self) -> str | None:
        """Get the raw API key (for display)."""
        return self._api_key


# Module-level singleton
auth_manager = AuthManager()


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for all HTTP requests."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for public paths
        if _is_public(path):
            return await call_next(request)

        # Skip auth for localhost (optional, controlled by config)
        # For now, localhost is always trusted
        if _is_local(request):
            # Still check for session cookie if present
            session_id = request.cookies.get("jarvis_session")
            if session_id and auth_manager.verify_session(session_id):
                request.state.authenticated = True
                request.state.auth_method = "session"
            else:
                request.state.authenticated = True
                request.state.auth_method = "local"
            return await call_next(request)

        # Check API key in header
        api_key = request.headers.get("X-API-Key")
        if api_key and auth_manager.verify_api_key(api_key):
            request.state.authenticated = True
            request.state.auth_method = "api_key"
            return await call_next(request)

        # Check session cookie
        session_id = request.cookies.get("jarvis_session")
        if session_id and auth_manager.verify_session(session_id):
            request.state.authenticated = True
            request.state.auth_method = "session"
            return await call_next(request)

        # Check Authorization header (Bearer token)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if auth_manager.verify_api_key(token):
                request.state.authenticated = True
                request.state.auth_method = "bearer"
                return await call_next(request)

        # Not authenticated
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide X-API-Key header or login.",
            headers={"WWW-Authenticate": "Bearer"},
        )
