"""Permission Center — macOS-like privacy settings for JARVIS.

Controls access to: Files, Screen, Accessibility, Terminal, Browser.
"""

import logging
from typing import Optional
from pathlib import Path
import json

log = logging.getLogger("jarvis.permissions")


class Permission:
    """A single permission toggle."""
    
    def __init__(self, name: str, description: str, reason: str, default: bool = True):
        self.name = name
        self.description = description
        self.reason = reason
        self.enabled = default
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "reason": self.reason,
            "enabled": self.enabled,
        }


class PermissionCenter:
    """Manages all JARVIS permissions."""
    
    def __init__(self):
        self._permissions: dict[str, Permission] = {
            "files": Permission(
                "files",
                "File Access",
                "Required to browse, read, and manage files on your computer",
                default=True,
            ),
            "screen": Permission(
                "screen",
                "Screen Capture",
                "Required to capture screenshots and view your screen",
                default=True,
            ),
            "accessibility": Permission(
                "accessibility",
                "Accessibility Control",
                "Required to control UI elements and automate interactions",
                default=False,
            ),
            "terminal": Permission(
                "terminal",
                "Terminal Execution",
                "Required to execute shell commands",
                default=True,
            ),
            "browser": Permission(
                "browser",
                "Browser Control",
                "Required to navigate websites and automate web tasks",
                default=True,
            ),
        }
        self._config_path = Path.home() / ".jarvis" / "permissions.json"
        self._load()
    
    def _load(self):
        """Load permissions from config file."""
        try:
            if self._config_path.exists():
                with open(self._config_path) as f:
                    data = json.load(f)
                for name, enabled in data.items():
                    if name in self._permissions:
                        self._permissions[name].enabled = enabled
        except Exception as e:
            log.debug(f"Failed to load permissions: {e}")
    
    def _save(self):
        """Save permissions to config file."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {name: perm.enabled for name, perm in self._permissions.items()}
            with open(self._config_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.debug(f"Failed to save permissions: {e}")
    
    def check(self, permission_name: str) -> bool:
        """Check if a permission is enabled."""
        perm = self._permissions.get(permission_name)
        if not perm:
            return False
        return perm.enabled
    
    def set(self, permission_name: str, enabled: bool) -> bool:
        """Set a permission value."""
        if permission_name not in self._permissions:
            return False
        self._permissions[permission_name].enabled = enabled
        self._save()
        log.info(f"Permission '{permission_name}' set to {enabled}")
        return True
    
    def get_all(self) -> list[dict]:
        """Get all permissions."""
        return [perm.to_dict() for perm in self._permissions.values()]
    
    def check_required(self, permissions: list[str]) -> tuple[bool, list[str]]:
        """Check if all required permissions are enabled.
        
        Returns (all_granted, missing_permissions).
        """
        missing = [p for p in permissions if not self.check(p)]
        return len(missing) == 0, missing


# Module-level singleton
permission_center = PermissionCenter()
