"""Trinity Permission System — Tri-state privacy controls for JARVIS v9.0.0.

Each capability has three states:
    ALLOW — auto-granted without asking
    ASK   — requires user confirmation before each use (or time-based grant)
    DENY  — blocked outright

Capabilities managed (12):
    files, screen, accessibility, terminal, browser,
    network, microphone, camera, clipboard, notifications,
    location, calendar

Usage:
    from jarvis.core.permissions import permission_center

    # Check a permission
    allowed, state = permission_center.check("terminal")
    if allowed:
        execute_command()

    # Tri-state set
    permission_center.set_state("files", TrinityState.ASK)
    permission_center.set_state("terminal", TrinityState.ALLOW)

    # Time-based grant (for ASK state)
    permission_center.grant("camera", duration=300)
"""

import json
import logging
import time
from enum import StrEnum
from pathlib import Path

log = logging.getLogger("jarvis.permissions")


class TrinityState(StrEnum):
    """Tri-state permission model.

    ALLOW — auto-granted, no user intervention needed.
    ASK   — requires user confirmation; can be temporarily granted.
    DENY  — always blocked.
    """

    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


class TrinityPermission:
    """A single capability with tri-state and optional time-based grant."""

    def __init__(
        self,
        name: str,
        description: str,
        reason: str,
        default: TrinityState = TrinityState.ALLOW,
    ) -> None:
        self.name = name
        self.description = description
        self.reason = reason
        self.state = default
        self._granted_until: float = 0.0

    def check(self) -> bool:
        """Return True if the permission is currently granted.

        Rules:
            ALLOW → True
            DENY  → False
            ASK   → True only if a time-based grant is still active.
        """
        if self.state == TrinityState.ALLOW:
            return True
        if self.state == TrinityState.DENY:
            return False
        if time.time() < self._granted_until:
            return True
        return False

    def grant(self, duration: float) -> None:
        """Temporarily override ASK state for *duration* seconds."""
        self._granted_until = time.time() + duration

    def revoke_grant(self) -> None:
        """Revoke any active time-based grant."""
        self._granted_until = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "reason": self.reason,
            "state": self.state.value,
            "granted": time.time() < self._granted_until,
        }


_DEFAULT_CAPABILITIES: list[tuple[str, str, str, TrinityState]] = [
    ("files", "File Access", "Browse, read, and manage files on your computer", TrinityState.ALLOW),
    ("screen", "Screen Capture", "Capture screenshots and view your screen", TrinityState.ALLOW),
    (
        "accessibility",
        "Accessibility Control",
        "Control UI elements and automate interactions",
        TrinityState.DENY,
    ),
    ("terminal", "Terminal Execution", "Execute shell commands", TrinityState.ALLOW),
    ("browser", "Browser Control", "Navigate websites and automate web tasks", TrinityState.ALLOW),
    (
        "network",
        "Network Access",
        "Make HTTP requests and access network resources",
        TrinityState.ALLOW,
    ),
    (
        "microphone",
        "Microphone Access",
        "Capture audio input for speech recognition",
        TrinityState.ASK,
    ),
    ("camera", "Camera Access", "Capture images from camera", TrinityState.DENY),
    ("clipboard", "Clipboard Access", "Read and write system clipboard", TrinityState.ASK),
    ("notifications", "Notifications", "Display system notifications", TrinityState.ALLOW),
    ("location", "Location Services", "Access geographic location", TrinityState.ASK),
    ("calendar", "Calendar Access", "Read and manage calendar events", TrinityState.ASK),
]


