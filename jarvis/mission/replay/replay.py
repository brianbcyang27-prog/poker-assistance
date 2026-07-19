"""MissionReplay — analyse and replay recorded missions."""

import logging
import time
from typing import Any, Dict, List, Optional

from .models import MissionEvent, MissionReport, MissionReplayQuery
from .recorder import MissionRecorder

logger = logging.getLogger(__name__)


class MissionReplay:
    """Analyse, query, and replay recorded missions.

    Usage::

        recorder = MissionRecorder()
        replay = MissionReplay(recorder)
        timeline = await replay.get_timeline("m1")
        text = await replay.replay("m1")
    """

    def __init__(self, recorder: MissionRecorder) -> None:
        self._recorder = recorder

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    async def get_timeline(self, mission_id: str) -> List[Dict[str, Any]]:
        """Return a formatted timeline for the mission."""
        report = await self._recorder.get_report(mission_id)
        if report:
            return report.to_timeline()
        # Fallback: build from raw events
        events = await self._recorder.get_events(mission_id)
        events.sort(key=lambda e: e.timestamp)
        return [{
            "time": time.strftime("%H:%M", time.localtime(e.timestamp)),
            "type": e.event_type,
            "title": e.title,
            "description": e.description[:200],
            "success": e.success,
        } for e in events]

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    async def get_report(self, mission_id: str) -> Optional[MissionReport]:
        """Return the mission report."""
        return await self._recorder.get_report(mission_id)

    async def get_summary(self, mission_id: str) -> str:
        """Return a human-readable summary."""
        report = await self._recorder.get_report(mission_id)
        if not report:
            events = await self._recorder.get_events(mission_id)
            if not events:
                return f"Mission {mission_id}: no data found."
            goal = events[0].description if events else ""
            return (
                f"Mission {mission_id}\n"
                f"  Goal: {goal}\n"
                f"  Events: {len(events)}\n"
                f"  (No final report available)"
            )

        lines = [
            f"Mission {report.mission_id}",
            f"  Goal: {report.goal}",
            f"  Outcome: {report.outcome}",
            f"  Duration: {report.duration_seconds:.1f}s",
            f"  Events: {report.total_events}",
            f"  Actions: {len(report.actions)}",
            f"  Problems: {len(report.problems)}",
        ]
        if report.verification:
            lines.append(f"  Verification: {report.verification[:120]}")
        if report.lessons:
            lines.append(f"  Lessons ({len(report.lessons)}):")
            for lesson in report.lessons[:5]:
                lines.append(f"    - {lesson}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Lessons
    # ------------------------------------------------------------------

    async def get_lessons(self, mission_id: str) -> List[str]:
        """Return lessons learned during a mission."""
        report = await self._recorder.get_report(mission_id)
        if report:
            return list(report.lessons)
        # Derive from error/recovery events
        events = await self._recorder.get_events(mission_id)
        lessons: List[str] = []
        for event in events:
            if event.event_type == "recovery":
                lessons.append(event.description)
        return lessons

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search_missions(self, query: MissionReplayQuery) -> List[Dict[str, Any]]:
        """Search missions by criteria."""
        summaries = await self._recorder.list_missions(limit=500)
        results: List[Dict[str, Any]] = []

        for summary in summaries:
            if query.mission_id and summary["mission_id"] != query.mission_id:
                continue
            if query.start_time and summary.get("started_at", 0) < query.start_time:
                continue
            if query.end_time and summary.get("started_at", 0) > query.end_time:
                continue
            results.append(summary)

        return results[:query.limit]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_stats(self) -> Dict[str, Any]:
        """Return overall mission statistics."""
        summaries = await self._recorder.list_missions(limit=10000)
        total = len(summaries)
        if total == 0:
            return {"total": 0, "success_rate": 0.0}

        success = sum(1 for s in summaries if s.get("outcome") == "success")
        failed = sum(1 for s in summaries if s.get("outcome") == "failed")
        avg_duration = (
            sum(s.get("duration_seconds", 0) for s in summaries) / total
        )
        avg_events = (
            sum(s.get("total_events", 0) for s in summaries) / total
        )

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": round(success / total, 3) if total else 0.0,
            "avg_duration_seconds": round(avg_duration, 2),
            "avg_events": round(avg_events, 1),
        }

    async def get_failed_missions(self) -> List[Dict[str, Any]]:
        """Return summaries of all failed missions."""
        summaries = await self._recorder.list_missions(limit=10000)
        return [s for s in summaries if s.get("outcome") == "failed"]

    # ------------------------------------------------------------------
    # Full Replay
    # ------------------------------------------------------------------

    async def replay(self, mission_id: str) -> str:
        """Return a full text replay of the mission."""
        report = await self._recorder.get_report(mission_id)
        events = await self._recorder.get_events(mission_id)

        if not events and not report:
            return f"Mission {mission_id}: no data found."

        lines: List[str] = []
        lines.append(f"{'='*60}")
        lines.append(f"MISSION REPLAY: {mission_id}")
        lines.append(f"{'='*60}")

        if report:
            lines.append(f"Goal: {report.goal}")
            lines.append(f"Outcome: {report.outcome}")
            lines.append(f"Duration: {report.duration_seconds:.1f}s")
            lines.append("")

        events_sorted = sorted(events, key=lambda e: e.timestamp)
        base_ts = events_sorted[0].timestamp if events_sorted else 0.0

        for event in events_sorted:
            elapsed = event.timestamp - base_ts if base_ts else 0.0
            status = "+" if event.success else "!"
            lines.append(
                f"[{elapsed:7.1f}s] {status} {event.event_type:12s} | {event.title}"
            )
            if event.description:
                desc = event.description[:150].replace("\n", " ")
                lines.append(f"           {' '*len(status)}   {desc}")
            if event.metadata:
                for k, v in event.metadata.items():
                    lines.append(f"           {' '*len(status)}   {k}: {v}")

        if report and report.lessons:
            lines.append("")
            lines.append("Lessons learned:")
            for lesson in report.lessons:
                lines.append(f"  - {lesson}")

        lines.append(f"{'='*60}")
        return "\n".join(lines)
