"""Desktop surface router — data feeds for the fullscreen desktop app (/core).

Surfaces:
  * Today Board — aggregate todos from connectors (Apple Reminders/Calendar,
    Apple Mail, Google Calendar/Gmail) plus JARVIS's own active mission tasks.
  * Documents — research/mission reports (workspaces.final_report and
    project_artifacts) rendered as scrollable markdown in the desktop app.
  * Feedback — lightweight user feedback log from the surfaces.

Read-only aggregation is best-effort by design: a failing connector never
breaks the board, it reports itself as unavailable under ``sources``.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import jarvis.web.main as web_main
from jarvis.core.database import get_db
from jarvis.core.models import AgentState
from jarvis.integrations import get_registry

log = logging.getLogger("jarvis.desktop")

router = APIRouter(prefix="/api/desktop", tags=["desktop"])

# Hard deadline for the aggregate board — connectors must never hang the UI.
_BOARD_TIMEOUT = 18.0

GROUP_ORDER = [
    ("overdue", "OVERDUE"),
    ("today", "TODAY"),
    ("upcoming", "UPCOMING"),
    ("jarvis", "JARVIS ACTIVE"),
    ("inbox", "INBOX"),
]

_ACTIVE_TASK_STATES = {AgentState.PLANNING, AgentState.WORKING, AgentState.REVIEWING}

# ── helpers ────────────────────────────────────────────────────────────────


def _parse_dt(raw: str | None) -> datetime | None:
    """Tolerant datetime parser for connector date strings."""
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    # ISO 8601 (Google)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        pass
    # AppleScript locale date strings:
    # "Wednesday, August 12, 2026 at 9:00:00 AM"
    for fmt in (
        "%A, %B %d, %Y at %I:%M:%S %p",
        "%A, %B %d, %Y at %I:%M %p",
        "%B %d, %Y at %I:%M:%S %p",
        "%B %d, %Y at %I:%M %p",
        "%A, %B %d, %Y",
        "%B %d, %Y",
    ):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _group_for_due(due: datetime | None) -> str:
    """Bucket a due datetime into a Today Board group."""
    if due is None:
        return "inbox"
    now = datetime.now()
    if due < now:
        return "overdue"
    if due.date() == now.date():
        return "today"
    if due < now + timedelta(days=7):
        return "upcoming"
    return "inbox"


def _when_label(due: datetime | None) -> str:
    if due is None:
        return "no date"
    now = datetime.now()
    if due < now:
        return "overdue"
    if due.date() == now.date():
        return due.strftime("%H:%M")
    return due.strftime("%a %b %d")


# ── models ─────────────────────────────────────────────────────────────────


class TodoCompleteRequest(BaseModel):
    source: str
    title: str = ""
    action: str = ""
    workspace_id: str | None = None
    task_id: str | None = None


class FeedbackRequest(BaseModel):
    surface: str
    target: str = ""
    text: str


# ── Today Board ────────────────────────────────────────────────────────────


async def _collect_apple_items(registry) -> tuple[list[dict], list[dict]]:
    """Return (todo items, source notes)."""
    items: list[dict] = []
    notes: list[dict] = []
    apple = registry.get("apple")
    if apple is None:
        return items, notes

    async def reminders():
        res = await registry.run_action("apple", "reminders_list", {"list": "today"})
        if res.get("ok"):
            for reminder in res.get("reminders", []):
                name = reminder.get("name") if isinstance(reminder, dict) else reminder
                due = _parse_dt(reminder.get("due")) if isinstance(reminder, dict) else None
                if due is None:
                    due = datetime.now() - timedelta(minutes=1)
                items.append(
                    {
                        "id": f"apple-reminder:{name}",
                        "source": "apple",
                        "source_label": "REMINDERS",
                        "title": name,
                        "when": None,
                        "due": due,
                        "action": "apple-reminder",
                    }
                )
            notes.append({"id": "apple", "label": "Reminders", "ok": True})
        else:
            notes.append(
                {"id": "apple", "label": "Reminders", "ok": False, "error": res.get("error", "")}
            )

    async def calendar():
        res = await registry.run_action("apple", "calendar_upcoming", {"limit": 20})
        if res.get("ok"):
            for ev in res.get("events", []):
                due = _parse_dt(ev.get("when"))
                items.append(
                    {
                        "id": f"apple-calendar:{ev.get('summary')}:{ev.get('when')}",
                        "source": "apple",
                        "source_label": "CALENDAR",
                        "title": ev.get("summary", ""),
                        "when": ev.get("when", ""),
                        "due": due,
                        "action": "apple-calendar",
                    }
                )

    async def mail():
        res = await registry.run_action("apple", "mail_unread", {"limit": 8})
        if res.get("ok"):
            for msg in res.get("messages", []):
                items.append(
                    {
                        "id": f"apple-mail:{msg.get('subject')}",
                        "source": "apple",
                        "source_label": "MAIL",
                        "title": msg.get("subject", "(no subject)"),
                        "when": msg.get("sender", ""),
                        "due": None,
                        "action": "apple-mail",
                    }
                )

    await asyncio.gather(reminders(), calendar(), mail())
    return items, notes


async def _collect_google_items(registry) -> tuple[list[dict], list[dict]]:
    """Return (todo items, source notes)."""
    items: list[dict] = []
    notes: list[dict] = []
    google = registry.get("google")
    if google is None:
        return items, notes
    if not google.connected:
        notes.append({"id": "google", "label": "Google", "ok": False, "error": "not connected"})
        return items, notes

    async def calendar():
        res = await registry.run_action("google", "calendar_upcoming", {"limit": 20})
        if res.get("ok"):
            for ev in res.get("events", []):
                due = _parse_dt(ev.get("start"))
                items.append(
                    {
                        "id": f"google-calendar:{ev.get('summary')}:{ev.get('start')}",
                        "source": "google",
                        "source_label": "G-CALENDAR",
                        "title": ev.get("summary", ""),
                        "when": ev.get("start", ""),
                        "due": due,
                        "action": "google-calendar",
                    }
                )
            notes.append({"id": "google", "label": "Google Calendar", "ok": True})
        else:
            notes.append(
                {
                    "id": "google",
                    "label": "Google Calendar",
                    "ok": False,
                    "error": res.get("error", ""),
                }
            )

    async def mail():
        res = await registry.run_action("google", "gmail_unread_with_meta", {"limit": 8})
        if res.get("ok"):
            for msg in res.get("messages", []):
                items.append(
                    {
                        "id": f"google-mail:{msg.get('id')}",
                        "source": "google",
                        "source_label": "GMAIL",
                        "title": msg.get("subject", "(no subject)"),
                        "when": msg.get("from", ""),
                        "due": None,
                        "action": "google-mail",
                    }
                )

    await asyncio.gather(calendar(), mail())
    return items, notes


async def _collect_jarvis_items() -> list[dict]:
    """Active JARVIS mission tasks (from workspaces)."""
    items: list[dict] = []
    try:
        workspaces = await web_main.workspace_manager.get_active_workspaces()
    except Exception as exc:  # noqa: BLE001 — board must not break
        log.warning("Failed to collect jarvis tasks: %s", exc)
        return items
    for ws in workspaces:
        ws_id = getattr(ws, "id", "")
        for task in getattr(ws, "tasks", []):
            status = getattr(task, "status", None)
            if status not in _ACTIVE_TASK_STATES:
                continue
            items.append(
                {
                    "id": f"jarvis:{ws_id}:{task.id}",
                    "source": "jarvis",
                    "source_label": "JARVIS",
                    "title": task.name,
                    "when": getattr(ws, "goal", ""),
                    "due": None,
                    "action": "jarvis-task",
                    "workspace_id": ws_id,
                    "task_id": getattr(task, "id", ""),
                }
            )
    return items


@router.get("/todos/today")
async def todos_today():
    """Aggregate today's todos from every available source."""
    registry = get_registry()
    items: list[dict] = []
    sources: list[dict] = []

    apple_task = asyncio.create_task(_collect_apple_items(registry))
    google_task = asyncio.create_task(_collect_google_items(registry))
    jarvis_task = asyncio.create_task(_collect_jarvis_items())

    done, pending = await asyncio.wait(
        {apple_task, google_task, jarvis_task}, timeout=_BOARD_TIMEOUT
    )
    for task in pending:
        task.cancel()
    collected: list[tuple[list[dict], list[dict]] | list[dict]] = []
    for task in done:
        try:
            result = task.result()
        except asyncio.CancelledError:
            continue
        except Exception as exc:  # noqa: BLE001 — board must not break
            log.warning("Today Board collector failed: %s", exc)
            continue
        collected.append(result)

    for result in collected:
        if isinstance(result, list):
            items.extend(result)
        else:
            apple_part, notes_part = result
            items.extend(apple_part)
            sources.extend(notes_part)

    grouped: dict[str, list[dict]] = {key: [] for key, _ in GROUP_ORDER}
    for item in items:
        due = item.get("due")
        if isinstance(due, datetime):
            item["due"] = due.isoformat()
        key = _group_for_due(due)
        if key not in grouped:
            key = "inbox"
        grouped[key].append(item)

    for key in grouped:
        grouped[key].sort(key=lambda it: it.get("due") or "9999-12-31T23:59:59")

    summary = {
        "overdue": len(grouped["overdue"]),
        "today": len(grouped["today"]),
        "upcoming": len(grouped["upcoming"]),
        "jarvis": len(grouped["jarvis"]),
        "inbox": len(grouped["inbox"]),
        "total_open": len(items),
    }

    return {
        "date": date.today().isoformat(),
        "summary": summary,
        "sources": sources,
        "groups": [
            {"key": key, "label": label, "items": grouped[key]}
            for key, label in GROUP_ORDER
            if grouped[key]
        ],
    }


