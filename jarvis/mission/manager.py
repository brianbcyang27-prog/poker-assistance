"""MissionManager — persistent long-running mission lifecycle manager.

Persistence: Uses the SQLite workspaces table (via Database) for unified storage
with MissionManager. WorkspaceManager also writes to the same table.
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Any

from .mission import Mission, MissionStatus

logger = logging.getLogger(__name__)


class MissionManager:
    """Create, control, persist, and replay long-running missions.

    Runtime split (v9):
      - MissionManager: replay/legacy API, lightweight lifecycle control
      - WorkspaceManager + DAGPlanner + MissionExecutor: production DAG pipeline
      Both write to the same workspaces SQLite table.
    """

    def __init__(self, storage_path: str | None = None, *, use_db: bool = True) -> None:
        self._missions: dict[str, Mission] = {}
        self._progress: dict[str, dict[str, Any]] = {}
        self._start_times: dict[str, float] = {}
        self._use_db = use_db
        if storage_path is not None:
            logger.debug("storage_path=%r is ignored — persistence is now DB-backed", storage_path)

    # ------------------------------------------------------------------
    # Database access
    # ------------------------------------------------------------------

    async def _db(self):
        if not self._use_db:
            return None
        try:
            from jarvis.core.database import get_db

            return await get_db()
        except Exception:
            return None

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
        db = await self._db()
        if db:
            try:
                await db.save_mission(mission.model_dump())
            except Exception:
                logger.warning("Failed to persist mission %s to DB", mission.id, exc_info=True)
        logger.info("Created mission %s", mission.id)
        return mission

    async def get(self, mission_id: str) -> Mission | None:
        if mission_id in self._missions:
            return self._missions[mission_id]
        db = await self._db()
        if db:
            try:
                data = await db.get_mission(mission_id)
                if data:
                    mission = self._mission_from_dict(data)
                    self._missions[mission_id] = mission
                    return mission
            except Exception:
                logger.warning("Failed to load mission %s from DB", mission_id, exc_info=True)
        return None

    async def list_active(self) -> list[Mission]:
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

    async def list_completed(self) -> list[Mission]:
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
        await self._persist_status(mission_id, mission.status)
        logger.info("Started mission %s", mission_id)

    async def pause(self, mission_id: str) -> None:
        mission = self._require(mission_id)
        if mission.status == MissionStatus.PAUSED:
            return
        mission.status = MissionStatus.PAUSED
        self._progress.setdefault(mission_id, {}).update({"status": "paused"})
        await self._persist_status(mission_id, MissionStatus.PAUSED)
        logger.info("Paused mission %s", mission_id)

    async def resume(self, mission_id: str) -> None:
        mission = self._require(mission_id)
        if mission.status != MissionStatus.PAUSED:
            raise RuntimeError("Mission is not paused")
        mission.status = MissionStatus.EXECUTING
        self._progress.setdefault(mission_id, {}).update({"status": "running"})
        await self._persist_status(mission_id, MissionStatus.EXECUTING)
        logger.info("Resumed mission %s", mission_id)

    async def cancel(self, mission_id: str) -> None:
        mission = self._require(mission_id)
        if mission.status in (MissionStatus.COMPLETED, MissionStatus.FAILED):
            return
        mission.status = MissionStatus.FAILED
        mission.add_error("Cancelled by user")
        self._progress.setdefault(mission_id, {}).update({"status": "cancelled"})
        await self._persist_status(mission_id, MissionStatus.FAILED)
        logger.info("Cancelled mission %s", mission_id)

        # Propagate cancellation to the running executor task
        try:
            from jarvis.brain.mission_executor import mission_executor

            mission_executor.cancel_execution(mission_id)
        except Exception:
            logger.warning(
                "Failed to propagate cancellation to executor for %s", mission_id, exc_info=True
            )

    async def retry(self, mission_id: str) -> None:
        mission = self._require(mission_id)
        if mission.status != MissionStatus.FAILED:
            raise RuntimeError("Can only retry failed missions")
        mission.status = MissionStatus.CREATED
        mission.errors.clear()
        self._progress.setdefault(mission_id, {}).update({"status": "retrying"})
        await self._persist_status(mission_id, MissionStatus.CREATED)
        logger.info("Retrying mission %s", mission_id)

    # ------------------------------------------------------------------
    # Progress & ETA
    # ------------------------------------------------------------------

    async def get_progress(self, mission_id: str) -> dict[str, Any]:
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

    async def get_eta(self, mission_id: str) -> float | None:
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
        original = self._require(mission_id)
        clone = await self.create(
            user_request=f"[REPLAY] {original.user_request}",
            priority=original.priority,
        )
        clone.goal = original.goal
        logger.info("Replayed mission %s -> %s", mission_id, clone.id)
        return clone

    # ------------------------------------------------------------------
    # Persistence (now DB-backed; signatures preserved for backward compat)
    # ------------------------------------------------------------------

    async def save(self) -> None:
        """Save all cached missions to the database (replaces JSON persistence)."""
        try:
            db = await self._db()
            for m in self._missions.values():
                try:
                    await db.save_mission(m.model_dump())
                except Exception:
                    logger.warning("Failed to save mission %s", m.id, exc_info=True)
            logger.info("Saved %d missions to database", len(self._missions))
        except Exception:
            logger.warning("Failed to save missions to database", exc_info=True)

    async def load(self) -> None:
        """Load missions from the database into the cache."""
        try:
            db = await self._db()
            raw = await db.list_missions(limit=1000)
            for entry in raw:
                mission = self._mission_from_dict(entry)
                self._missions[mission.id] = mission
            logger.info("Loaded %d missions from database", len(raw))
        except Exception:
            logger.warning("Failed to load missions from database", exc_info=True)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _require(self, mission_id: str) -> Mission:
        mission = self._missions.get(mission_id)
        if mission is None:
            raise KeyError(f"Mission '{mission_id}' not found")
        return mission

    async def _persist_status(self, mission_id: str, status: str) -> None:
        try:
            db = await self._db()
            await db.update_mission_status(mission_id, status)
        except Exception:
            pass

    @staticmethod
    def _mission_from_dict(data: dict) -> Mission:
        return Mission(
            id=data.get("id", ""),
            user_request=data.get("user_request", ""),
            goal=data.get("goal", ""),
            owner=data.get("owner", ""),
            status=data.get("status", MissionStatus.CREATED),
            current_stage=data.get("current_stage", "understand"),
            priority=data.get("priority", "normal"),
            research_findings=data.get("research_findings", []),
            tool_candidates=data.get("tool_candidates", []),
            architecture_plan=data.get("architecture_plan"),
            execution_results=data.get("execution_results", []),
            verification_results=data.get("verification_results", []),
            review_items=data.get("review_items", []),
            memory_record=data.get("memory_record"),
            final_report=data.get("final_report", ""),
            timeline_events=data.get("timeline_events", []),
            stage_history=data.get("stage_history", []),
            errors=data.get("errors", []),
        )
