"""Privacy Controls data models."""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PrivacySettings:
    """Per-category observation toggles.

    All fields default to ``False`` (privacy-preserving) except
    *application_monitoring* and *notification_level* / *data_retention_days*
    which have slightly more permissive defaults.
    """
    application_monitoring: bool = True
    browser_monitoring: bool = False
    file_monitoring: bool = False
    calendar_access: bool = False
    email_access: bool = False
    clipboard_monitoring: bool = False
    microphone_access: bool = False
    camera_access: bool = False
    location_access: bool = False
    notification_level: str = "suggestions"
    data_retention_days: int = 90

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "application_monitoring": self.application_monitoring,
            "browser_monitoring": self.browser_monitoring,
            "file_monitoring": self.file_monitoring,
            "calendar_access": self.calendar_access,
            "email_access": self.email_access,
            "clipboard_monitoring": self.clipboard_monitoring,
            "microphone_access": self.microphone_access,
            "camera_access": self.camera_access,
            "location_access": self.location_access,
            "notification_level": self.notification_level,
            "data_retention_days": self.data_retention_days,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PrivacySettings":
        return cls(
            application_monitoring=bool(data.get("application_monitoring", True)),
            browser_monitoring=bool(data.get("browser_monitoring", False)),
            file_monitoring=bool(data.get("file_monitoring", False)),
            calendar_access=bool(data.get("calendar_access", False)),
            email_access=bool(data.get("email_access", False)),
            clipboard_monitoring=bool(data.get("clipboard_monitoring", False)),
            microphone_access=bool(data.get("microphone_access", False)),
            camera_access=bool(data.get("camera_access", False)),
            location_access=bool(data.get("location_access", False)),
            notification_level=str(data.get("notification_level", "suggestions")),
            data_retention_days=int(data.get("data_retention_days", 90)),
        )


@dataclass
class AuditEntry:
    """A single observation audit record."""
    timestamp: str
    category: str
    action: str
    detail: str
    allowed: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "category": self.category,
            "action": self.action,
            "detail": self.detail,
            "allowed": self.allowed,
        }
