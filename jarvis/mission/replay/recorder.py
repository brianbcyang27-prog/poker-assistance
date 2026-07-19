"""MissionRecorder — records mission events to JSON files."""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import MissionEvent, MissionReport, MissionEventType

logger = logging.getLogger(__name__)

_DEFAULT_STORAGE = Path("memory_store/missions")


class MissionRecorder:
    """Records mission events and generates reports.

    Persists per-mission JSON files to ``storage_dir``.

    Usage::

        recorder = MissionRecorder()
        await recorder.start_recording("m1", "Build chat app")
        await recorder.record_event("m1", "action", "Created files", "Wrote 5 modules")
        report = await recorder.complete("m1", "success", "All tests pass", ["Use async"])
    """

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self._storage = Path(storage_dir) if storage_dir else _DEFAULT_STORAGE
        self._storage.mkdir(parents=True, exist_ok=True)
        # In-memory caches keyed by mission_id
        self._events: Dict[str, List[MissionEvent]] = {}
        self._reports: Dict[str, MissionReport] = {}

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    async def start_recording(self, mission_id: str, goal: str) -> MissionEvent:
        """Begin recording a new mission."""
        event = MissionEvent(
            mission_id=mission_id,
            event_type=MissionEventType.STARTED,
            title="Mission started",
            description=goal,
        )
        self._ensure_list(mission_id)
        self._events[mission_id].append(event)
        self._save_event(mission_id, event)
        logger.info("Started recording mission %s", mission_id)
        return event

    async def record_event(
        self,
        mission_id: str,
        event_type: str,
        title: str,
        description: str = "",
        agent_id: str = "",
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MissionEvent:
        """Record a single mission event."""
        event = MissionEvent(
            mission_id=mission_id,
            event_type=event_type,
            title=title,
            description=description,
            agent_id=agent_id,
            success=success,
            metadata=metadata or {},
        )
        self._ensure_list(mission_id)
        self._events[mission_id].append(event)
        self._save_event(mission_id, event)
        return event

    async def record_error(
        self,
        mission_id: str,
        error_type: str,
        description: str,
        agent_id: str = "",
    ) -> MissionEvent:
        """Record an error event."""
        event = MissionEvent(
            mission_id=mission_id,
            event_type=MissionEventType.ERROR,
            title=error_type,
            description=description,
            agent_id=agent_id,
            success=False,
        )
        self._ensure_list(mission_id)
        self._events[mission_id].append(event)
        self._save_event(mission_id, event)
        return event

    async def record_recovery(
        self,
        mission_id: str,
        description: str,
        agent_id: str = "",
    ) -> MissionEvent:
        """Record a recovery event after an error."""
        event = MissionEvent(
            mission_id=mission_id,
            event_type=MissionEventType.RECOVERY,
            title="Recovery",
            description=description,
            agent_id=agent_id,
            success=True,
        )
        self._ensure_list(mission_id)
        self._events[mission_id].append(event)
        self._save_event(mission_id, event)
        return event

    async def complete(
        self,
        mission_id: str,
        outcome: str,
        verification: str = "",
        lessons: Optional[List[str]] = None,
    ) -> MissionReport:
        """Finalize the mission and persist the report."""
        events = self._events.get(mission_id, [])
        actions = [e for e in events if e.event_type not in (
            MissionEventType.ERROR, MissionEventType.RECOVERY,
        )]
        problems = [e for e in events if e.event_type in (
            MissionEventType.ERROR, MissionEventType.RECOVERY,
        )]

        started_at = events[0].timestamp if events else 0.0
        completed_at = time.time()
        duration = completed_at - started_at if started_at else 0.0

        goal = ""
        plan = ""
        if events:
            goal = events[0].description

        report = MissionReport(
            mission_id=mission_id,
            goal=goal,
            plan=plan,
            actions=actions,
            problems=problems,
            verification=verification,
            lessons=lessons or [],
            outcome=outcome,
            duration_seconds=round(duration, 2),
            total_events=len(events),
            started_at=started_at,
            completed_at=completed_at,
        )

        # Emit final event
        final_type = MissionEventType.COMPLETED if outcome == "success" else MissionEventType.FAILED
        final_event = MissionEvent(
            mission_id=mission_id,
            event_type=final_type,
            title=f"Mission {outcome}",
            description=verification,
        )
        self._ensure_list(mission_id)
        self._events[mission_id].append(final_event)

        self._reports[mission_id] = report
        self._save_report(mission_id, report)
        logger.info("Completed mission %s (%s)", mission_id, outcome)
        return report

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_events(self, mission_id: str) -> List[MissionEvent]:
        """Return all events for a mission."""
        if mission_id in self._events:
            return list(self._events[mission_id])
        # Try loading from disk
        self._load(mission_id)
        return list(self._events.get(mission_id, []))

    async def get_report(self, mission_id: str) -> Optional[MissionReport]:
        """Return the final report for a mission."""
        if mission_id in self._reports:
            return self._reports[mission_id]
        self._load(mission_id)
        return self._reports.get(mission_id)

    async def list_missions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent mission summaries."""
        summaries: List[Dict[str, Any]] = []
        for path in sorted(self._storage.glob("*/report.json"), reverse=True):
            if len(summaries) >= limit:
                break
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                summaries.append({
                    "mission_id": raw.get("mission_id", path.parent.name),
                    "goal": raw.get("goal", ""),
                    "outcome": raw.get("outcome", ""),
                    "duration_seconds": raw.get("duration_seconds", 0),
                    "total_events": raw.get("total_events", 0),
                    "started_at": raw.get("started_at", 0),
                })
            except Exception as exc:
                logger.debug("Failed to read report %s: %s", path, exc)
        return summaries

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _ensure_list(self, mission_id: str) -> None:
        if mission_id not in self._events:
            self._events[mission_id] = []

    def _mission_dir(self, mission_id: str) -> Path:
        d = self._storage / mission_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _save_event(self, mission_id: str, event: MissionEvent) -> None:
        events_file = self._mission_dir(mission_id) / "events.jsonl"
        try:
            with events_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.debug("Failed to save event: %s", exc)

    def _save_report(self, mission_id: str, report: MissionReport) -> None:
        report_file = self._mission_dir(mission_id) / "report.json"
        try:
            report_file.write_text(
                json.dumps(report.to_dict(), indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.debug("Failed to save report: %s", exc)

    def _load(self, mission_id: str) -> None:
        """Load events and report from disk into memory."""
        mission_dir = self._storage / mission_id
        if not mission_dir.is_dir():
            return

        # Load events
        events_file = mission_dir / "events.jsonl"
        if events_file.is_file() and mission_id not in self._events:
            events: List[MissionEvent] = []
            for line in events_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    events.append(MissionEvent(**raw))
                except Exception:
                    pass
            self._events[mission_id] = events

        # Load report
        report_file = mission_dir / "report.json"
        if report_file.is_file() and mission_id not in self._reports:
            try:
                raw = json.loads(report_file.read_text(encoding="utf-8"))
                actions = [MissionEvent(**a) for a in raw.pop("actions", [])]
                problems = [MissionEvent(**p) for p in raw.pop("problems", [])]
                report = MissionReport(**raw)
                report.actions = actions
                report.problems = problems
                self._reports[mission_id] = report
            except Exception:
                pass
