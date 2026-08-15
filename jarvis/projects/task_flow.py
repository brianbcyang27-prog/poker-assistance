"""Task-flow orchestration for the chat router (v9.0.0 M2, contract §3.6).

Pure orchestration: complexity → project resolution → domain selection →
mission creation → master execution → artifact/decision recording. The chat
router calls :func:`route_task` and streams its events; keeping this module
free of FastAPI makes the branch unit-testable.
"""

import logging
from datetime import datetime

from ..core.models import Task
from ..domains.models import domain_by_alias
from .complexity import estimate_complexity
from .manager import project_manager

logger = logging.getLogger(__name__)

#: Event callbacks receive dicts: {"type", "payload"}.
EVENT_TYPES = ("project_resolved", "domain_selected", "mission_start", "mission_step")


def select_domain(message: str, default: str = "engineering") -> str:
    """Pick the domain for a request by alias match, defaulting to engineering."""
    domain = domain_by_alias(message)
    if domain is not None:
        return domain.value
    import re

    from ..domains.models import DOMAIN_INFO

    lowered = message.lower()
    words = set(re.findall(r"[a-z0-9]+", lowered))
    for info in DOMAIN_INFO.values():
        if words.intersection(info.aliases):
            return info.domain.value
        if any(alias in lowered for alias in info.aliases if " " in alias):
            return info.domain.value
    return default


