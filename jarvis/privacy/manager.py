"""Privacy Manager — controls JARVIS observation permissions and audit trail."""

import json
import os
import time
from typing import Any, Dict, List, Optional

from jarvis.privacy.models import AuditEntry, PrivacySettings


class PrivacyManager:
    """Persistent privacy controls backed by JSON files.

    Settings are stored in ``privacy_settings.json`` and the append-only
    audit log lives in ``privacy_audit.json``.  Both files live next to
    the module by default but the paths can be overridden via the
    constructor.
    """

    SETTINGS_FILE = "privacy_settings.json"
    AUDIT_FILE = "privacy_audit.json"

    def __init__(
        self,
        settings_path: Optional[str] = None,
        audit_path: Optional[str] = None,
    ) -> None:
        base = os.path.dirname(os.path.abspath(__file__))
        self._settings_path = settings_path or os.path.join(base, self.SETTINGS_FILE)
        self._audit_path = audit_path or os.path.join(base, self.AUDIT_FILE)
        self._settings: PrivacySettings = PrivacySettings()
        self._audit_log: List[AuditEntry] = []

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    async def get_settings(self) -> PrivacySettings:
        """Return the current privacy settings."""
        return self._settings

    async def update_setting(self, category: str, enabled: bool) -> None:
        """Toggle a specific privacy category on or off."""
        if not hasattr(self._settings, category):
            raise ValueError(f"Unknown privacy category: '{category}'")
        setattr(self._settings, category, enabled)

    async def is_allowed(self, category: str) -> None:
        """Return ``True`` if the given category is currently enabled."""
        return getattr(self._settings, category, False)

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------

    async def get_audit_log(self, limit: int = 100) -> List[AuditEntry]:
        """Return the most recent audit entries (newest first)."""
        return list(reversed(self._audit_log[-limit:]))

    async def log_observation(self, category: str, detail: str) -> None:
        """Append an observation to the audit trail."""
        allowed = await self.is_allowed(category)
        entry = AuditEntry(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            category=category,
            action="observe",
            detail=detail,
            allowed=allowed,
        )
        self._audit_log.append(entry)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def save(self) -> None:
        """Persist current settings and audit log to disk."""
        with open(self._settings_path, "w", encoding="utf-8") as fh:
            json.dump(self._settings.to_dict(), fh, indent=2)

        audit_data = [e.to_dict() for e in self._audit_log]
        with open(self._audit_path, "w", encoding="utf-8") as fh:
            json.dump(audit_data, fh, indent=2)

    async def load(self) -> None:
        """Load settings and audit log from disk (if the files exist)."""
        if os.path.exists(self._settings_path):
            with open(self._settings_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self._settings = PrivacySettings.from_dict(data)

        if os.path.exists(self._audit_path):
            with open(self._audit_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self._audit_log = [
                AuditEntry(
                    timestamp=str(e.get("timestamp", "")),
                    category=str(e.get("category", "")),
                    action=str(e.get("action", "")),
                    detail=str(e.get("detail", "")),
                    allowed=bool(e.get("allowed", False)),
                )
                for e in data
            ]