class PermissionCenter:
    """Manages all JARVIS permissions with tri-state control."""

    def __init__(self) -> None:
        self._permissions: dict[str, TrinityPermission] = {}
        self._config_path = Path.home() / ".jarvis" / "permissions.json"
        self._initialize_defaults()
        self._load()
        self._audit_log: list[dict] = []
        self._audit_max = 500

    def _initialize_defaults(self) -> None:
        for name, desc, reason, default in _DEFAULT_CAPABILITIES:
            self._permissions[name] = TrinityPermission(
                name=name,
                description=desc,
                reason=reason,
                default=default,
            )

    def _load(self) -> None:
        try:
            if self._config_path.exists():
                raw = json.loads(self._config_path.read_text())
                if not raw:
                    return
                first_val = next(iter(raw.values()))
                is_old_format = isinstance(first_val, bool)
                for name, state_value in raw.items():
                    if name in self._permissions:
                        if is_old_format:
                            state_value = TrinityState.ALLOW if state_value else TrinityState.DENY
                        else:
                            try:
                                state_value = TrinityState(state_value)
                            except ValueError:
                                log.warning("Invalid state %r for %s, skipping", state_value, name)
                                continue
                        self._permissions[name].state = state_value
        except Exception as e:
            log.debug("Failed to load permissions: %s", e)

    def _save(self) -> None:
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {name: perm.state.value for name, perm in self._permissions.items()}
            self._config_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            log.debug("Failed to save permissions: %s", e)

    def check(self, permission_name: str) -> tuple[bool, str]:
        """Check if a permission is currently granted.

        Returns:
            (allowed: bool, current_state: str)

        The caller should use the state string to determine the UX flow:
            "allow" → proceed silently
            "ask"   → prompt user for confirmation (unless time-granted)
            "deny"  → show blocked message
        """
        perm = self._permissions.get(permission_name)
        if not perm:
            self._audit("check", permission_name, "unknown permission", "deny")
            return False, "deny"
        allowed = perm.check()
        detail = f"state={perm.state.value}, granted={time.time() < perm._granted_until}"
        self._audit("check", permission_name, detail, "allow" if allowed else "deny")
        return allowed, perm.state.value

    def set_state(self, permission_name: str, state: TrinityState) -> bool:
        """Set a permission to a specific tri-state value.

        Returns True if the permission exists and was updated.
        """
        if permission_name not in self._permissions:
            self._audit("set_state", permission_name, "permission not found", "error")
            return False
        self._permissions[permission_name].state = state
        self._permissions[permission_name].revoke_grant()
        self._save()
        log.info("Permission %s set to %s", permission_name, state.value)
        self._audit("set_state", permission_name, f"state={state.value}", "ok")
        return True

    def set(self, permission_name: str, enabled: bool) -> bool:
        """Legacy binary toggle — converts to tri-state.

        True  → ALLOW
        False → DENY

        Provided for backward compatibility with existing API consumers.
        Prefer set_state() for new code.
        """
        new_state = TrinityState.ALLOW if enabled else TrinityState.DENY
        return self.set_state(permission_name, new_state)

    def grant(self, permission_name: str, duration: float = 300) -> bool:
        """Grant temporary access for *duration* seconds.

        Only effective when the permission is in ASK state.
        Returns True if the permission exists.
        """
        perm = self._permissions.get(permission_name)
        if not perm:
            self._audit("grant", permission_name, "permission not found", "error")
            return False
        perm.grant(duration)
        log.info("Permission %s granted for %.0fs", permission_name, duration)
        self._audit("grant", permission_name, f"duration={duration}s", "ok")
        return True

    def get_all(self) -> list[dict]:
        """Get all permissions as serializable dicts."""
        return [perm.to_dict() for perm in self._permissions.values()]

    def get(self, permission_name: str) -> dict | None:
        """Get a single permission as a dict, or None if not found."""
        perm = self._permissions.get(permission_name)
        return perm.to_dict() if perm else None

    def check_required(self, permissions: list[str]) -> tuple[bool, list[str]]:
        """Check if all required permissions are currently granted.

        Returns (all_granted, missing_permissions).
        """
        missing = [p for p in permissions if not self.check(p)[0]]
        return len(missing) == 0, missing

    def _audit(self, action: str, permission_name: str, detail: str, result: str) -> None:
        """Record an audit entry for permission activity."""
        entry = {
            "timestamp": time.time(),
            "action": action,
            "permission": permission_name,
            "detail": detail,
            "result": result,
        }
        self._audit_log.append(entry)
        if len(self._audit_log) > self._audit_max:
            self._audit_log.pop(0)

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        """Return the most recent audit entries."""
        return list(self._audit_log[-limit:])


permission_center = PermissionCenter()