async def route_task(
    message: str,
    domain_registry,
    emit=None,
    session_id: str | None = None,
    fact_checker=None,
) -> dict:
    """Run the full task flow for a request and return its summary.

    - complexity < "small" → {"skipped": True, "reason": ...}
    - project resolution: existing name match, else auto-create when the
      complexity suggests it (mission-level requests are linked to an existing
      project when one matches, otherwise a "create project" project is made).
    - mission record created; workspace link optional (chat layer provides it).
    - execution delegates to the selected domain master (plans → workers →
      review) and records results as artifact + decision.
    - optional fact-check gate: ``fact_checker`` is an async callable
      ``(title, content) -> {"verified", "issues", "summary"}``; when provided,
      the completed result is verified and a mission report is produced.
    """
    complexity = estimate_complexity(message)
    level = complexity["level"]

    if level == "tiny":
        return {"skipped": True, "reason": "tiny", "complexity": complexity}

    # v9.2.0 D4: mirror every mission event onto the global event bus so all
    # connected clients see the action in their live activity stream. The bus
    # publish is unconditional; the caller-supplied emit (SSE etc.) is optional.
    caller_emit = emit

    async def _emit(event: dict):
        if caller_emit is not None:
            await caller_emit(event)
        try:
            from jarvis.core.events import Event, event_bus

            # SSE types are non-dotted (mission_start); the event bus
            # wildcard "mission.*" needs dotted types (mission.start).
            bus_type = "mission." + event["type"].split("_", 1)[-1]
            await event_bus.emit(
                Event(
                    type=bus_type,
                    source="mission",
                    data=event.get("payload", {}),
                )
            )
        except Exception:  # pragma: no cover - bus must never break the flow
            logger.debug("event bus publish failed", exc_info=True)

    emit = _emit

    project_id = await project_manager.resolve_project_for_request(message)
    created_project = project_id is None and level == "project"
    if project_id is None:
        slug = _slugify(message)
        project = await project_manager.create_project(
            name=slug, description=message[:120], domain=select_domain(message)
        )
        project_id = project.id

    project = await project_manager.get_project(project_id)
    domain = select_domain(message)
    await project_manager.touch(project_id)

    mission = await project_manager.add_mission(
        project_id=project_id,
        title=message[:60],
        goal=message,
        complexity=level,
        domain=domain,
    )
    await project_manager.update_mission(mission.id, status="active", started_at=datetime.now())

    if emit:
        await emit({"type": "project_resolved", "payload": {"project_id": project_id}})
        await emit({"type": "domain_selected", "payload": {"domain": domain}})
        await emit(
            {
                "type": "mission_start",
                "payload": {
                    "mission_id": mission.id,
                    "title": mission.title,
                    "complexity": level,
                    "project_id": project_id,
                },
            }
        )

    master = domain_registry.get(domain) if domain_registry else None
    result = None
    if master is not None:
        task = Task(name=mission.title, description=mission.goal, assigned_to=domain)
        result = await master.execute_task(task)
        status = "completed" if result.status == "completed" else "failed"
        await project_manager.update_mission(
            mission.id, status=status, completed_at=datetime.now()
        )

        if result.status == "completed":
            fact_check = None
            if fact_checker is not None:
                try:
                    fact_check = await fact_checker(mission.title, result.content)
                except Exception as e:  # pragma: no cover - LLM-dependent
                    logger.warning("Fact check gate failed: %s", e)
                    fact_check = {
                        "verified": False,
                        "issues": [f"fact check error: {e}"],
                        "summary": "unverified",
                    }
                if emit:
                    await emit(
                        {
                            "type": "mission_factcheck",
                            "payload": {
                                "mission_id": mission.id,
                                "project_id": project_id,
                                "fact_check": fact_check,
                            },
                        }
                    )

            report = _build_mission_report(mission, project, result, fact_check, status)
            await project_manager.add_artifact(
                project_id=project_id,
                name="mission report",
                artifact_type="report",
                content=report,
            )
            await project_manager.add_decision(
                project_id=project_id,
                topic=mission.title[:80],
                decision=result.content[:500],
                context=message[:200],
            )
            if emit:
                await emit(
                    {
                        "type": "mission_report",
                        "payload": {
                            "mission_id": mission.id,
                            "project_id": project_id,
                            "report": report,
                            "fact_check": fact_check,
                        },
                    }
                )
        if emit:
            await emit(
                {
                    "type": "mission_step",
                    "payload": {
                        "mission_id": mission.id,
                        "project_id": project_id,
                        "status": status,
                        "confidence": result.confidence,
                        "issues": result.issues,
                    },
                }
            )
    else:
        await project_manager.update_mission(mission.id, status="failed")
        if emit:
            await emit(
                {
                    "type": "mission_step",
                    "payload": {
                        "mission_id": mission.id,
                        "project_id": project_id,
                        "status": "failed",
                        "error": f"domain '{domain}' has no master",
                    },
                }
            )

    return {
        "skipped": False,
        "complexity": complexity,
        "project_id": project_id,
        "created_project": created_project,
        "domain": domain,
        "mission": mission.model_dump(mode="json"),
        "result": result.to_dict() if result is not None else None,
    }


def _build_mission_report(mission, project, result, fact_check, status) -> str:
    """Compose the markdown mission report artifact from flow outputs."""
    lines = [
        f"# Mission Report: {mission.title}",
        "",
        f"- **Project**: {project.name if project else '-'}",
        f"- **Domain**: {mission.domain}",
        f"- **Complexity**: {mission.complexity}",
        f"- **Status**: {status}",
        f"- **Confidence**: {result.confidence}",
    ]
    if getattr(result, "issues", None):
        lines.append(f"- **Issues**: {'; '.join(result.issues[:5])}")
    if fact_check is not None:
        verdict = "verified" if fact_check.get("verified") else "unverified"
        lines.append(
            f"- **Fact check**: {verdict} — {fact_check.get('summary', '')}"
        )
        fc_issues = fact_check.get("issues") or []
        if fc_issues:
            lines.append(f"- **Fact-check issues**: {'; '.join(fc_issues[:5])}")
    lines.extend(["", "## Result", "", result.content])
    return "\n".join(lines)


def _slugify(message: str) -> str:
    import re

    words = re.findall(r"[a-zA-Z0-9]+", message.lower())
    stem = "-".join(words[:3]) if words else "project"
    return stem[:40] or "project"
