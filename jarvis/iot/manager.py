"""IoT Device Manager — discovers and controls ESP32/Arduino devices.

Devices register via:
1. mDNS auto-discovery (devices broadcast _jarvis-iot._tcp)
2. Manual config via /api/iot/register
3. Config file (devices.json)

JARVIS can then:
- List all devices
- Send commands ( digitalWrite, analogWrite, servo, etc. )
- Read sensors ( temperature, humidity, distance, etc. )
- Get device status
- OTA update (future)
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Optional
from datetime import datetime

import aiohttp

from .protocol import IoTMessage, IoTResponse, DeviceInfo


class DeviceManager:
    """Manages all connected IoT devices."""
    
    def __init__(self):
        self._devices: dict[str, DeviceInfo] = {}
        self._config_path = Path("devices.json")
        self._load_config()
        self._discovery_task: Optional[asyncio.Task] = None
    
    def _load_config(self):
        """Load device config from file."""
        if self._config_path.exists():
            try:
                with open(self._config_path) as f:
                    data = json.load(f)
                for d in data.get("devices", []):
                    info = DeviceInfo(**d)
                    self._devices[info.device_id] = info
            except Exception:
                pass
    
    def _save_config(self):
        """Save device config to file."""
        data = {
            "devices": [d.model_dump() for d in self._devices.values()]
        }
        with open(self._config_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def register_device(
        self,
        device_id: str,
        name: str,
        ip: str,
        port: int = 80,
        capabilities: list[str] = None,
        sensors: list[str] = None,
        actuators: list[str] = None,
        metadata: dict = None,
    ) -> DeviceInfo:
        """Register a new device (called by ESP32 on connect or manually)."""
        info = DeviceInfo(
            device_id=device_id,
            name=name,
            ip=ip,
            port=port,
            capabilities=capabilities or [],
            sensors=sensors or [],
            actuators=actuators or [],
            metadata=metadata or {},
        )
        self._devices[device_id] = info
        self._save_config()
        return info
    
    def unregister_device(self, device_id: str):
        """Remove a device."""
        self._devices.pop(device_id, None)
        self._save_config()
    
    def list_devices(self) -> list[dict]:
        """List all registered devices."""
        # Mark offline if not seen in 60s
        now = time.time()
        for d in self._devices.values():
            d.online = (now - d.last_seen) < 60
        
        return [d.model_dump() for d in self._devices.values()]
    
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """Get a specific device."""
        return self._devices.get(device_id)
    
    def get_status(self, device_id: str) -> dict:
        """Get device status (sync wrapper for tool executor)."""
        device = self._devices.get(device_id)
        if not device:
            return {"error": f"Device {device_id} not found"}
        return device.model_dump()
    
    async def send_command(
        self,
        device_id: str,
        command: str,
        payload: dict = None,
    ) -> dict:
        """Send a command to a device and wait for response."""
        device = self._devices.get(device_id)
        if not device:
            return {"error": f"Device {device_id} not found"}
        
        msg = IoTMessage(cmd=command, payload=payload or {})
        
        try:
            url = f"http://{device.ip}:{device.port}/jarvis"
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=msg.model_dump(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()
                    device.last_seen = time.time()
                    return data
        except asyncio.TimeoutError:
            return {"error": "Device timed out"}
        except Exception as e:
            return {"error": str(e)}
    
    async def read_sensor(self, device_id: str, sensor: str) -> dict:
        """Read a sensor value from a device."""
        return await self.send_command(device_id, "read_sensor", {"sensor": sensor})
    
    async def broadcast(self, command: str, payload: dict = None) -> dict:
        """Send a command to ALL online devices."""
        results = {}
        for device_id, device in self._devices.items():
            if device.online:
                results[device_id] = await self.send_command(device_id, command, payload)
        return results
    
    async def start_discovery(self):
        """Start mDNS discovery in background."""
        self._discovery_task = asyncio.create_task(self._discovery_loop())
    
    async def _discovery_loop(self):
        """Continuously look for new devices via mDNS."""
        while True:
            try:
                # Try zeroconf if available
                from zeroconf import ServiceBrowser, Zeroconf
                
                class Listener:
                    def __init__(self, manager):
                        self.manager = manager
                    
                    def add_service(self, zc, svc_type, name):
                        info = zc.get_service_info(svc_type, name)
                        if info:
                            ip = info.parsed_addresses()[0] if info.parsed_addresses() else None
                            if ip:
                                props = {k.decode(): v.decode() for k, v in info.properties.items()}
                                self.manager.register_device(
                                    device_id=props.get("id", name),
                                    name=props.get("name", name),
                                    ip=ip,
                                    port=info.port,
                                    capabilities=props.get("capabilities", "").split(","),
                                    sensors=props.get("sensors", "").split(","),
                                    actuators=props.get("actuators", "").split(","),
                                )
                    
                    def remove_service(self, zc, svc_type, name):
                        pass
                    
                    def update_service(self, zc, svc_type, name):
                        pass
                
                zc = Zeroconf()
                listener = Listener(self)
                browser = ServiceBrowser(zc, "_jarvis-iot._tcp.local.", listener)
                
                # Run for 30s then restart
                await asyncio.sleep(30)
                browser.cancel()
                zc.close()
                
            except ImportError:
                # zeroconf not installed, skip discovery
                await asyncio.sleep(60)
            except Exception:
                await asyncio.sleep(30)


# Singleton
device_manager = DeviceManager()
