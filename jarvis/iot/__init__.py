"""JARVIS IoT — ESP32/Arduino WiFi device integration.

Lets JARVIS discover, monitor, and control ESP32 devices on the local network.
Devices register themselves via mDNS or manual config, then JARVIS can
send commands, read sensors, and manage them.
"""

from .manager import DeviceManager, device_manager
from .protocol import IoTMessage, IoTResponse

__all__ = [
    "DeviceManager",
    "device_manager",
    "IoTMessage",
    "IoTResponse",
]
