"""YOLO analysis for the world monitor.

Lazy-loads a single yolov8n model on first use (inside a worker thread so the
event loop never blocks) and runs detection on fetched webcam frames.
"""

from __future__ import annotations

import asyncio
import io

import httpx

from jarvis.core.logging import get_logger

log = get_logger("jarvis.world")

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

CONF_THRESHOLD = 0.35
MAX_DIM = 640
MIN_BYTES = 1000

VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle"}


class Analyzer:
    """Fetches webcam frames and returns detection counts by class."""

    def __init__(self) -> None:
        self._model = None
        self._lock: asyncio.Lock | None = None  # lazy — avoid module-level loop

    @property
    def loaded(self) -> bool:
        return self._model is not None

    async def _lock_async(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def load_model(self):
        """Ensure the YOLO model is loaded (idempotent)."""
        if self._model is not None:
            return self._model
        lock = await self._lock_async()
        async with lock:
            if self._model is not None:
                return self._model
            try:
                from ultralytics import YOLO

                self._model = await asyncio.to_thread(YOLO, "yolov8n.pt")
                log.info("YOLO model loaded (yolov8n.pt)")
            except Exception as exc:  # noqa: BLE001 — fall back to no-detection mode
                log.warning("YOLO model load failed: %s", exc)
                self._model = None
        return self._model

    async def fetch_image(self, url: str) -> bytes | None:
        """Fetch a webcam frame; returns raw bytes or None on any failure."""
        try:
            async with httpx.AsyncClient(
                timeout=15.0, follow_redirects=True, headers={"User-Agent": _UA}
            ) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    log.info("fetch %s -> HTTP %s", url, resp.status_code)
                    return None
                if len(resp.content) < MIN_BYTES:
                    return None
                return resp.content
        except httpx.HTTPError as exc:
            log.info("fetch %s failed: %s", url, exc)
            return None

    async def analyze(self, url: str) -> dict[str, int] | None:
        """Detect objects in a webcam frame.

        Returns a class -> count map, {} when the frame had no detections, or
        None when the frame could not be fetched/decoded.
        """
        model = await self.load_model()
        if model is None:
            return {}
        image_bytes = await self.fetch_image(url)
        if image_bytes is None:
            return None
        try:
            return await asyncio.to_thread(self._predict, model, image_bytes)
        except Exception as exc:  # noqa: BLE001 — a bad frame must not kill the scan
            log.warning("analyze %s failed: %s", url, exc)
            return None

    def _predict(self, model, image_bytes: bytes) -> dict[str, int]:
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((MAX_DIM, MAX_DIM))
        results = model.predict(img, conf=CONF_THRESHOLD, verbose=False)
        counts: dict[str, int] = {}
        if results and results[0].boxes is not None:
            names = results[0].names
            for cls_id in results[0].boxes.cls.tolist():
                name = names.get(int(cls_id), "unknown")
                counts[name] = counts.get(name, 0) + 1
        return counts


def score_detections(counts: dict[str, int], thresholds: dict | None = None) -> tuple[bool, dict]:
    """Return (interesting, grouped_counts) for a frame.

    Interesting = persons or vehicles at/over the per-source thresholds, or a
    large crowd (>= 8 people) regardless of configured thresholds.
    """
    thresholds = thresholds or {}
    persons = int(counts.get("person", 0))
    vehicles = sum(int(counts.get(cls, 0)) for cls in VEHICLE_CLASSES)
    grouped = {"persons": persons, "vehicles": vehicles}
    interesting = (
        persons >= int(thresholds.get("persons", 4))
        or vehicles >= int(thresholds.get("vehicles", 6))
        or persons >= 8
    )
    return interesting, grouped


def summarize(source: dict, grouped: dict) -> str:
    """Human-readable alert text for an interesting frame."""
    bits = []
    if grouped.get("persons"):
        persons = grouped["persons"]
        bits.append(f"{persons} person{'s' if persons != 1 else ''}")
    if grouped.get("vehicles"):
        vehicles = grouped["vehicles"]
        bits.append(f"{vehicles} vehicle{'s' if vehicles != 1 else ''}")
    detail = " and ".join(bits) or "activity"
    return f"World Monitor: {source.get('name', 'a camera')} — {detail} detected"
