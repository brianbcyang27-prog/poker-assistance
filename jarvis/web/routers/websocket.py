"""WebSocket router for real-time agent status updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import asyncio
from typing import Set

from jarvis.web.main import jarvis

router = APIRouter(tags=["websocket"])

# Connected WebSocket clients
_clients: Set[WebSocket] = set()


async def broadcast_status():
    """Broadcast agent status to all connected clients."""
    if not _clients or not jarvis:
        return
    
    status = jarvis.get_status()
    
    # Add worker details for each king
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
    
    message = json.dumps({
        "type": "status",
        "data": status
    })
    
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
        if jarvis:
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
            await websocket.send_text(json.dumps({"type": "status", "data": status}))
        
        # Keep connection alive
        while True:
            try:
                # Wait for messages from client (keeps connection alive)
                await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            except asyncio.TimeoutError:
                # No message, but connection still alive
                # Send periodic status update
                if jarvis:
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
                    await websocket.send_text(json.dumps({"type": "status", "data": status}))
    
    except WebSocketDisconnect:
        _clients.discard(websocket)
    except Exception as e:
        _clients.discard(websocket)
    finally:
        _clients.discard(websocket)
