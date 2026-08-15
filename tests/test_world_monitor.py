"""Tests for the world webcam monitor (sources, analyzer scoring, monitor scan)."""

from __future__ import annotations

import pytest

from jarvis.world import sources
from jarvis.world.analyzer import score_detections
from jarvis.world.monitor import WorldMonitor


class FakeAnalyzer:
    loaded = True

    def __init__(self, results: dict) -> None:
        self._results = results

    async def analyze(self, url: str) -> dict | None:
        return self._results.get(url, {})


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "STATE_FILE", tmp_path / "world_state.json")
    return tmp_path


def _enabled_source(name: str, image_url: str, thresholds: dict | None = None) -> str:
    source = sources.add_source(
        name=name, kind="highway", location="Testville", image_url=image_url
    )
    sources.update_source(source["id"], enabled=True, thresholds=thresholds)
    return source["id"]


def test_score_persons_at_threshold():
    interesting, grouped = score_detections({"person": 4}, {"persons": 4, "vehicles": 6})
    assert interesting is True
    assert grouped == {"persons": 4, "vehicles": 0}


def test_score_vehicles_at_threshold():
    interesting, grouped = score_detections({"car": 5, "truck": 1}, {"persons": 4, "vehicles": 6})
    assert interesting is True
    assert grouped["vehicles"] == 6


def test_score_below_threshold_not_interesting():
    interesting, _ = score_detections({"person": 2, "car": 3}, {"persons": 4, "vehicles": 6})
    assert interesting is False


def test_score_crowd_overrides_threshold():
    interesting, _ = score_detections({"person": 8}, {"persons": 10, "vehicles": 10})
    assert interesting is True


def test_add_list_remove_source(tmp_state):
    source_id = _enabled_source("Cam A", "https://example.com/a.jpg")
    assert source_id
    names = [s["name"] for s in sources.list_sources()]
    assert "Cam A" in names
    assert sources.remove_source(source_id) is True
    assert sources.remove_source("nope") is False


def test_update_source_thresholds(tmp_state):
    source_id = _enabled_source("Cam B", "https://example.com/b.jpg")
    sources.update_source(source_id, thresholds={"persons": 9})
    updated = sources.get_source(source_id)
    assert updated["thresholds"]["persons"] == 9
    assert updated["thresholds"]["vehicles"] == 6


@pytest.mark.asyncio
async def test_scan_records_interesting_events(tmp_state, monkeypatch):
    hot = _enabled_source("Hot Cam", "https://example.com/hot.jpg", {"persons": 1, "vehicles": 1})
    _enabled_source("Quiet Cam", "https://example.com/quiet.jpg", {"persons": 99, "vehicles": 99})
    monitor = WorldMonitor()
    monitor._analyzer = FakeAnalyzer(
        {
            "https://example.com/hot.jpg": {"person": 3},
            "https://example.com/quiet.jpg": {"person": 1},
        }
    )
    alerts = []
    async def fake_notify(text: str, imessage_target: str | None) -> dict:
        alerts.append(text)
        return {"telegram": True, "imessage": False}

    monkeypatch.setattr("jarvis.world.monitor.notify_alert", fake_notify)
    result = await monitor.scan_once()
    assert result["ok"] is True
    assert result["scanned"] == 2
    assert len(result["events"]) == 1
    assert result["events"][0]["source_id"] == hot
    assert result["events"][0]["detections"] == {"persons": 3, "vehicles": 0}
    assert len(alerts) == 1


@pytest.mark.asyncio
async def test_scan_cooldown_dedupe(tmp_state, monkeypatch):
    _enabled_source("Hot Cam", "https://example.com/hot.jpg", {"persons": 1, "vehicles": 1})
    monitor = WorldMonitor()
    monitor._analyzer = FakeAnalyzer({"https://example.com/hot.jpg": {"person": 3}})
    monkeypatch.setattr("jarvis.world.monitor.notify_alert", lambda text, target: _noop())
    first = await monitor.scan_once()
    second = await monitor.scan_once()
    assert len(first["events"]) == 1
    assert len(second["events"]) == 0
    monitor._last_alert_at.clear()
    third = await monitor.scan_once()
    assert len(third["events"]) == 1


async def _noop() -> dict:
    return {"telegram": True, "imessage": False}


@pytest.mark.asyncio
async def test_unreachable_camera_records_error_event(tmp_state, monkeypatch):
    dead = _enabled_source("Dead Cam", "https://example.com/dead.jpg")
    monitor = WorldMonitor()
    monitor._analyzer = FakeAnalyzer({"https://example.com/dead.jpg": None})
    result = await monitor.scan_once()
    assert result["scanned"] == 0
    assert len(result["events"]) == 1
    assert result["events"][0]["error"] is True
    assert result["events"][0]["source_id"] == dead


def test_event_log_capped(tmp_state):
    for index in range(120):
        sources.add_event({"id": str(index), "summary": f"event {index}", "at": index})
    assert len(sources.recent_events(200)) == 100
    assert sources.recent_events(200)[0]["summary"] == "event 119"


def test_sources_are_disabled_by_default(tmp_state):
    assert all(not s["enabled"] for s in sources.list_sources())
