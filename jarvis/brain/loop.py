"""Living Brain - Permanent background intelligence loop for JARVIS.

Runs continuously, observing the user's environment and producing
predictions and planned actions. Does NOT take autonomous actions;
all proposals are queued for user approval or auto-approved based
on safety rules.

Designed for Python 3.9.6+ with stdlib only.
"""

import asyncio
import logging
import time
from collections import deque
from typing import Any, Dict, List, Optional

from jarvis.brain.living_models import (
    ActionResult,
    ContextSnapshot,
    PlannedAction,
    Prediction,
    Understanding,
)

logger = logging.getLogger(__name__)


class LivingBrain:
    """The permanent background intelligence loop.

    Observes, understands, predicts, plans, and assists in a continuous
    cycle. CPU usage is near zero between ticks (asyncio.sleep).
    """

    def __init__(self, interval_seconds: float = 30.0) -> None:
        self._interval = interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._timeline: deque = deque(maxlen=100)
        self._tick_count = 0
        self._last_tick: Optional[float] = None
        self._start_time: Optional[float] = None

    async def start(self) -> None:
        """Start the background loop as an asyncio task."""
        async with self._lock:
            if self._running:
                logger.warning("LivingBrain already running")
                return
            self._running = True
            self._start_time = time.time()
            self._task = asyncio.create_task(self._loop())
            logger.info("LivingBrain started (interval=%.1fs)", self._interval)

    async def stop(self) -> None:
        """Stop the background loop gracefully."""
        async with self._lock:
            if not self._running:
                return
            self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("LivingBrain stopped after %d ticks", self._tick_count)

    async def _loop(self) -> None:
        """Internal loop: tick then sleep."""
        while self._running:
            try:
                await self.tick()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("LivingBrain tick failed")
            await asyncio.sleep(self._interval)

    async def tick(self) -> None:
        """Single iteration: observe -> understand -> predict -> plan -> assist."""
        snapshot = await self.observe()
        understanding = await self.understand(snapshot)
        predictions = await self.predict(understanding)
        actions = await self.plan(predictions)
        results = await self.assist(actions)

        self._tick_count += 1
        self._last_tick = time.time()
        self._timeline.append(snapshot)

    async def observe(self) -> ContextSnapshot:
        """Capture current state of the user's environment."""
        snapshot = ContextSnapshot()
        snapshot.context_dict = {
            "tick": self._tick_count,
            "observe_time": time.time(),
        }
        return snapshot

    async def understand(self, snapshot: ContextSnapshot) -> Understanding:
        """Analyze what's happening based on a snapshot."""
        return Understanding(
            snapshot=snapshot,
            summary="Context captured at tick %d" % self._tick_count,
            detected_patterns=[],
            anomalies=[],
            context_changes=[],
        )

    async def predict(self, understanding: Understanding) -> List[Prediction]:
        """Predict what the user might need next."""
        return []

    async def plan(self, predictions: List[Prediction]) -> List[PlannedAction]:
        """Plan potential actions from predictions."""
        return []

    async def assist(self, actions: List[PlannedAction]) -> List[ActionResult]:
        """Execute safe actions. By default, nothing is auto-executed."""
        results: List[ActionResult] = []
        for action in actions:
            if action.auto_approve:
                results.append(
                    ActionResult(
                        action=action,
                        executed=True,
                        result="Auto-approved (stub)",
                    )
                )
            else:
                results.append(
                    ActionResult(
                        action=action,
                        executed=False,
                        result="Queued for user approval",
                    )
                )
        return results

    def get_status(self) -> Dict[str, Any]:
        """Return current loop status."""
        uptime = 0.0
        if self._start_time is not None:
            uptime = time.time() - self._start_time
        return {
            "running": self._running,
            "ticks": self._tick_count,
            "last_tick": self._last_tick,
            "interval_seconds": self._interval,
            "uptime_seconds": round(uptime, 1),
            "timeline_size": len(self._timeline),
        }

    def get_timeline(self) -> List[ContextSnapshot]:
        """Return recent snapshots (last 100)."""
        return list(self._timeline)
