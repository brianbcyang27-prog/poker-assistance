"""V10 permission manager — maps LEVEL 0-3 onto the existing permission systems.

The V10 tool layer defines four execution levels (docs/JARVIS_V10_MASTER_PLAN.md):

    LEVEL 0  SAFE          fully automatic, no confirmation
    LEVEL 1  LOW_RISK      automatic, audited
    LEVEL 2  CONFIRMATION  requires user confirmation before execution
    LEVEL 3  HIGH_RISK     blocked unless explicitly approved

This module adapts those levels onto the two systems that already exist in the
codebase and must keep working:

* ``jarvis.core.permissions.permission_center`` — Trinity capability gates
  (ALLOW / ASK / DENY for files, terminal, browser, network, ...)
* ``jarvis.computer.permissions.permission_system`` — RiskLevel classification
  of exact commands and paths (safe / low / medium / high / dangerous)

The manager never bypasses either system — it composes them. Resolution order:

1. **Trinity gate** — a DENY capability is a hard stop; an ungranted ASK
   capability requires consent (the executor must prompt and grant, then retry).
2. **Risk gate** — for terminal/file-style actions, the exact command or path is
   classified through ``permission_system`` and its RiskLevel is mapped back to
   a LEVEL (``dangerous`` ⇒ LEVEL 3).
3. **LEVEL policy** — the effective LEVEL (tool level ∪ risk-derived level)
   decides whether the action needs confirmation (2) or explicit approval (3).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from jarvis.computer.actions import ActionType
from jarvis.computer.permissions import (
    PermissionSystem,
)
from jarvis.computer.permissions import (
    permission_system as _computer_permission_system,
)
from jarvis.core.permissions import (
    PermissionCenter,
    TrinityState,
)
from jarvis.core.permissions import (
    permission_center as _core_permission_center,
)
from jarvis.tools.base import ToolSpec

# --- V10 execution levels -------------------------------------------------

LEVEL_SAFE = 0
LEVEL_LOW_RISK = 1
LEVEL_CONFIRMATION = 2
LEVEL_HIGH_RISK = 3

LEVEL_NAMES = {
    LEVEL_SAFE: "safe",
    LEVEL_LOW_RISK: "low_risk",
    LEVEL_CONFIRMATION: "confirmation",
    LEVEL_HIGH_RISK: "high_risk",
}

# Computer RiskLevel (jarvis.computer.permissions) → V10 LEVEL.
RISK_TO_LEVEL = {
    "safe": LEVEL_SAFE,
    "low": LEVEL_LOW_RISK,
    "medium": LEVEL_CONFIRMATION,
    "high": LEVEL_HIGH_RISK,
    "dangerous": LEVEL_HIGH_RISK,
}


def level_name(level: int) -> str:
    """Return the LEVEL_NAMES label for a clamped LEVEL 0-3."""
    return LEVEL_NAMES[max(LEVEL_SAFE, min(LEVEL_HIGH_RISK, level))]


@dataclass
class ToolPermissionDecision:
    """Result of a V10 permission check for a single tool invocation.

    Semantics for the executor:

    * ``allowed=False`` + ``denied_by="trinity"`` + ``requires_confirmation``
      → the capability is ASK and no grant is active; prompt the user and
      ``permission_manager.grant(capability)`` on consent, then re-check.
    * ``allowed=False`` + ``requires_approval=True`` → LEVEL 3; blocked until an
      explicit approval flow exists and approves.
    * ``allowed=True`` + ``requires_confirmation=True`` → LEVEL 2; run only
      after the user confirms this specific action.
    """

    allowed: bool
    level: int
    level_name: str
    requires_confirmation: bool
    requires_approval: bool
    denied_by: str = ""  # "trinity" | "risk" | "policy" | ""
    reason: str = ""
    trinity_state: str = ""  # TrinityState value, "" when no capability checked
    risk_level: str = ""  # RiskLevel value, "" when no command checked
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize for action logs and the executor."""
        return {
            "allowed": self.allowed,
            "level": self.level,
            "level_name": self.level_name,
            "requires_confirmation": self.requires_confirmation,
            "requires_approval": self.requires_approval,
            "denied_by": self.denied_by,
            "reason": self.reason,
            "trinity_state": self.trinity_state,
            "risk_level": self.risk_level,
            "metadata": self.metadata,
        }


