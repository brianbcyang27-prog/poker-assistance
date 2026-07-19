"""Lesson engine — extract, store, and apply lessons from errors and experience."""
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from .models import Lesson

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = os.path.join(os.path.expanduser("~"), ".jarvis", "memory_store")
LESSONS_FILE = "lessons.json"


class LessonEngine:
    """Persistent lesson storage backed by JSON."""

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self._storage_dir = storage_dir or DEFAULT_STORAGE_DIR
        self._store_path = os.path.join(self._storage_dir, LESSONS_FILE)
        self._lessons: Dict[str, Lesson] = {}
        self._loaded = False

    async def load(self) -> None:
        """Load lessons from disk."""
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._store_path):
            self._lessons = {}
            self._loaded = True
            return
        try:
            with open(self._store_path, "r") as f:
                data = json.load(f)
            self._lessons = {
                k: Lesson.from_dict(v) for k, v in data.items()
            }
            self._loaded = True
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load lessons: %s", exc)
            self._lessons = {}
        self._loaded = True

    async def save(self) -> None:
        """Persist lessons to disk."""
        self._save()

    def _save(self) -> None:
        os.makedirs(self._storage_dir, exist_ok=True)
        data = {k: v.to_dict() for k, v in self._lessons.items()}
        try:
            with open(self._store_path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as exc:
            logger.error("Failed to save lessons: %s", exc)

    async def learn(
        self,
        error_id: str,
        description: str,
        trigger: str,
        action: str,
        category: str = "general",
        confidence: float = 0.8,
    ) -> Lesson:
        """Extract and store a new lesson."""
        lesson = Lesson(
            category=category,
            description=description,
            trigger=trigger,
            action=action,
            confidence=confidence,
        )
        self._lessons[lesson.id] = lesson
        await self.save()
        logger.info("Lesson learned: %s (category=%s)", description[:60], category)
        return lesson

    async def get_applicable_lessons(
        self, context: Dict[str, Any]
    ) -> List[Lesson]:
        """Find lessons relevant to the current context."""
        applicable: List[Lesson] = []
        context_text = " ".join(str(v) for v in context.values()).lower()

        for lesson in self._lessons.values():
            trigger_lower = lesson.trigger.lower()
            category_lower = lesson.category.lower()
            if (
                trigger_lower in context_text
                or any(word in context_text for word in category_lower.split())
            ):
                applicable.append(lesson)

        applicable.sort(key=lambda l: l.confidence, reverse=True)
        return applicable

    async def apply_lesson(self, lesson_id: str) -> Dict[str, Any]:
        """Mark a lesson as applied and increment its usage count."""
        lesson = self._lessons.get(lesson_id)
        if not lesson:
            return {"ok": False, "error": f"Lesson {lesson_id} not found"}

        lesson.times_applied += 1
        lesson.confidence = min(1.0, lesson.confidence + 0.05)
        await self.save()

        return {
            "ok": True,
            "lesson_id": lesson_id,
            "times_applied": lesson.times_applied,
            "action": lesson.action,
        }

    async def get_by_category(self, category: str) -> List[Lesson]:
        """Return all lessons in a category."""
        return [
            l for l in self._lessons.values()
            if l.category == category
        ]

    async def get_all(self) -> List[Lesson]:
        """Return all lessons."""
        return list(self._lessons.values())

    async def search(self, query: str) -> List[Lesson]:
        """Search lessons by query string."""
        q_lower = query.lower()
        return [
            l for l in self._lessons.values()
            if q_lower in l.description.lower()
            or q_lower in l.trigger.lower()
            or q_lower in l.action.lower()
            or q_lower in l.category.lower()
        ]
