"""Decision memory engine for JARVIS v5.4.0."""

import json
import logging
import os

from .models import Decision, DecisionQuery

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = os.path.join(os.path.expanduser("~"), ".jarvis", "memory_store")
DECISIONS_FILE = "decisions.json"


class DecisionEngine:
    """Persistent decision memory backed by JSON storage."""

    def __init__(self, storage_dir: str | None = None) -> None:
        self._storage_dir = storage_dir or DEFAULT_STORAGE_DIR
        self._store_path = os.path.join(self._storage_dir, DECISIONS_FILE)
        self._decisions: dict[str, Decision] = {}
        self._loaded = False

    async def load(self) -> None:
        """Load decisions from disk."""
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._store_path):
            self._decisions = {}
            return
        try:
            with open(self._store_path) as f:
                data = json.load(f)
            self._decisions = {k: Decision.from_dict(v) for k, v in data.items()}
            self._loaded = True
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load decisions: %s", exc)
            self._decisions = {}

    async def save(self) -> None:
        """Persist decisions to disk."""
        self._save()

    def _save(self) -> None:
        os.makedirs(self._storage_dir, exist_ok=True)
        data = {k: v.to_dict() for k, v in self._decisions.items()}
        try:
            with open(self._store_path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as exc:
            logger.error("Failed to save decisions: %s", exc)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    async def record(
        self,
        title: str,
        description: str = "",
        reason: str = "",
        alternatives: list[str] | None = None,
        chosen_option: str = "",
        impact: str = "medium",
        related_entities: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> Decision:
        """Record a new decision."""
        decision = Decision(
            title=title,
            description=description,
            reason=reason,
            alternatives=alternatives or [],
            chosen_option=chosen_option,
            impact=impact,
            related_entities=related_entities or [],
            tags=tags or [],
        )
        self._decisions[decision.id] = decision
        await self.save()
        return decision

    async def get(self, decision_id: str) -> Decision | None:
        """Retrieve a decision by ID."""
        return self._decisions.get(decision_id)

    async def query(self, q: DecisionQuery) -> list[Decision]:
        """Query decisions with filters."""
        results: list[Decision] = []
        for d in self._decisions.values():
            if q.status and d.status != q.status:
                continue
            if q.impact and d.impact != q.impact:
                continue
            if q.tags and not any(t in d.tags for t in q.tags):
                continue
            if q.related_entity and q.related_entity not in d.related_entities:
                continue
            if q.start_date and d.date < q.start_date:
                continue
            if q.end_date and d.date > q.end_date:
                continue
            results.append(d)
        results.sort(key=lambda d: d.timestamp, reverse=True)
        return results[: q.limit]

    async def update_outcome(self, decision_id: str, outcome: str) -> Decision | None:
        """Update the outcome of a decision."""
        d = self._decisions.get(decision_id)
        if not d:
            return None
        d.outcome = outcome
        await self.save()
        return d

    async def supersede(
        self,
        decision_id: str,
        new_title: str,
        new_reason: str,
        new_chosen: str,
    ) -> Decision:
        """Mark old decision as superseded, create new one."""
        old = self._decisions.get(decision_id)
        if old:
            old.status = "superseded"

        new = Decision(
            title=new_title,
            reason=new_reason,
            chosen_option=new_chosen,
            related_entities=old.related_entities if old else [],
            tags=old.tags if old else [],
        )
        if old:
            old.superseded_by = new.id
        self._decisions[new.id] = new
        await self.save()
        return new

    async def reverse(self, decision_id: str, reason: str = "") -> Decision | None:
        """Mark a decision as reversed."""
        d = self._decisions.get(decision_id)
        if not d:
            return None
        d.status = "reversed"
        if reason:
            d.outcome = f"Reversed: {reason}"
        await self.save()
        return d

    async def why(self, entity_id: str) -> list[Decision]:
        """Find all active decisions related to an entity."""
        return [
            d
            for d in self._decisions.values()
            if entity_id in d.related_entities and d.status == "active"
        ]

    async def get_active(self) -> list[Decision]:
        """Return all active decisions."""
        return [d for d in self._decisions.values() if d.status == "active"]

    async def get_by_impact(self, impact: str) -> list[Decision]:
        """Return decisions filtered by impact level."""
        return [d for d in self._decisions.values() if d.impact == impact]

    async def get_recent(self, n: int = 10) -> list[Decision]:
        """Return the N most recent decisions."""
        sorted_d = sorted(self._decisions.values(), key=lambda d: d.timestamp, reverse=True)
        return sorted_d[:n]

    async def search(self, query: str) -> list[Decision]:
        """Simple substring search across titles, descriptions, and reasons."""
        q = query.lower()
        return [
            d
            for d in self._decisions.values()
            if q in d.title.lower()
            or q in d.description.lower()
            or q in d.reason.lower()
            or q in d.chosen_option.lower()
        ]

    async def get_all(self) -> list[Decision]:
        """Return all decisions."""
        return list(self._decisions.values())
