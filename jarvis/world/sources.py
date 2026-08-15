"""Persistent state for the world webcam monitor.

Sources, config and event history live in ~/.jarvis/world_state.json so the
monitor survives server restarts. Default sources are pre-registered but ship
disabled — the user enables them or adds their own camera URLs from the UI.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

STATE_FILE = Path.home() / ".jarvis" / "world_state.json"

MAX_EVENTS = 100
MAX_SOURCES = 50

ALLOWED_KINDS = ("highway", "landscape", "live", "other")

DEFAULT_THRESHOLDS = {"persons": 4, "vehicles": 6}

# Documented public webcam endpoints. These cannot be verified live from every
# network, so they ship disabled — flip them on (or add your own) in the UI.
DEFAULT_SOURCES = [
    {
        "id": "nyc-brooklyn-bridge",
        "name": "Brooklyn Bridge (NYC DOT)",
        "kind": "highway",
        "location": "New York City, NY",
        "image_url": "https://webcams.nyctmc.org/images/cameras/120/image.jpg",
        "enabled": False,
        "thresholds": dict(DEFAULT_THRESHOLDS),
    },
    {
        "id": "nyc-times-square",
        "name": "Times Square (NYC DOT)",
        "kind": "highway",
        "location": "New York City, NY",
        "image_url": "https://webcams.nyctmc.org/images/cameras/50/image.jpg",
        "enabled": False,
        "thresholds": {"persons": 6, "vehicles": 4},
    },
    {
        "id": "wsdot-snoqualmie-pass",
        "name": "I-90 Snoqualmie Pass (WSDOT)",
        "kind": "landscape",
        "location": "Snoqualmie Pass, WA",
        "image_url": "https://images.wsdot.wa.gov/nw/009vc12300.jpg",
        "enabled": False,
        "thresholds": dict(DEFAULT_THRESHOLDS),
    },
    {
        "id": "wsdot-skykomish",
        "name": "US 2 Skykomish (WSDOT)",
        "kind": "landscape",
        "location": "Skykomish, WA",
        "image_url": "https://images.wsdot.wa.gov/nw/005vc00044.jpg",
        "enabled": False,
        "thresholds": dict(DEFAULT_THRESHOLDS),
    },
]


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
        except (ValueError, OSError):
            state = {}
    else:
        state = {}
    state.setdefault("config", {"interval": 120, "cooldown": 600, "imessage_target": None})
    state.setdefault("sources", {})
    state.setdefault("events", [])
    return state


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def _ensure_defaults(state: dict) -> None:
    """Register default sources (by id) so disabling persists; skip existing ids."""
    for source in DEFAULT_SOURCES:
        if source["id"] not in state["sources"]:
            state["sources"][source["id"]] = source


def list_sources() -> list[dict]:
    state = _load_state()
    _ensure_defaults(state)
    _save_state(state)
    return sorted(state["sources"].values(), key=lambda s: s.get("name", ""))


def get_source(source_id: str) -> dict | None:
    state = _load_state()
    _ensure_defaults(state)
    return state["sources"].get(source_id)


def add_source(
    name: str,
    kind: str,
    location: str,
    image_url: str,
    thresholds: dict | None = None,
) -> dict | None:
    """Add a source; returns the created source or None if invalid/over cap."""
    kind = (kind or "live").strip().lower()
    if kind not in ALLOWED_KINDS:
        kind = "other"
    name = (name or "").strip()
    if not name:
        return None
    state = _load_state()
    if len(state["sources"]) >= MAX_SOURCES:
        return None
    source = {
        "id": uuid4().hex[:8],
        "name": name[:120],
        "kind": kind,
        "location": (location or "").strip()[:120],
        "image_url": image_url.strip(),
        "enabled": False,
        "thresholds": dict(thresholds or DEFAULT_THRESHOLDS),
    }
    state["sources"][source["id"]] = source
    _save_state(state)
    return source


def update_source(source_id: str, **changes) -> dict | None:
    """Apply partial changes (name/kind/location/image_url/enabled/thresholds)."""
    state = _load_state()
    source = state["sources"].get(source_id)
    if source is None:
        return None
    for key, value in changes.items():
        if value is None:
            continue
        if key == "kind" and value not in ALLOWED_KINDS:
            continue
        if key == "thresholds" and isinstance(value, dict):
            merged = dict(source.get("thresholds", DEFAULT_THRESHOLDS))
            merged.update(value)
            value = merged
        source[key] = value
    _save_state(state)
    return source


def remove_source(source_id: str) -> bool:
    state = _load_state()
    if source_id not in state["sources"]:
        return False
    del state["sources"][source_id]
    _save_state(state)
    return True


def get_config() -> dict:
    state = _load_state()
    return dict(state["config"])


def update_config(**changes) -> dict:
    state = _load_state()
    for key, value in changes.items():
        if value is not None:
            state["config"][key] = value
    _save_state(state)
    return dict(state["config"])


def add_event(entry: dict) -> None:
    state = _load_state()
    state["events"].insert(0, entry)
    del state["events"][MAX_EVENTS:]
    _save_state(state)


def recent_events(limit: int = 50) -> list[dict]:
    state = _load_state()
    return state["events"][: max(0, limit)]
