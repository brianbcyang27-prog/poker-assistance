"""Computer control module — JARVIS's Hands.

v4.2.0: Safe computer interaction through a permission-gated manager.
v4.4.0: Accessibility intelligence — semantic UI control via element inspection.
v4.5.0: Vision Core — multimodal perception with accessibility-first fallback.

Architecture:
    Agent → ComputerManager → Permission Check → Execution → Logging → Memory

Multi-perception (v4.5.0):
    smart.click("Export")  → tries accessibility first, falls back to vision
    smart.type("search", "query") → accessibility first, vision fallback
"""

from .actions import RiskLevel, ActionStatus, ActionType, ActionResult, ActionRecord
from .permissions import PermissionSystem, PermissionDecision, permission_system
from .sandbox import Sandbox, SandboxConfig, SandboxResult, default_sandbox
from .observer import ScreenObserver, ScreenState, WindowInfo, observer
from .manager import ComputerManager, computer_manager
from .providers import platform_provider
from .accessibility import AccessibilityManager, accessibility_manager

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
    # Accessibility (v4.4.0)
    "AccessibilityManager", "accessibility_manager",
]
