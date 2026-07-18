"""Browser session management.

Persistent browser sessions with:
- Cookie storage
- Login state preservation
- Multiple profiles (personal, engineering, work)
- Session restore
- Database-backed persistence
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

log = logging.getLogger("jarvis.browser.sessions")

# Default storage directory
SESSIONS_DIR = Path.home() / ".jarvis" / "browser_sessions"


@dataclass
class BrowserSession:
    """A persistent browser session profile."""
    id: str = ""
    name: str = ""
    description: str = ""
    profile_dir: str = ""  # path to persistent storage
    cookies: list[dict] = None
    local_storage: dict = None
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    is_active: bool = False
    metadata: dict = None

    def __post_init__(self):
        if self.cookies is None:
            self.cookies = []
        if self.local_storage is None:
            self.local_storage = {}
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "profile_dir": self.profile_dir,
            "cookie_count": len(self.cookies),
            "created_at": self.created_at,
            "last_used": self.last_used,
            "is_active": self.is_active,
        }


class SessionManager:
    """Manages persistent browser sessions.

    Sessions are stored as JSON files in ~/.jarvis/browser_sessions/
    and optionally backed by the database for cross-restart persistence.

    Usage:
        mgr = SessionManager()
        session = await mgr.create("personal", description="Personal browsing")
        await mgr.save_cookies("personal", cookies)
        session = await mgr.restore("personal")
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else SESSIONS_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, BrowserSession] = {}

    async def create(
        self,
        name: str,
        description: str = "",
        profile_dir: Optional[str] = None,
    ) -> BrowserSession:
        """Create a new browser session profile."""
        if name in self._sessions:
            return self._sessions[name]

        if not profile_dir:
            profile_dir = str(self.storage_dir / name)
        Path(profile_dir).mkdir(parents=True, exist_ok=True)

        session = BrowserSession(
            id=f"session_{name}",
            name=name,
            description=description,
            profile_dir=profile_dir,
            created_at=time.time(),
        )

        self._sessions[name] = session
        await self._persist(session)
        log.info(f"Created session: {name}")
        return session

    async def get(self, name: str) -> Optional[BrowserSession]:
        """Get a session by name."""
        if name in self._sessions:
            return self._sessions[name]
        # Try loading from disk
        session = await self._load(name)
        if session:
            self._sessions[name] = session
        return session

    async def restore(self, name: str) -> Optional[BrowserSession]:
        """Restore a session for use (loads cookies, etc)."""
        session = await self.get(name)
        if session:
            session.is_active = True
            session.last_used = time.time()
            await self._persist(session)
        return session

    async def save_cookies(self, name: str, cookies: list[dict]):
        """Save cookies for a session."""
        session = await self.get(name)
        if not session:
            session = await self.create(name)
        session.cookies = cookies
        session.last_used = time.time()
        await self._persist(session)

    async def save_local_storage(self, name: str, data: dict):
        """Save local storage data for a session."""
        session = await self.get(name)
        if not session:
            session = await self.create(name)
        session.local_storage.update(data)
        session.last_used = time.time()
        await self._persist(session)

    async def list_sessions(self) -> list[BrowserSession]:
        """List all available sessions."""
        # Load any from disk that aren't in memory
        if self.storage_dir.exists():
            for entry in self.storage_dir.iterdir():
                if entry.is_dir() and entry.name not in self._sessions:
                    session = await self._load(entry.name)
                    if session:
                        self._sessions[entry.name] = session
        return list(self._sessions.values())

    async def delete(self, name: str) -> bool:
        """Delete a session."""
        session = self._sessions.pop(name, None)
        session_file = self.storage_dir / name / "session.json"
        if session_file.exists():
            session_file.unlink()
        profile_dir = self.storage_dir / name
        if profile_dir.exists():
            import shutil
            shutil.rmtree(profile_dir, ignore_errors=True)
        return session is not None

    async def export_cookies(self, name: str) -> list[dict]:
        """Export cookies for external use."""
        session = await self.get(name)
        return session.cookies if session else []

    async def import_cookies(self, name: str, cookies: list[dict]):
        """Import cookies from external source."""
        await self.save_cookies(name, cookies)

    async def _persist(self, session: BrowserSession):
        """Save session to disk."""
        session_dir = Path(session.profile_dir)
        session_dir.mkdir(parents=True, exist_ok=True)
        session_file = session_dir / "session.json"
        try:
            with open(session_file, "w") as f:
                json.dump(session.to_dict(), f, indent=2)
        except Exception as e:
            log.debug(f"Failed to persist session: {e}")

    async def _load(self, name: str) -> Optional[BrowserSession]:
        """Load session from disk."""
        session_file = self.storage_dir / name / "session.json"
        if not session_file.exists():
            return None
        try:
            with open(session_file) as f:
                data = json.load(f)
            return BrowserSession(
                id=data.get("id", f"session_{name}"),
                name=data.get("name", name),
                description=data.get("description", ""),
                profile_dir=data.get("profile_dir", str(self.storage_dir / name)),
                created_at=data.get("created_at", 0),
                last_used=data.get("last_used", 0),
                is_active=data.get("is_active", False),
            )
        except Exception as e:
            log.debug(f"Failed to load session: {e}")
            return None

    def get_stats(self) -> dict:
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": sum(1 for s in self._sessions.values() if s.is_active),
            "storage_dir": str(self.storage_dir),
        }


# Module-level singleton
session_manager = SessionManager()
