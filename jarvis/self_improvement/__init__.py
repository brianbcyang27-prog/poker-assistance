"""JARVIS Self-Improvement — Self debugging, error memory, recovery, and lessons."""

from .models import ErrorRecord, RecoveryPlan, Lesson, ErrorSeverity, RecoveryAction
from .error_memory import ErrorMemory
from .recovery import AutoRecovery
from .lessons import LessonEngine

__all__ = [
    "ErrorRecord",
    "RecoveryPlan",
    "Lesson",
    "ErrorSeverity",
    "RecoveryAction",
    "ErrorMemory",
    "AutoRecovery",
    "LessonEngine",
]
