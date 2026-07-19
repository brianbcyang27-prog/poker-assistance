"""Memory privacy manager for JARVIS v5.4.0."""
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from .models import AuditEntry, ExportData, MemoryPrivacySettings

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = os.path.join(os.path.expanduser("~"), ".jarvis", "memory_store")
PRIVACY_FILE = "privacy.json"


class MemoryPrivacyManager:
    """Persistent memory privacy controls backed by JSON storage."""

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self._storage_dir = storage_dir or DEFAULT_STORAGE_DIR
        self._store_path = os.path.join(self._storage_dir, PRIVACY_FILE)
        self._settings = MemoryPrivacySettings()
        self._audit_log: List[AuditEntry] = []
        self._loaded = False

    async def load(self) -> None:
        """Load settings and audit log from disk."""
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._store_path):
            return
        try:
            with open(self._store_path, "r") as f:
                data = json.load(f)
            self._settings = MemoryPrivacySettings.from_dict(
                data.get("settings", {})
            )
            self._audit_log = [
                AuditEntry.from_dict(e) for e in data.get("audit_log", [])
            ]
            self._loaded = True
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load privacy data: %s", exc)

    async def save(self) -> None:
        """Persist settings and audit log to disk."""
        self._save()

    def _save(self) -> None:
        os.makedirs(self._storage_dir, exist_ok=True)
        data = {
            "settings": self._settings.to_dict(),
            "audit_log": [e.to_dict() for e in self._audit_log],
        }
        try:
            with open(self._store_path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as exc:
            logger.error("Failed to save privacy data: %s", exc)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    async def get_settings(self) -> MemoryPrivacySettings:
        """Return current privacy settings."""
        return self._settings

    async def update_settings(self, **kwargs: Any) -> MemoryPrivacySettings:
        """Update settings by keyword arguments."""
        for k, v in kwargs.items():
            if hasattr(self._settings, k):
                setattr(self._settings, k, v)
        await self.save()
        return self._settings

    async def is_paused(self) -> bool:
        """Check if memory collection is paused."""
        return self._settings.paused

    async def pause(self) -> Dict[str, Any]:
        """Pause memory collection."""
        self._settings.paused = True
        await self.log_audit("pause", "memory", "Memory collection paused")
        await self.save()
        return {"paused": True}

    async def resume(self) -> Dict[str, Any]:
        """Resume memory collection."""
        self._settings.paused = False
        await self.log_audit("resume", "memory", "Memory collection resumed")
        await self.save()
        return {"paused": False}

    # ------------------------------------------------------------------
    # Entity filtering
    # ------------------------------------------------------------------

    async def is_allowed(self, entity_type: str, entity_data: str) -> bool:
        """Check if an entity can be stored based on privacy rules."""
        if self._settings.paused:
            return False

        data_lower = entity_data.lower()

        for topic in self._settings.forgotten_topics:
            if topic.lower() in data_lower:
                return False

        for project in self._settings.private_projects:
            if project.lower() in data_lower:
                return False

        if entity_type in self._settings.encrypted_categories:
            return True  # allowed but will be encrypted

        return True

    # ------------------------------------------------------------------
    # Private projects
    # ------------------------------------------------------------------

    async def add_private_project(self, project_name: str) -> Dict[str, Any]:
        """Add a project to the private list."""
        if project_name not in self._settings.private_projects:
            self._settings.private_projects.append(project_name)
            await self.log_audit(
                "view", f"project:{project_name}", "Added to private projects"
            )
            await self.save()
        return {"added": project_name, "private_projects": self._settings.private_projects}

    async def remove_private_project(self, project_name: str) -> Dict[str, Any]:
        """Remove a project from the private list."""
        if project_name in self._settings.private_projects:
            self._settings.private_projects.remove(project_name)
            await self.log_audit(
                "delete", f"project:{project_name}", "Removed from private projects"
            )
            await self.save()
        return {"removed": project_name, "private_projects": self._settings.private_projects}

    # ------------------------------------------------------------------
    # Forgotten topics
    # ------------------------------------------------------------------

    async def add_forgotten_topic(self, topic: str) -> Dict[str, Any]:
        """Add a topic to the forgotten list."""
        if topic not in self._settings.forgotten_topics:
            self._settings.forgotten_topics.append(topic)
            await self.log_audit(
                "forget", f"topic:{topic}", "Added to forgotten topics"
            )
            await self.save()
        return {"added": topic, "forgotten_topics": self._settings.forgotten_topics}

    async def is_forgotten(self, topic: str) -> bool:
        """Check if a topic is marked as forgotten."""
        return topic.lower() in [t.lower() for t in self._settings.forgotten_topics]

    async def forget_topic(self, topic: str) -> Dict[str, Any]:
        """Mark a topic as forgotten."""
        return await self.add_forgotten_topic(topic)

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------

    async def log_audit(self, action: str, target: str, details: str = "") -> AuditEntry:
        """Log an audit entry."""
        entry = AuditEntry(
            action=action,
            target=target,
            details=details,
        )
        self._audit_log.append(entry)
        if self._settings.audit_enabled:
            await self.save()
        return entry

    async def get_audit_log(self, limit: int = 50) -> List[AuditEntry]:
        """Return the most recent audit entries."""
        return list(reversed(self._audit_log[-limit:]))

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    async def export_all(
        self,
        knowledge_graph: Any = None,
        preference_engine: Any = None,
        decision_engine: Any = None,
        timeline_engine: Any = None,
    ) -> ExportData:
        """Export all memory data for portability."""
        await self.log_audit("export", "all", "Full memory export initiated")

        entities: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []
        preferences: List[Dict[str, Any]] = []
        decisions: List[Dict[str, Any]] = []
        timeline: List[Dict[str, Any]] = []

        if knowledge_graph is not None:
            if hasattr(knowledge_graph, "get_all_entities"):
                raw = knowledge_graph.get_all_entities()
                if hasattr(raw, "__await__"):
                    raw = await raw
                entities = [
                    e.to_dict() if hasattr(e, "to_dict") else e
                    for e in (raw or [])
                ]
            if hasattr(knowledge_graph, "get_all_relationships"):
                raw = knowledge_graph.get_all_relationships()
                if hasattr(raw, "__await__"):
                    raw = await raw
                relationships = [
                    r.to_dict() if hasattr(r, "to_dict") else r
                    for r in (raw or [])
                ]

        if preference_engine is not None:
            if hasattr(preference_engine, "get_all"):
                raw = preference_engine.get_all()
                if hasattr(raw, "__await__"):
                    raw = await raw
                preferences = [
                    p.to_dict() if hasattr(p, "to_dict") else p
                    for p in (raw or [])
                ]

        if decision_engine is not None:
            if hasattr(decision_engine, "get_all"):
                raw = decision_engine.get_all()
                if hasattr(raw, "__await__"):
                    raw = await raw
                decisions = [
                    d.to_dict() if hasattr(d, "to_dict") else d
                    for d in (raw or [])
                ]

        if timeline_engine is not None:
            if hasattr(timeline_engine, "get_recent"):
                raw = timeline_engine.get_recent(1000)
                if hasattr(raw, "__await__"):
                    raw = await raw
                timeline = [
                    t.to_dict() if hasattr(t, "to_dict") else t
                    for t in (raw or [])
                ]

        export = ExportData(
            entities=entities,
            relationships=relationships,
            preferences=preferences,
            decisions=decisions,
            timeline=timeline,
        )
        await self.log_audit(
            "export", "all",
            f"Exported {len(entities)} entities, {len(relationships)} relationships, "
            f"{len(preferences)} preferences, {len(decisions)} decisions",
        )
        return export
