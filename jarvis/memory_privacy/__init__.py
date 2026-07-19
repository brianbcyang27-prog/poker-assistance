"""JARVIS Memory Privacy — controls what gets remembered and forgotten.

Usage:
    manager = MemoryPrivacyManager()
    await manager.add_forgotten_topic("passwords")
    await manager.add_private_project("secret-project")
    is_ok = await manager.is_allowed("note", "meeting notes")
    export = await manager.export_all(knowledge_graph=kg)
"""

from .manager import MemoryPrivacyManager
from .models import (
    AuditAction,
    AuditEntry,
    ExportData,
    MemoryPrivacySettings,
    PrivacyLevel,
)

__all__ = [
    "MemoryPrivacyManager",
    "AuditAction",
    "AuditEntry",
    "ExportData",
    "MemoryPrivacySettings",
    "PrivacyLevel",
]
