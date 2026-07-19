"""WebSocket router for real-time agent status + Event Bus events."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import asyncio
from typing import Optional, Set

import jarvis.web.main as web_main

router = APIRouter(tags=["websocket"])

# Connected WebSocket clients
_clients: Set[WebSocket] = set()

# Event history for late joiners (ring buffer)
_event_history: list[dict] = []
MAX_EVENT_HISTORY = 100

# Tracked background tasks
_bridge_tasks: list = set()

# Event type to human-readable labels
EVENT_LABELS = {
    "system.started": "System initialized",
    "jarvis.thinking": "Analyzing your request",
    "jarvis.delegated": "Delegating to specialist",
    "jarvis.responded": "Preparing response",
    "king.planning": "Planning execution strategy",
    "king.delegated": "Assigning workers",
    "king.completed": "Reviewing results",
    "worker.started": "Worker began task",
    "worker.completed": "Worker finished task",
    "worker.error": "Worker encountered error",
    "worker.tool_call": "Using tool",
    "king.worker_result": "Worker reported back",
    "mission.started": "Mission started",
    "mission.progress": "Mission progressing",
    "mission.completed": "Mission complete",
    "mission.failed": "Mission failed",
    "memory.retrieved": "Retrieving memories",
    "rag.retrieved": "Searching knowledge base",
    "review.passed": "Quality review passed",
    "review.failed": "Quality review failed",
}

# Event type to visual state for Three.js core
EVENT_VISUAL_STATE = {
    "system.started": "idle",
    "jarvis.thinking": "thinking",
    "jarvis.delegated": "delegating",
    "jarvis.responded": "speaking",
    "king.planning": "planning",
    "king.delegated": "delegating",
    "king.completed": "reviewing",
    "worker.started": "working",
    "worker.completed": "working",
    "worker.error": "error",
    "worker.tool_call": "working",
    "mission.started": "mission_active",
    "mission.progress": "mission_active",
    "mission.completed": "complete",
    "mission.failed": "error",
    "memory.retrieved": "retrieving",
    "rag.retrieved": "retrieving",
    "review.passed": "complete",
    "review.failed": "error",
}

# Event type to visual hint
EVENT_ICONS = {
    "system.started": "\u2699",
    "jarvis.thinking": "\U0001f9e0",
    "jarvis.delegated": "\u2b07",
    "jarvis.responded": "\u2714",
    "king.planning": "\U0001f4cb",
    "king.delegated": "\U0001f464",
    "king.completed": "\U0001f44d",
    "worker.started": "\u25b6",
    "worker.completed": "\u2714",
    "worker.error": "\u274c",
    "worker.tool_call": "\U0001f527",
    "mission.started": "\U0001f3af",
    "mission.progress": "\u2b05",
    "mission.completed": "\u2714\ufe0f",
    "mission.failed": "\u274c",
    "memory.retrieved": "\U0001f4da",
    "rag.retrieved": "\U0001f50d",
    "review.passed": "\u2705",
    "review.failed": "\u274c",
}


def _get_status_with_workers():
    """Get jarvis status including worker details."""
    jarvis = web_main.jarvis
    if not jarvis:
        return None
    status = jarvis.get_status()
    for king_id, king_data in status.get("kings", {}).items():
        king = jarvis.get_king(king_id)
        if king:
            king_data["workers"] = {
                w.card_id: {
                    "card_id": w.card_id,
                    "name": w.name,
                    "state": w.state.value,
                }
                for w in king.get_all_workers()
            }
    return status


def _setup_event_bridge():
    """Subscribe to Event Bus and store events for WebSocket streaming."""
    global _bridge_tasks
    if _bridge_tasks:
        return  # Already set up

    try:
        from jarvis.core.events import event_bus, Event

        async def on_event(event: Event):
            global _clients
            label = EVENT_LABELS.get(event.type, event.type)
            icon = EVENT_ICONS.get(event.type, "\u2022")

            entry = {
                "type": "event",
                "data": {
                    "event_type": event.type,
                    "source": event.source,
                    "payload": event.data,
                    "timestamp": event.timestamp,
                    "label": label,
                    "icon": icon,
                },
            }
            _event_history.append(entry)
            if len(_event_history) > MAX_EVENT_HISTORY:
                del _event_history[:len(_event_history) - MAX_EVENT_HISTORY]

            # Broadcast to all connected clients
            message = json.dumps(entry)
            disconnected = set()
            tasks = []
            for client in list(_clients):
                try:
                    tasks.append(asyncio.ensure_future(client.send_text(message)))
                except Exception:
                    disconnected.add(client)
            _clients -= disconnected

            # Also broadcast visual state change for Three.js
            visual_state = EVENT_VISUAL_STATE.get(event.type)
            if visual_state:
                state_msg = json.dumps({"type": "visual_state", "state": visual_state})
                for client in list(_clients):
                    try:
                        tasks.append(asyncio.ensure_future(client.send_text(state_msg)))
                    except Exception:
                        disconnected.add(client)
                _clients -= disconnected

            # Send agent conversation data for right panel
            conv_data = _extract_conversation(event)
            if conv_data:
                conv_msg = json.dumps({"type": "agent_conversation", "data": conv_data})
                for client in list(_clients):
                    try:
                        tasks.append(asyncio.ensure_future(client.send_text(conv_msg)))
                    except Exception:
                        disconnected.add(client)
                _clients -= disconnected

            if tasks:
                try:
                    await asyncio.gather(*tasks, return_exceptions=True)
                except Exception:
                    pass

        # Subscribe to all JARVIS events
        loop = asyncio.get_event_loop()
        subscriptions = [
            ("jarvis.*", on_event),
            ("king.*", on_event),
            ("worker.*", on_event),
            ("system.*", on_event),
            ("mission.*", on_event),
            ("memory.*", on_event),
            ("rag.*", on_event),
            ("review.*", on_event),
        ]
        for event_type, handler in subscriptions:
            t = loop.create_task(event_bus.on(event_type, handler))
            _bridge_tasks.append(t)
    except Exception:
        pass  # Don't fail WebSocket setup if event bus unavailable


def _extract_conversation(event) -> Optional[dict]:
    """Extract agent conversation data from an event for the right panel."""
    d = event.data or {}

    if event.type == "king.planning":
        return {
            "sender": d.get("king", "?"),
            "title": _get_agent_title(d.get("king")),
            "card_id": d.get("king", "?"),
            "content": f"Planning: {d.get('task', 'task')}",
        }

    if event.type == "king.delegated":
        workers = d.get("workers", [])
        return {
            "sender": d.get("king", "?"),
            "title": _get_agent_title(d.get("king")),
            "card_id": d.get("king", "?"),
            "receiver": ", ".join(workers) if workers else "?",
            "content": f"Delegating {len(workers)} worker(s) for: {d.get('task', 'task')}",
        }

    if event.type == "king.completed":
        return {
            "sender": d.get("king", "?"),
            "title": _get_agent_title(d.get("king")),
            "card_id": d.get("king", "?"),
            "content": f"Review complete — confidence: {d.get('confidence', 0):.0%}",
        }

    if event.type == "worker.started":
        return {
            "sender": d.get("worker", "?"),
            "title": _get_agent_title(d.get("worker")),
            "card_id": d.get("worker", "?"),
            "content": f"Started: {d.get('task', 'task')}",
        }

    if event.type == "worker.completed":
        conf = d.get("confidence", 0)
        issues = d.get("issues", [])
        content = f"Done — confidence: {conf:.0%}"
        if issues:
            content += f", {len(issues)} issue(s)"
        return {
            "sender": d.get("worker", "?"),
            "title": _get_agent_title(d.get("worker")),
            "card_id": d.get("worker", "?"),
            "content": content,
        }

    if event.type == "worker.error":
        return {
            "sender": d.get("worker", "?"),
            "title": _get_agent_title(d.get("worker")),
            "card_id": d.get("worker", "?"),
            "content": f"Error: {d.get('error', 'unknown')[:100]}",
        }

    if event.type == "worker.tool_call":
        return {
            "sender": d.get("worker", "?"),
            "title": _get_agent_title(d.get("worker")),
            "card_id": d.get("worker", "?"),
            "content": f"Tool: {d.get('action', '?')}({d.get('params', '')})",
        }

    if event.type.startswith("mission."):
        return {
            "sender": "J",
            "title": "JARVIS",
            "card_id": "J",
            "content": f"{event.type.split('.')[-1].title()}: {d.get('goal', d.get('task', ''))[:80]}",
        }

    return None


def _get_agent_title(card_id: str) -> str:
    """Get human-readable title from card_id."""
    titles = {
        "J": "JARVIS",
        "\u2660K": "Engineering King",
        "\u2665K": "Personal King",
        "\u2666K": "Research King",
        "\u2663K": "System King",
    }
    if card_id in titles:
        return titles[card_id]
    # Worker cards like ♠A, ♥2, etc.
    suit_names = {"\u2660": "Eng", "\u2665": "Pers", "\u2666": "Res", "\u2663": "Sys"}
    for sym, name in suit_names.items():
        if card_id and card_id.startswith(sym):
            return f"{name} Worker"
    return card_id or "?"


async def broadcast_status():
    """Broadcast agent status to all connected clients."""
    if not _clients or not web_main.jarvis:
        return

    status = _get_status_with_workers()
    message = json.dumps({"type": "status", "data": status})

    disconnected = set()
    for client in list(_clients):
        try:
            await client.send_text(message)
        except Exception:
            disconnected.add(client)

    _clients -= disconnected


@router.websocket("/ws/agents")
async def websocket_agents(websocket: WebSocket):
    """Unified WebSocket: agent status + Event Bus events."""
    await websocket.accept()
    _clients.add(websocket)
    last_pong = asyncio.get_event_loop().time()

    # Setup event bridge on first connection
    if len(_clients) == 1:
        _setup_event_bridge()

    try:
        # Send initial status
        status = _get_status_with_workers()
        if status:
            await websocket.send_text(json.dumps({"type": "status", "data": status}))

        # Send recent event history
        for entry in _event_history[-20:]:
            await websocket.send_text(json.dumps(entry))

        # Keep connection alive, broadcast status every 5s, detect dead clients
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                last_pong = asyncio.get_event_loop().time()
                # Client heartbeat pong — if they send anything, they're alive
            except asyncio.TimeoutError:
                now = asyncio.get_event_loop().time()
                # If no pong in 30s, consider dead
                if now - last_pong > 30:
                    break
                status = _get_status_with_workers()
                if status:
                    try:
                        await websocket.send_text(json.dumps({"type": "status", "data": status}))
                    except Exception:
                        break

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _clients.discard(websocket)