@router.post("/todos/complete")
async def todos_complete(req: TodoCompleteRequest):
    """Mark a Today Board item done (best-effort writeback)."""
    registry = get_registry()
    if req.action == "apple-reminder":
        res = await registry.run_action(
            "apple", "reminders_complete", {"name": req.title}
        )
        if not res.get("ok"):
            return {"ok": False, "reason": res.get("error", "apple writeback failed")}
        return {"ok": True, "source": "apple-reminder"}
    if req.action == "jarvis-task":
        if not req.workspace_id or not req.task_id:
            return {"ok": False, "reason": "missing workspace/task id"}
        ok = await web_main.workspace_manager.update_task_status(
            req.workspace_id, req.task_id, AgentState.COMPLETED
        )
        if not ok:
            return {"ok": False, "reason": "task not found"}
        return {"ok": True, "source": "jarvis-task"}
    return {"ok": False, "reason": f"no writeback for action {req.action!r}"}


# ── Documents ──────────────────────────────────────────────────────────────


async def _workspace_documents() -> list[dict]:
    try:
        db = await get_db()
        cursor = await db._db.execute(
            "SELECT * FROM workspaces "
            "WHERE final_report IS NOT NULL AND TRIM(final_report) != '' "
            "ORDER BY COALESCE(completed_at, created_at) DESC LIMIT 30"
        )
        rows = await cursor.fetchall()
    except Exception as exc:  # noqa: BLE001 — defensive query
        log.warning("workspace documents query failed: %s", exc)
        return []
    docs = []
    for row in rows:
        data = dict(row)
        docs.append(
            {
                "id": data.get("id", ""),
                "kind": "workspace",
                "title": data.get("goal") or data.get("user_request") or "Mission report",
                "subtitle": f"Mission report · {data.get('status', '')}",
                "date": data.get("completed_at") or data.get("created_at") or "",
                "snippet": (data.get("final_report") or "")[:160],
            }
        )
    return docs


