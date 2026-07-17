"""IoT router — manage ESP32/Arduino devices from JARVIS."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from jarvis.iot.manager import device_manager

router = APIRouter(prefix="/api/iot", tags=["iot"])


class RegisterDeviceRequest(BaseModel):
    device_id: str
    name: str
    ip: str
    port: int = 80
    capabilities: list[str] = []
    sensors: list[str] = []
    actuators: list[str] = []
    metadata: dict = {}


class SendCommandRequest(BaseModel):
    command: str
    payload: dict = {}


@router.get("/devices")
async def list_devices():
    """List all registered IoT devices."""
    return device_manager.list_devices()


@router.post("/register")
async def register_device(req: RegisterDeviceRequest):
    """Register a new IoT device."""
    info = device_manager.register_device(
        device_id=req.device_id,
        name=req.name,
        ip=req.ip,
        port=req.port,
        capabilities=req.capabilities,
        sensors=req.sensors,
        actuators=req.actuators,
        metadata=req.metadata,
    )
    return info.model_dump()


@router.delete("/{device_id}")
async def unregister_device(device_id: str):
    """Remove an IoT device."""
    device_manager.unregister_device(device_id)
    return {"status": "removed"}


@router.get("/{device_id}")
async def get_device(device_id: str):
    """Get device details."""
    device = device_manager.get_device(device_id)
    if not device:
        return {"error": "Device not found"}
    return device.model_dump()


@router.post("/{device_id}/command")
async def send_command(device_id: str, req: SendCommandRequest):
    """Send a command to a device."""
    result = await device_manager.send_command(device_id, req.command, req.payload)
    return result


@router.get("/{device_id}/sensor/{sensor_name}")
async def read_sensor(device_id: str, sensor_name: str):
    """Read a sensor value from a device."""
    result = await device_manager.read_sensor(device_id, sensor_name)
    return result


@router.post("/broadcast")
async def broadcast_command(req: SendCommandRequest):
    """Send a command to ALL online devices."""
    result = await device_manager.broadcast(req.command, req.payload)
    return result
