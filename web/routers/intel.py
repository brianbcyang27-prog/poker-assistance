import asyncio
import json
import time
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter(tags=["intel"])


class IntelUpdate(BaseModel):
    status: str = "Ready"
    mission: dict = None
    thinking: dict = None
    agents: list = []
    cost: float = 0.0


# Connected WebSocket clients
_clients: Set[WebSocket] = set()
_start_time = time.time()
_api_calls = 0
_total_tokens = 0
_cost = 0.0


@router.get("/api/intel")
async def get_intel():
    elapsed = time.time() - _start_time
    minutes = int(elapsed / 60)
    uptime = f"{minutes}m" if minutes < 60 else f"{minutes // 60}h {minutes % 60}m"

    return {
        "status": "Ready",
        "uptime": uptime,
        "api_calls": _api_calls,
        "total_tokens": _total_tokens,
        "cost": _cost,
        "agents": [],
        "mission": None,
    }


@router.websocket("/ws/intel")
async def websocket_intel(websocket: WebSocket):
    await websocket.accept()
    _clients.add(websocket)
    try:
        while True:
            # Keep connection alive, receive any client messages
            data = await websocket.receive_text()
            # Client can send commands like {"type": "ping"}
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        _clients.discard(websocket)
    except Exception:
        _clients.discard(websocket)


async def broadcast(data: dict):
    """Send update to all connected WebSocket clients."""
    dead = set()
    for client in _clients:
        try:
            await client.send_json(data)
        except Exception:
            dead.add(client)
    _clients.difference_update(dead)


def track_api_call(tokens: int = 0, cost: float = 0.0):
    global _api_calls, _total_tokens, _cost
    _api_calls += 1
    _total_tokens += tokens
    _cost += cost
