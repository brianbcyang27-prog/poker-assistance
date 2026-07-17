"""WebSocket router for real-time agent status updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import asyncio
from typing import Set

import jarvis.web.main as web_main

router = APIRouter(tags=["websocket"])

# Connected WebSocket clients
_clients: Set[WebSocket] = set()


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
    """WebSocket endpoint for real-time agent status."""
    await websocket.accept()
    _clients.add(websocket)
    
    try:
        # Send initial status immediately
        status = _get_status_with_workers()
        if status:
            await websocket.send_text(json.dumps({"type": "status", "data": status}))
        
        # Keep connection alive
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
