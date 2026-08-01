"""Embedded Provider — Abstract base for embedded systems integrations.

Supported platforms: Arduino, ESP32/PlatformIO, Raspberry Pi, STM32, MicroPython
"""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any


class Platform(StrEnum):
    ARDUINO = "arduino"
    ESP32 = "esp32"
    RASPBERRY_PI = "raspberry_pi"
    STM32 = "stm32"
    MICROPYTHON = "micropython"
    ESPIDF = "esp_idf"


class BuildStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    COMPILING = "compiling"
    UPLOADING = "uploading"
    UNKNOWN = "unknown"


class EmbeddedProvider(ABC):
    """Abstract base class for embedded systems integrations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform name."""
        ...

    @property
    @abstractmethod
    def supported_platforms(self) -> list[Platform]:
        """List of supported embedded platforms."""
        ...

    @abstractmethod
    async def create_project(self, name: str, platform: Platform, params: dict[str, Any]) -> dict:
        """Create a new embedded project.

        Args:
            name: Project name
            platform: Target platform (Arduino, ESP32, etc.)
            params: Project parameters (board, libraries, etc.)

        Returns:
            Dict with project_id, name, path, platform
        """
        ...

    @abstractmethod
    async def compile(self, project_id: str) -> dict:
        """Compile firmware.

        Returns:
            Dict with status, binary_path, size, warnings, errors
        """
        ...

    @abstractmethod
    async def upload(self, project_id: str, device: str) -> dict:
        """Upload firmware to device.

        Args:
            project_id: Project ID
            device: Serial port or device identifier

        Returns:
            Dict with status, device, upload_time
        """
        ...

    @abstractmethod
    async def monitor(self, project_id: str, device: str, duration: int = 10) -> dict:
        """Monitor serial output from device.

        Args:
            project_id: Project ID
            device: Serial port
            duration: Monitoring duration in seconds

        Returns:
            Dict with output lines, timestamps
        """
        ...

    @abstractmethod
    async def list_devices(self) -> list[dict]:
        """List connected devices.

        Returns:
            List of dicts with port, board, description
        """
        ...

    @abstractmethod
    async def list_boards(self, platform: Platform | None = None) -> list[dict]:
        """List supported boards.

        Returns:
            List of dicts with fqbn, name, platform
        """
        ...

    @abstractmethod
    async def install_library(self, library: str) -> dict:
        """Install a library.

        Returns:
            Dict with status, library, version
        """
        ...

    @abstractmethod
    async def list_libraries(self) -> list[dict]:
        """List installed libraries.

        Returns:
            List of dicts with name, version, author
        """
        ...

    async def generate_pin_map(self, board: str) -> dict:
        """Generate pin map for a board.

        Returns:
            Dict with pins, capabilities, constraints
        """
        return {"pins": [], "note": "Pin map generation not supported"}

    async def validate_pin_config(self, board: str, config: dict[str, Any]) -> dict:
        """Validate pin configuration for conflicts.

        Returns:
            Dict with valid, conflicts, warnings
        """
        return {"valid": True, "conflicts": [], "warnings": []}