class PermissionManager:
    """Composes Trinity capability gates and RiskLevel classification into LEVEL 0-3.

    Injectable for tests: pass fakes for ``permission_center`` / ``permission_system``
    to avoid touching the real singletons.
    """

    def __init__(
        self,
        permission_center: PermissionCenter | None = None,
        permission_system: PermissionSystem | None = None,
    ) -> None:
        self._center = (
            permission_center if permission_center is not None else _core_permission_center
        )
        self._system = (
            permission_system if permission_system is not None else _computer_permission_system
        )

    # -- public API ---------------------------------------------------------

    def check(
        self,
        level: int,
        capability: str = "",
        command: str = "",
        risk_level: str = "",
        action_type: str = ActionType.TERMINAL,
        agent: str = "",
        context: dict | None = None,
    ) -> ToolPermissionDecision:
        """Resolve a LEVEL (plus optional capability / command) to a decision.

        Args:
            level: The tool's declared LEVEL 0-3.
            capability: Trinity capability name (e.g. "terminal", "browser").
            command: Exact command / path to classify through the risk system.
            risk_level: Optional pre-classified RiskLevel (e.g. from ToolSpec).
            action_type: ActionType for the risk system (default TERMINAL).
            agent: Which agent is requesting (for the risk audit trail).
            context: Additional context (project path, etc.).

        Returns:
            ToolPermissionDecision — never raises on permission lookups.
        """
        level = max(LEVEL_SAFE, min(LEVEL_HIGH_RISK, int(level)))
        effective = max(level, RISK_TO_LEVEL.get(risk_level, level))
        requires_confirmation = False
        requires_approval = False
        reason = ""
        trinity_state = ""
        classified_risk = ""
        metadata: dict = {}

        # 1. Trinity capability gate (fail closed on lookup errors).
        if capability and self._center is not None:
            try:
                granted, state = self._center.check(capability)
            except Exception as exc:  # noqa: BLE001 — a permission lookup must never crash the executor
                return self._deny(
                    effective,
                    reason=f"Trinity lookup failed for '{capability}': {exc}",
                    denied_by="trinity",
                    trinity_state="deny",
                )
            trinity_state = state
            if state == TrinityState.DENY:
                return self._deny(
                    effective,
                    reason=f"Trinity denies capability '{capability}'",
                    denied_by="trinity",
                    trinity_state=trinity_state,
                )
            if not granted:
                return self._deny(
                    effective,
                    reason=f"Trinity requires consent for '{capability}' (state=ASK)",
                    denied_by="trinity",
                    trinity_state=trinity_state,
                    requires_confirmation=True,
                )
            metadata["trinity"] = {"capability": capability, "state": trinity_state}

        # 2. Risk gate for exact commands / paths.
        if command and self._system is not None:
            decision = self._system.check(
                command=command,
                action_type=action_type,
                agent=agent,
                context=context,
            )
            classified_risk = decision.risk_level
            effective = max(effective, RISK_TO_LEVEL.get(classified_risk, effective))
            metadata["computer_decision"] = asdict(decision)
            if not decision.allowed:
                return self._deny(
                    effective,
                    reason=decision.reason,
                    denied_by="risk",
                    risk_level=classified_risk,
                    requires_confirmation=decision.requires_confirmation,
                    requires_approval=decision.requires_approval,
                    metadata=metadata,
                )
            requires_confirmation = requires_confirmation or decision.requires_confirmation
            requires_approval = requires_approval or decision.requires_approval

        # 3. LEVEL policy on the effective LEVEL.
        if effective >= LEVEL_HIGH_RISK:
            return self._deny(
                effective,
                reason="LEVEL 3 (high_risk): blocked unless explicitly approved",
                denied_by="policy",
                trinity_state=trinity_state,
                risk_level=classified_risk,
                requires_approval=True,
                metadata=metadata,
            )
        if effective == LEVEL_CONFIRMATION:
            requires_confirmation = True
            reason = "LEVEL 2 (confirmation): requires user confirmation"

        return ToolPermissionDecision(
            allowed=True,
            level=effective,
            level_name=level_name(effective),
            requires_confirmation=requires_confirmation,
            requires_approval=requires_approval,
            denied_by="",
            reason=reason,
            trinity_state=trinity_state,
            risk_level=classified_risk,
            metadata=metadata,
        )

    def check_tool(
        self,
        spec: ToolSpec,
        command: str = "",
        action_type: str = ActionType.TERMINAL,
        agent: str = "",
        context: dict | None = None,
    ) -> ToolPermissionDecision:
        """Resolve a decision from a ToolSpec (declared level, capability, risk).

        The spec's ``risk_level`` feeds the effective LEVEL computation even when
        no exact command is provided.
        """
        return self.check(
            level=spec.permission_level,
            capability=spec.capability or "",
            command=command,
            risk_level=spec.risk_level or "",
            action_type=action_type,
            agent=agent,
            context=context,
        )

    # -- consent passthroughs ------------------------------------------------

    def grant(self, capability: str, duration: float = 300) -> bool:
        """Temporarily grant a Trinity capability (used after ASK consent)."""
        if self._center is None:
            return False
        return self._center.grant(capability, duration)

    def approve_command(self, command: str, agent: str = "") -> None:
        """Approve a command in the computer permission system."""
        if self._system is not None:
            self._system.approve_command(command, agent)

    def is_path_allowed(self, path: str) -> bool:
        """True when *path* is outside the restricted paths."""
        if self._system is None:
            return True
        return self._system.is_path_allowed(path)

    # -- helpers -------------------------------------------------------------

    def _deny(
        self,
        level: int,
        *,
        reason: str,
        denied_by: str,
        trinity_state: str = "",
        risk_level: str = "",
        requires_confirmation: bool = False,
        requires_approval: bool = False,
        metadata: dict | None = None,
    ) -> ToolPermissionDecision:
        return ToolPermissionDecision(
            allowed=False,
            level=level,
            level_name=level_name(level),
            requires_confirmation=requires_confirmation,
            requires_approval=requires_approval,
            denied_by=denied_by,
            reason=reason,
            trinity_state=trinity_state,
            risk_level=risk_level,
            metadata=metadata or {},
        )


# Module-level singleton — the one the executor will import.
permission_manager = PermissionManager()

__all__ = [
    "LEVEL_SAFE",
    "LEVEL_LOW_RISK",
    "LEVEL_CONFIRMATION",
    "LEVEL_HIGH_RISK",
    "LEVEL_NAMES",
    "RISK_TO_LEVEL",
    "level_name",
    "ToolPermissionDecision",
    "PermissionManager",
    "permission_manager",
]
