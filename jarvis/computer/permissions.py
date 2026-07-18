"""Permission system for computer control.

Classifies every action into risk levels and enforces approval policies.

Risk levels:
  SAFE      — auto-approve (screenshots, reads, status)
  LOW       — auto-approve with logging (ls, git status, project files)
  MEDIUM    — allow with notification (installs, file modifications)
  HIGH      — require explicit confirmation (sudo, deletes)
  DANGEROUS — block unless manually approved (system folder changes)
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from .actions import RiskLevel, ActionType

log = logging.getLogger("jarvis.computer.permissions")


# ── Restricted paths (never allow without explicit override) ──

RESTRICTED_PATHS = [
    "/System",
    "/private/etc",
    "/private/var",
    "/usr/bin",
    "/usr/sbin",
    "/Library/LaunchDaemons",
    "~/.ssh",
    "~/.gnupg",
    "~/.aws/credentials",
    "~/.env",
    "/etc/hosts",
    "/etc/passwd",
    "/etc/shadow",
]

# Safe project directories (default allowed)
SAFE_DIRECTORIES = [
    os.path.expanduser("~/Projects"),
    os.path.expanduser("~/Documents"),
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Downloads"),
    "/tmp",
]

# Commands that are always dangerous
DANGEROUS_COMMANDS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+~",
    r"rm\s+-rf\s+\*",
    r"mkfs\.",
    r"dd\s+if=.*of=/dev/",
    r"chmod\s+777\s+/",
    r"curl.*\|\s*(ba)?sh",
    r"wget.*\|\s*(ba)?sh",
    r"sudo\s+rm",
    r"sudo\s+chmod",
    r"sudo\s+chown",
    r"launchctl\s+(un)?load",
    r"defaults\s+write",
    r"security\s+",
    r"diskutil\s+erase",
    r"kill\s+-9\s+1\b",
    r"shutdown",
    r"reboot",
    r"halt",
]

# Commands that require confirmation
HIGH_RISK_COMMANDS = [
    r"sudo\s+",
    r"rm\s+(-[a-zA-Z]*r|-r|-rf)\s+",
    r"rm\s+.*\.\w+\s*$",
    r"rmdir",
    r"kill\s+",
    r"killall\s+",
    r"pkill\s+",
    r"pip\s+install\s+--force",
    r"npm\s+install\s+--force",
    r"brew\s+uninstall",
    r"git\s+push\s+.*--force",
    r"git\s+clean\s+-fd",
    r"git\s+checkout\s+.*--force",
]

# Commands that are medium risk (modify files/system)
MEDIUM_RISK_COMMANDS = [
    r"pip\s+install",
    r"npm\s+install",
    r"yarn\s+add",
    r"brew\s+install",
    r"apt\s+install",
    r"brew\s+upgrade",
    r"mkdir",
    r"touch",
    r"cp\s+",
    r"mv\s+",
    r"chmod",
    r"chown",
    r"git\s+commit",
    r"git\s+push",
    r"git\s+merge",
    r"python\s+.*\.py",
    r"node\s+",
    r"npx\s+",
]

# Safe commands (read-only / informational)
SAFE_COMMANDS = [
    r"ls",
    r"pwd",
    r"echo",
    r"cat",
    r"head",
    r"tail",
    r"wc",
    r"grep",
    r"find",
    r"which",
    r"whereis",
    r"whoami",
    r"hostname",
    r"date",
    r"uptime",
    r"git\s+status",
    r"git\s+log",
    r"git\s+diff",
    r"git\s+branch",
    r"git\s+show",
    r"python\s+--version",
    r"node\s+--version",
    r"npm\s+--version",
    r"curl\s+.*\s+-I",  # HEAD requests
    r"ps\s+",
    r"top\s+-l\s+1",
    r"df\s+",
    r"du\s+",
    r"file\s+",
    r"stat\s+",
    r"type\s+",
    r"source\s+",
]


@dataclass
class PermissionDecision:
    """Result of a permission check."""
    allowed: bool
    risk_level: str
    reason: str
    requires_confirmation: bool = False
    requires_approval: bool = False
    approved_by: str = ""  # "auto", "cache", "notification", ""
    metadata: dict = field(default_factory=dict)


class PermissionSystem:
    """Classifies and gates computer actions based on risk.

    Usage:
        perms = PermissionSystem()
        decision = perms.check("rm -rf ./build")
        if decision.requires_confirmation:
            # ask user
        if decision.allowed:
            # execute
    """

    def __init__(self, safe_dirs: Optional[list[str]] = None, mode: str = "normal"):
        """Initialize permission system.

        Args:
            safe_dirs: Additional directories considered safe
            mode: "normal" | "permissive" | "strict"
        """
        self.mode = mode
        self.safe_dirs = list(SAFE_DIRECTORIES)
        if safe_dirs:
            self.safe_dirs.extend(safe_dirs)
        self._approval_cache: dict[str, bool] = {}

    def check(
        self,
        command: str,
        action_type: str = ActionType.TERMINAL,
        agent: str = "",
        context: Optional[dict] = None,
    ) -> PermissionDecision:
        """Check if an action is allowed.

        Args:
            command: The command or action to execute
            action_type: Type of action
            agent: Which agent is requesting
            context: Additional context (project path, etc.)

        Returns:
            PermissionDecision with allowed, risk_level, reason
        """
        # Step 1: Classify risk
        risk = self.classify_risk(command, action_type)

        # Step 2: Check restricted paths for file operations
        if action_type in (ActionType.FILE_WRITE, ActionType.FILE_DELETE, ActionType.FILE_MOVE):
            path_risk = self._check_path_risk(command)
            risk = self._higher_risk(risk, path_risk)

        # Step 3: Apply policy
        decision = self._apply_policy(risk, command, agent)

        log.debug(f"Permission check: '{command[:50]}' → {risk} → {'allowed' if decision.allowed else 'blocked'}")
        return decision

    def classify_risk(self, command: str, action_type: str = ActionType.TERMINAL) -> str:
        """Classify the risk level of a command.

        Returns one of: safe, low, medium, high, dangerous
        """
        if action_type in (ActionType.SCREENSHOT, ActionType.FILE_READ, ActionType.SYSTEM):
            return RiskLevel.SAFE

        if action_type in (ActionType.MOUSE, ActionType.KEYBOARD, ActionType.BROWSER):
            return RiskLevel.LOW

        cmd = command.strip()

        # Check dangerous patterns first
        for pattern in DANGEROUS_COMMANDS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return RiskLevel.DANGEROUS

        # Check high risk
        for pattern in HIGH_RISK_COMMANDS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return RiskLevel.HIGH

        # Check medium risk
        for pattern in MEDIUM_RISK_COMMANDS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return RiskLevel.MEDIUM

        # Check safe patterns
        for pattern in SAFE_COMMANDS:
            if re.search(rf"^{pattern}\b", cmd, re.IGNORECASE):
                return RiskLevel.SAFE

        # Default to low for unknown commands
        return RiskLevel.LOW

    def _check_path_risk(self, command: str) -> str:
        """Check if a command touches restricted paths."""
        for restricted in RESTRICTED_PATHS:
            expanded = os.path.expanduser(restricted)
            if expanded in command or restricted in command:
                return RiskLevel.DANGEROUS
        return RiskLevel.SAFE

    def _higher_risk(self, a: str, b: str) -> str:
        """Return the higher of two risk levels."""
        order = [RiskLevel.SAFE, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.DANGEROUS]
        ai = order.index(a) if a in order else 0
        bi = order.index(b) if b in order else 0
        return order[max(ai, bi)]

    def _apply_policy(self, risk: str, command: str, agent: str) -> PermissionDecision:
        """Apply the permission policy for a given risk level."""
        # Check cache for previously approved commands
        cache_key = f"{command}:{agent}"
        if cache_key in self._approval_cache:
            return PermissionDecision(
                allowed=True,
                risk_level=risk,
                reason="Previously approved",
                approved_by="cache",
            )

        if self.mode == "permissive":
            if risk in (RiskLevel.SAFE, RiskLevel.LOW, RiskLevel.MEDIUM):
                return PermissionDecision(allowed=True, risk_level=risk, reason="Permissive mode")
            if risk == RiskLevel.HIGH:
                return PermissionDecision(
                    allowed=True, risk_level=risk,
                    reason="Permissive mode (high risk)",
                    requires_confirmation=True,
                )
            return PermissionDecision(
                allowed=False, risk_level=risk,
                reason="Even permissive mode blocks dangerous actions",
                requires_approval=True,
            )

        if self.mode == "strict":
            if risk in (RiskLevel.SAFE,):
                return PermissionDecision(allowed=True, risk_level=risk, reason="Strict mode: safe action")
            return PermissionDecision(
                allowed=False, risk_level=risk,
                reason="Strict mode: requires manual approval",
                requires_approval=True,
            )

        # Normal mode
        if risk in (RiskLevel.SAFE, RiskLevel.LOW):
            return PermissionDecision(
                allowed=True, risk_level=risk,
                reason=f"Auto-approved: {risk} risk",
                approved_by="auto",
            )

        if risk == RiskLevel.MEDIUM:
            return PermissionDecision(
                allowed=True, risk_level=risk,
                reason="Medium risk: allowed with notification",
                requires_confirmation=True,
                approved_by="notification",
            )

        if risk == RiskLevel.HIGH:
            return PermissionDecision(
                allowed=False, risk_level=risk,
                reason="High risk: requires explicit confirmation",
                requires_confirmation=True,
                requires_approval=True,
            )

        # DANGEROUS
        return PermissionDecision(
            allowed=False, risk_level=risk,
            reason="Dangerous: blocked unless manually approved",
            requires_approval=True,
        )

    def approve_command(self, command: str, agent: str = "") -> None:
        """Cache an approval for a specific command."""
        cache_key = f"{command}:{agent}"
        self._approval_cache[cache_key] = True
        log.info(f"Approved command: '{command[:50]}' for {agent}")

    def revoke_approval(self, command: str, agent: str = "") -> None:
        """Remove a cached approval."""
        cache_key = f"{command}:{agent}"
        self._approval_cache.pop(cache_key, None)

    def is_path_allowed(self, path: str) -> bool:
        """Check if a file path is in an allowed directory."""
        expanded = os.path.expanduser(path)
        abs_path = os.path.abspath(expanded)

        for restricted in RESTRICTED_PATHS:
            expanded_restricted = os.path.expanduser(restricted)
            if abs_path.startswith(os.path.abspath(expanded_restricted)):
                return False

        return True

    def get_stats(self) -> dict:
        """Get permission system statistics."""
        return {
            "mode": self.mode,
            "cached_approvals": len(self._approval_cache),
            "safe_dirs": len(self.safe_dirs),
            "restricted_paths": len(RESTRICTED_PATHS),
        }


# Module-level singleton
permission_system = PermissionSystem()
