"""Computer control module — JARVIS's Hands.

v4.2.0: Safe computer interaction through a permission-gated manager.

Architecture:
    Agent → ComputerManager → Permission Check → Execution → Logging → Memory

Every computer action goes through the manager.
Workers NEVER directly control the OS.
"""

from .actions import RiskLevel, ActionStatus, ActionType, ActionResult, ActionRecord
from .permissions import PermissionSystem, PermissionDecision, permission_system
from .sandbox import Sandbox, SandboxConfig, SandboxResult, default_sandbox
from .observer import ScreenObserver, ScreenState, WindowInfo, observer
from .manager import ComputerManager, computer_manager
from .providers import platform_provider

__all__ = [
    # Models
    "RiskLevel", "ActionStatus", "ActionType", "ActionResult", "ActionRecord",
    # Permissions
    "PermissionSystem", "PermissionDecision", "permission_system",
    # Sandbox
    "Sandbox", "SandboxConfig", "SandboxResult", "default_sandbox",
    # Observer
    "ScreenObserver", "ScreenState", "WindowInfo", "observer",
    # Manager
    "ComputerManager", "computer_manager",
    # Provider
    "platform_provider",
]
