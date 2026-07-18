"""MissionManager — persistent long-running mission lifecycle manager."""

import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .mission import Mission, MissionStatus

logger = logging.getLogger(__name__)

_DEFAULT_STORAGE = Path("jarvis_missions.json")


class MissionManager:
    """Create, control, persist, and replay long-running missions."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        self._missions: Dict[str, Mission] = {}
        self._storage = Path(storage_path) if storage_path else _DEFAULT_STORAGE
        self._progress: Dict[str, Dict[str, Any]] = {}
        self._start_times: Dict[str, float] = {}
        self._durations: Dict[str, List[float]] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, user_request: str, priority: str = "normal") -> Mission:
        mission = Mission(
            id=f"mission_{uuid.uuid4().hex[:12]}",
            user_request=user_request,
            goal=user_request,
            priority=priority,
        )
        self._missions[mission.id] = mission
        self._progress[mission.id] = {"steps_total": 0, "steps_done": 0, "status": "created"}
        logger.info("Created mission %s", mission.id)
        return mission

    async def get(self, mission_id: str) -> Optional[Mission]:
        return self._missions.get(mission_id)

    async def list_active(self) -> List[Mission]:
        active_statuses = {
            MissionStatus.CREATED,
            MissionStatus.RESEARCHING,
            MissionStatus.PLANNING,
            MissionStatus.EXECUTING,
            MissionStatus.VERIFYING,
            MissionStatus.REVIEWING,
            MissionStatus.PAUSED,
        }
        return [m for m in self._missions.values() if m.status in active_statuses]

    async def list_completed(self) -> List[Mission]:
        return [
            m
            for m in self._missions.values()
            if m.status in (MissionStatus.COMPLETED, MissionStatus.FAILED)
        ]

    # ------------------------------------------------------------------
    # Lifecycle control
    # ------------------------------------------------------------------

    async def start(self, mission_id: str) -> None:
        mission = self._require(mission_id)
        if mission.status not in (MissionStatus.CREATED, MissionStatus.PAUSED):
            raise RuntimeError(f"Cannot start mission in status {mission.status}")
        mission.status = MissionStatus.RESEARCHING
        mission.started_at = datetime.now()
        self._start_times[mission_id] = time.time()
        self._progress.setdefault(mission_id, {}).update({"status": "running"})
        logger.info("Started mission %s", mission_id)

    async def pause(self, mission_id: str) -> None:
        mission = self._require(mission_id)
        if mission.status == MissionStatus.PAUSED:
            return
        mission.status = MissionStatus.PAUSED
        self._progress.setdefault(mission_id, {}).update({"status": "paused"})
        logger.info("Paused mission %s", mission_id)

    async def resume(self, mission_id: str) -> None:
        mission = self._require(mission_id)
        if mission.status != MissionStatus.PAUSED:
            raise RuntimeError("Mission is not paused")
        # Resume to the next logical stage (default: executing)
        mission.status = MissionStatus.EXECUTING
        self._progress.setdefault(mission_id, {}).update({"status": "running"})
        logger.info("Resumed mission %s", mission_id)

    async def cancel(self, mission_id: str) -> None:
        mission = self._require(mission_id)
        if mission.status in (MissionStatus.COMPLETED, MissionStatus.FAILED):
            return
        mission.status = MissionStatus.FAILED
        mission.add_error("Cancelled by user")
        self._progress.setdefault(mission_id, {}).update({"status": "cancelled"})
        logger.info("Cancelled mission %s", mission_id)

    async def retry(self, mission_id: str) -> None:
        mission = self._require(mission_id)
        if mission.status != MissionStatus.FAILED:
            raise RuntimeError("Can only retry failed missions")
        mission.status = MissionStatus.CREATED
        mission.errors.clear()
        self._progress.setdefault(mission_id, {}).update({"status": "retrying"})
        logger.info("Retrying mission %s", mission_id)

    # ------------------------------------------------------------------
    # Progress & ETA
    # ------------------------------------------------------------------

    async def get_progress(self, mission_id: str) -> Dict[str, Any]:
        self._require(mission_id)
        prog = self._progress.get(mission_id, {})
        mission = self._missions[mission_id]
        return {
            "mission_id": mission_id,
            "status": mission.status,
            "current_stage": mission.current_stage,
            "steps_total": prog.get("steps_total", 0),
            "steps_done": prog.get("steps_done", 0),
            "progress_pct": (
                round(prog["steps_done"] / prog["steps_total"] * 100, 1)
                if prog.get("steps_total")
                else 0.0
            ),
        }

    async def get_eta(self, mission_id: str) -> Optional[float]:
        """Estimated seconds remaining based on average stage duration."""
        self._require(mission_id)
        start = self._start_times.get(mission_id)
        if start is None:
            return None
        elapsed = time.time() - start
        prog = self._progress.get(mission_id, {})
        total = prog.get("steps_total", 0)
        done = prog.get("steps_done", 0)
        if done == 0 or total == 0:
            return None
        avg_per_step = elapsed / done
        remaining = total - done
        return round(avg_per_step * remaining, 2)

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------

    async def replay(self, mission_id: str) -> Mission:
        """Create a new mission cloned from a completed/failed one."""
        original = self._require(mission_id)
        clone = await self.create(
            user_request=f"[REPLAY] {original.user_request}",
            priority=original.priority,
        )
        clone.goal = original.goal
        logger.info("Replayed mission %s -> %s", mission_id, clone.id)
        return clone

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def save(self) -> None:
        data: List[Dict[str, Any]] = []
        for m in self._missions.values():
            entry = m.to_dict()
            entry["_progress"] = self._progress.get(m.id, {})
            data.append(entry)
        self._storage.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        logger.info("Saved %d missions to %s", len(data), self._storage)

    async def load(self) -> None:
        if not self._storage.is_file():
            return
        raw = json.loads(self._storage.read_text(encoding="utf-8"))
        for entry in raw:
            mission = Mission(
                id=entry.get("id", ""),
                user_request=entry.get("user_request", ""),
                goal=entry.get("goal", ""),
                status=entry.get("status", MissionStatus.CREATED),
                current_stage=entry.get("current_stage", ""),
                priority=entry.get("priority", "normal"),
            )
            self._missions[mission.id] = mission
            self._progress[mission.id] = entry.get("_progress", {})
        logger.info("Loaded %d missions from %s", len(raw), self._storage)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _require(self, mission_id: str) -> Mission:
        mission = self._missions.get(mission_id)
        if mission is None:
            raise KeyError(f"Mission '{mission_id}' not found")
        return mission


