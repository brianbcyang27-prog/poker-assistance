"""WebSocket router for real-time agent status + Event Bus events."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import asyncio
from typing import Set

import jarvis.web.main as web_main

router = APIRouter(tags=["websocket"])

# Connected WebSocket clients
_clients: Set[WebSocket] = set()

# Event history for late joiners
_event_history: list[dict] = []
MAX_EVENT_HISTORY = 100

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
    "worker.error": "idle",
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
    try:
        from jarvis.core.events import event_bus, Event

        async def on_event(event: Event):
            entry = {
                "type": "event",
                "data": {
                    "event_type": event.type,
                    "source": event.source,
                    "payload": event.data,
                    "timestamp": event.timestamp,
                    "label": EVENT_LABELS.get(event.type, event.type),
                    "icon": EVENT_ICONS.get(event.type, "\u2022"),
                },
            }
            _event_history.append(entry)
            if len(_event_history) > MAX_EVENT_HISTORY:
                _event_history.clear()

            # Broadcast to all connected clients
            message = json.dumps(entry)
            disconnected = set()
            for client in list(_clients):
                try:
                    asyncio.get_event_loop().create_task(client.send_text(message))
                except Exception:
                    disconnected.add(client)
            _clients -= disconnected

            # Also broadcast visual state change for Three.js
            visual_state = EVENT_VISUAL_STATE.get(event.type)
            if visual_state:
                state_msg = json.dumps({"type": "visual_state", "state": visual_state})
                for client in list(_clients):
                    try:
                        asyncio.get_event_loop().create_task(client.send_text(state_msg))
                    except Exception:
                        disconnected.add(client)
                _clients -= disconnected

        # Subscribe to all JARVIS events
        import asyncio
        loop = asyncio.get_event_loop()
        loop.create_task(event_bus.on("jarvis.*", on_event))
        loop.create_task(event_bus.on("king.*", on_event))
        loop.create_task(event_bus.on("worker.*", on_event))
        loop.create_task(event_bus.on("system.*", on_event))
    except Exception:
        pass  # Don't fail WebSocket setup if event bus unavailable


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

        # Keep connection alive, broadcast status every 5s
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            except asyncio.TimeoutError:
                status = _get_status_with_workers()
                if status:
                    await websocket.send_text(json.dumps({"type": "status", "data": status}))

    except WebSocketDisconnect:
        _clients.discard(websocket)
    except Exception:
        _clients.discard(websocket)
    finally:
        _clients.discard(websocket)
