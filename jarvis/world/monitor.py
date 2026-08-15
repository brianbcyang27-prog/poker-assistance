"""Background world monitor — periodically scans enabled webcam sources."""

from __future__ import annotations

import asyncio
import time
from uuid import uuid4

from jarvis.core.logging import get_logger
from jarvis.world import sources
from jarvis.world.analyzer import Analyzer, score_detections, summarize
from jarvis.world.notify import notify_alert, telegram_config

log = get_logger("jarvis.world")

DEFAULT_INTERVAL = 120
DEFAULT_COOLDOWN = 600


class WorldMonitor:
    """Scans enabled webcam sources in a background task and alerts on interest."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._lock: asyncio.Lock | None = None  # lazy — avoid module-level loop
        self._analyzer = Analyzer()
        self._last_alert_at: dict[str, float] = {}
        self._last_scan_at: float | None = None

    @property
    def analyzer(self) -> Analyzer:
        return self._analyzer

    async def _scan_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run())
        log.info("World monitor started")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            log.info("World monitor stopped")

    async def _run(self) -> None:
        try:
            while True:
                try:
                    await self._scan_once()
                except Exception as exc:  # noqa: BLE001 — a bad scan must not kill the loop
                    log.warning("world scan failed: %s", exc)
                await asyncio.sleep(sources.get_config().get("interval", DEFAULT_INTERVAL))
        except asyncio.CancelledError:
            pass

    async def scan_once(self) -> dict:
        """Manual scan (API-triggered); skips if a scan is already in flight."""
        lock = await self._scan_lock()
        if lock.locked():
            return {"ok": True, "skipped": True, "scanned": 0, "events": []}
        async with lock:
            return await self._scan_once()

    async def _scan_once(self) -> dict:
        config = sources.get_config()
        enabled = [s for s in sources.list_sources() if s.get("enabled")]
        scanned = 0
        new_events = []
        for source in enabled:
            counts = await self._analyzer.analyze(source["image_url"])
            if counts is None:
                entry = await self._record_failure(source, config)
                if entry is not None:
                    new_events.append(entry)
                continue
            scanned += 1
            interesting, grouped = score_detections(counts, source.get("thresholds"))
            if not interesting:
                continue
            now = time.time()
            if now - self._last_alert_at.get(source["id"], 0.0) < config.get(
                "cooldown", DEFAULT_COOLDOWN
            ):
                continue
            self._last_alert_at[source["id"]] = now
            entry = {
                "id": uuid4().hex[:8],
                "source_id": source["id"],
                "source_name": source.get("name"),
                "kind": source.get("kind", "other"),
                "at": now,
                "summary": summarize(source, grouped),
                "detections": grouped,
            }
            sources.add_event(entry)
            new_events.append(entry)
            channels = await notify_alert(entry["summary"], config.get("imessage_target"))
            log.info("world alert: %s (%s)", entry["summary"], channels)
        self._last_scan_at = time.time()
        return {"ok": True, "scanned": scanned, "events": new_events}

    async def _record_failure(self, source: dict, config: dict) -> dict | None:
        now = time.time()
        if now - self._last_alert_at.get(source["id"], 0.0) < config.get(
            "cooldown", DEFAULT_COOLDOWN
        ):
            return None
        self._last_alert_at[source["id"]] = now
        entry = {
            "id": uuid4().hex[:8],
            "source_id": source["id"],
            "source_name": source.get("name"),
            "kind": source.get("kind", "other"),
            "at": now,
            "summary": f"Camera unreachable: {source.get('name')}",
            "detections": {},
            "error": True,
        }
        sources.add_event(entry)
        return entry

    async def status(self) -> dict:
        config = sources.get_config()
        telegram_ok, telegram_chat_id = await telegram_config()
        imessage_target = config.get("imessage_target")
        return {
            "running": self._task is not None and not self._task.done(),
            "yolo_loaded": self._analyzer.loaded,
            "last_scan_at": self._last_scan_at,
            "interval": config.get("interval", DEFAULT_INTERVAL),
            "notifications": {
                "telegram_configured": telegram_ok,
                "telegram_chat_id": telegram_chat_id,
                "imessage_configured": bool(imessage_target),
            },
        }


world_monitor = WorldMonitor()
