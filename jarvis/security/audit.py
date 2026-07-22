"""Audit log for secret access tracking."""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


_AUDIT_FILE = ".security_audit.jsonl"


class AuditLog:
    """Append-only audit log for all secret operations."""

    def __init__(self, log_dir: Optional[str] = None):
        self._path = Path(log_dir) if log_dir else Path.cwd()
        self._audit_file = self._path / _AUDIT_FILE

    def log(self, action: str, key: str, provider: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Append an audit entry."""
        entry = {
            "timestamp": time.time(),
            "action": action,
            "key": key,
            "provider": provider,
        }
        if details:
            entry["details"] = details

        try:
            with open(self._audit_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            pass

    def get_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Read recent audit entries."""
        if not self._audit_file.exists():
            return []

        entries = []
        try:
            lines = self._audit_file.read_text().strip().splitlines()
            for line in lines[-limit:]:
                if line.strip():
                    entries.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass

        return entries

    def get_stats(self) -> Dict[str, Any]:
        """Get audit statistics."""
        entries = self.get_entries(limit=10000)
        if not entries:
            return {"total": 0, "actions": {}, "providers": {}}

        actions = {}
        providers = {}
        for e in entries:
            actions[e.get("action", "unknown")] = actions.get(e.get("action", "unknown"), 0) + 1
            providers[e.get("provider", "unknown")] = providers.get(e.get("provider", "unknown"), 0) + 1

        return {
            "total": len(entries),
            "actions": actions,
            "providers": providers,
            "last_entry": entries[-1] if entries else None,
        }

    def clear(self) -> None:
        """Clear the audit log."""
        if self._audit_file.exists():
            self._audit_file.unlink()
