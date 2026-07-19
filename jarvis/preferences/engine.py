"""Preference learning engine for JARVIS v5.4.0."""
import json
import logging
import os
import time
from typing import Dict, List, Optional, Any

from .models import Preference, PreferenceCategory, PreferenceProfile

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = os.path.join(os.path.expanduser("~"), ".jarvis", "memory_store")
PREFERENCES_FILE = "preferences.json"


class PreferenceEngine:
    """Persistent preference learning backed by JSON storage."""

    default_coding_prefs: Dict[str, str] = {
        "language": "python",
        "style": "clean",
        "testing": "pytest",
        "type_checking": "mypy",
        "linting": "ruff",
        "formatting": "ruff",
        "editor": "vscode",
        "vcs": "git",
    }

    default_hardware_prefs: Dict[str, str] = {
        "mcu": "esp32",
        "cad": "fusion360",
        "pcb": "kicad",
        "simulation": "ltspice",
        "ide": "platformio",
    }

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self._storage_dir = storage_dir or DEFAULT_STORAGE_DIR
        self._store_path = os.path.join(self._storage_dir, PREFERENCES_FILE)
        self._preferences: Dict[str, Preference] = {}
        self._loaded = False

    async def load(self) -> None:
        """Load preferences from disk."""
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._store_path):
            self._preferences = {}
            return
        try:
            with open(self._store_path, "r") as f:
                data = json.load(f)
            self._preferences = {
                k: Preference.from_dict(v) for k, v in data.items()
            }
            self._loaded = True
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load preferences: %s", exc)
            self._preferences = {}

    async def save(self) -> None:
        """Persist preferences to disk."""
        self._save()

    def _save(self) -> None:
        os.makedirs(self._storage_dir, exist_ok=True)
        data = {k: v.to_dict() for k, v in self._preferences.items()}
        try:
            with open(self._store_path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as exc:
            logger.error("Failed to save preferences: %s", exc)

    async def bootstrap(self) -> None:
        """Seed defaults if no preferences exist yet."""
        if self._preferences:
            return
        for k, v in self.default_coding_prefs.items():
            await self.learn("coding", k, v, confidence=0.9, source="bootstrap")
        for k, v in self.default_hardware_prefs.items():
            await self.learn("hardware", k, v, confidence=0.9, source="bootstrap")
        await self.save()

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def _key(self, category: str, key: str) -> str:
        return f"{category}::{key}"

    async def learn(
        self,
        category: str,
        key: str,
        value: str,
        confidence: float = 0.8,
        source: str = "",
        evidence: Optional[List[str]] = None,
    ) -> Preference:
        """Record or reinforce a user preference."""
        composite = self._key(category, key)
        existing = self._preferences.get(composite)
        if existing:
            existing.value = value
            existing.confidence = min(1.0, existing.confidence + 0.05)
            existing.times_reinforced += 1
            existing.last_seen = time.time()
            if evidence:
                existing.evidence.extend(evidence)
            if source:
                existing.source = source
            pref = existing
        else:
            pref = Preference(
                category=category,
                key=key,
                value=value,
                confidence=confidence,
                source=source,
                evidence=evidence or [],
            )
            self._preferences[composite] = pref
        await self.save()
        return pref

    async def reinforce(self, preference_id: str, delta: float = 0.05) -> Optional[Preference]:
        """Increase confidence of an existing preference."""
        for pref in self._preferences.values():
            if pref.id == preference_id:
                pref.confidence = min(1.0, pref.confidence + delta)
                pref.times_reinforced += 1
                pref.last_seen = time.time()
                await self.save()
                return pref
        return None

    async def get(self, category: str, key: str) -> Optional[Preference]:
        """Retrieve a single preference by category+key."""
        return self._preferences.get(self._key(category, key))

    async def get_by_category(self, category: str) -> List[Preference]:
        """Return all preferences in a category."""
        return [
            p for p in self._preferences.values() if p.category == category
        ]

    async def get_profile(self) -> Dict[str, PreferenceProfile]:
        """Return a profile per category with dominant values."""
        categories: Dict[str, List[Preference]] = {}
        for pref in self._preferences.values():
            categories.setdefault(pref.category, []).append(pref)

        profiles: Dict[str, PreferenceProfile] = {}
        for cat, prefs in categories.items():
            dominant: Dict[str, str] = {}
            for p in prefs:
                if p.key not in dominant:
                    dominant[p.key] = p.value
                else:
                    existing = next(
                        (x for x in prefs if x.key == p.key and x.value == dominant[p.key]),
                        None,
                    )
                    if existing and p.confidence > existing.confidence:
                        dominant[p.key] = p.value
            profiles[cat] = PreferenceProfile(
                category=cat,
                preferences=sorted(prefs, key=lambda p: p.confidence, reverse=True),
                dominant_values=dominant,
            )
        return profiles

    async def get_dominant(self, category: str) -> Optional[Preference]:
        """Return the highest-confidence preference in a category."""
        cat_prefs = await self.get_by_category(category)
        if not cat_prefs:
            return None
        return max(cat_prefs, key=lambda p: p.confidence)

    async def search(self, query: str) -> List[Preference]:
        """Simple substring search across keys, values, and categories."""
        q = query.lower()
        return [
            p for p in self._preferences.values()
            if q in p.key.lower()
            or q in p.value.lower()
            or q in p.category.lower()
        ]

    async def contradict(
        self,
        category: str,
        key: str,
        new_value: str,
        confidence: float = 0.8,
    ) -> Preference:
        """Update a preference with a contradicting value."""
        composite = self._key(category, key)
        existing = self._preferences.get(composite)
        if existing:
            existing.value = new_value
            existing.confidence = confidence
            existing.times_reinforced = 1
            existing.last_seen = time.time()
            existing.evidence.append(
                f"contradicted at {existing.last_seen}"
            )
            await self.save()
            return existing
        return await self.learn(category, key, new_value, confidence)

    async def forget(self, preference_id: str) -> bool:
        """Remove a preference by ID."""
        for composite, pref in list(self._preferences.items()):
            if pref.id == preference_id:
                del self._preferences[composite]
                await self.save()
                return True
        return False

    async def get_coding_preferences(self) -> Dict[str, str]:
        """Shorthand: return all coding preferences as key->value."""
        prefs = await self.get_by_category("coding")
        return {p.key: p.value for p in prefs}

    async def get_hardware_preferences(self) -> Dict[str, str]:
        """Shorthand: return all hardware preferences as key->value."""
        prefs = await self.get_by_category("hardware")
        return {p.key: p.value for p in prefs}

    async def get_all(self) -> List[Preference]:
        """Return all preferences."""
        return list(self._preferences.values())
