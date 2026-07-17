"""IoT communication protocol between JARVIS and ESP32 devices.

Protocol: HTTP JSON over WiFi.
ESP32 runs a lightweight HTTP server.
JARVIS sends commands as JSON, ESP32 responds with JSON.

Message format:
{
    "cmd": "command_name",
    "payload": { ... },
    "id": "unique_message_id"
}

Response format:
{
    "status": "ok" | "error",
    "data": { ... },
    "id": "matching_message_id"
}
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
import uuid
import time


class IoTMessage(BaseModel):
    """Message sent TO an ESP32 device."""
    cmd: str
    payload: dict = Field(default_factory=dict)
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = Field(default_factory=time.time)


class IoTResponse(BaseModel):
    """Response FROM an ESP32 device."""
    status: str = "ok"
    data: dict = Field(default_factory=dict)
    id: str = ""
    timestamp: float = Field(default_factory=time.time)


class DeviceInfo(BaseModel):
    """Information about a connected ESP32 device."""
    device_id: str
    name: str
    ip: str
    port: int = 80
    capabilities: list[str] = Field(default_factory=list)
    sensors: list[str] = Field(default_factory=list)
    actuators: list[str] = Field(default_factory=list)
    last_seen: float = Field(default_factory=time.time)
    online: bool = True
    metadata: dict = Field(default_factory=dict)
