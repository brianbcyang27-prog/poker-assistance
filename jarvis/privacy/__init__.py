"""JARVIS Privacy Controls — observation permissions and audit trail.

Every subsystem checks :func:`is_allowed` before accessing
sensitive resources.  All access attempts are appended to an
immutable audit log.
"""

from typing import List, Optional

from jarvis.privacy.manager import PrivacyManager
from jarvis.privacy.models import AuditEntry, PrivacySettings

__all__ = [
    "Privacy",
    "PrivacySettings",
    "AuditEntry",
]


class Privacy:
    """Public facade over :class:`PrivacyManager`.

    Wraps every manager method as a thin async call so callers
    only need to import this module.
    """

    def __init__(self) -> None:
        self._mgr = PrivacyManager()

    async def get_settings(self) -> PrivacySettings:
        """Return current privacy settings."""
        return await self._mgr.get_settings()

    async def update_setting(self, category: str, enabled: bool) -> None:
        """Toggle a privacy category."""
        await self._mgr.update_setting(category, enabled)

    async def is_allowed(self, category: str) -> bool:
        """Check whether a specific observation category is enabled."""
        return await self._mgr.is_allowed(category)

    async def get_audit_log(self, limit: int = 100) -> List[AuditEntry]:
        """Return the most recent audit entries."""
        return await self._mgr.get_audit_log(limit)

    async def log_observation(self, category: str, detail: str) -> None:
        """Log an observation attempt to the audit trail."""
        await self._mgr.log_observation(category, detail)

    async def save(self) -> None:
        """Persist settings and audit log to disk."""
        await self._mgr.save()

    async def load(self) -> None:
        """Load settings and audit log from disk."""
        await self._mgr.load()