async def _artifact_documents() -> list[dict]:
    try:
        db = await get_db()
        cursor = await db._db.execute(
            "SELECT * FROM project_artifacts "
            "WHERE artifact_type = 'report' ORDER BY created_at DESC LIMIT 30"
        )
        rows = await cursor.fetchall()
    except Exception as exc:  # noqa: BLE001 — defensive query
        log.warning("artifact documents query failed: %s", exc)
        return []
    docs = []
    for row in rows:
        data = dict(row)
        docs.append(
            {
                "id": str(data.get("id", "")),
                "kind": "artifact",
                "title": data.get("title") or "Artifact report",
                "subtitle": "Research report",
                "date": data.get("created_at") or "",
                "snippet": (data.get("content") or "")[:160],
            }
        )
    return docs


@router.get("/documents")
async def documents():
    """List recent JARVIS documents (mission reports + research artifacts)."""
    docs = await _workspace_documents() + await _artifact_documents()
    docs.sort(key=lambda d: d.get("date") or "", reverse=True)
    return {"documents": docs[:30]}


@router.get("/documents/{kind}/{doc_id}")
async def document_detail(kind: str, doc_id: str):
    """Fetch a single document's markdown content."""
    db = await get_db()
    if kind == "workspace":
        try:
            cursor = await db._db.execute(
                "SELECT * FROM workspaces WHERE id = ?", (doc_id,)
            )
            row = await cursor.fetchone()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"query failed: {exc}")
        if row is None:
            raise HTTPException(status_code=404, detail="Document not found")
        data = dict(row)
        return {
            "id": doc_id,
            "kind": kind,
            "title": data.get("goal") or data.get("user_request") or "Mission report",
            "date": data.get("completed_at") or data.get("created_at") or "",
            "content": data.get("final_report") or "",
        }
    if kind == "artifact":
        try:
            cursor = await db._db.execute(
                "SELECT * FROM project_artifacts WHERE id = ?", (doc_id,)
            )
            row = await cursor.fetchone()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"query failed: {exc}")
        if row is None:
            raise HTTPException(status_code=404, detail="Document not found")
        data = dict(row)
        return {
            "id": doc_id,
            "kind": kind,
            "title": data.get("title") or "Artifact report",
            "date": data.get("created_at") or "",
            "content": data.get("content") or "",
        }
    raise HTTPException(status_code=404, detail=f"Unknown document kind: {kind}")


# ── Feedback ───────────────────────────────────────────────────────────────


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Log user feedback from a desktop surface (capped history)."""
    if not req.text.strip():
        return {"ok": False, "reason": "empty feedback"}
    db = await get_db()
    raw = await db.get_preference("desktop.feedback")
    history: list[dict[str, Any]] = []
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                history = parsed
        except (json.JSONDecodeError, TypeError):
            history = []
    history.append(
        {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "surface": req.surface,
            "target": req.target,
            "text": req.text.strip(),
        }
    )
    history = history[-200:]
    await db.set_preference("desktop.feedback", json.dumps(history))
    log.info("desktop feedback (%s): %s", req.surface, req.text.strip()[:80])
    return {"ok": True, "count": len(history)}
