"""PCB Provider — Abstract base for electronics design integrations.

Supported platforms: KiCad, EasyEDA, Fusion Electronics, Altium
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


class PCBFormat(str, Enum):
    GERBER = "gerber"
    DRILL = "drill"
    BOM = "bom"
    PICK_AND_PLACE = "pnp"
    NETLIST = "netlist"
    SCHEMATIC_PDF = "schematic_pdf"
    PCB_PDF = "pcb_pdf"
    IPC2581 = "ipc2581"


class ComponentType(str, Enum):
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    DIODE = "diode"
    TRANSISTOR = "transistor"
    IC = "ic"
    CONNECTOR = "connector"
    LED = "led"
    SENSOR = "sensor"
    MCU = "mcu"
    REGULATOR = "regulator"
    CRYSTAL = "crystal"
    OTHER = "other"


class PCBProvider(ABC):
    """Abstract base class for PCB design platform integrations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform name (e.g., 'kicad', 'easyeda', 'fusion_electronics')."""
        ...

    @property
    @abstractmethod
    def supported_formats(self) -> List[PCBFormat]:
        """List of export formats this provider supports."""
        ...

    @abstractmethod
    async def create_project(self, name: str, params: Dict[str, Any]) -> Dict:
        """Create a new PCB project.

        Args:
            name: Project name
            params: Project parameters (layers, board_size, etc.)

        Returns:
            Dict with project_id, name, path
        """
        ...

    @abstractmethod
    async def add_component(
        self, project_id: str, component: Dict[str, Any]
    ) -> Dict:
        """Add component to schematic.

        Args:
            project_id: Project ID
            component: Component info (type, value, footprint, reference)

        Returns:
            Dict with component_id, reference, footprint
        """
        ...

    @abstractmethod
    async def connect_nets(
        self, project_id: str, connections: List[Dict[str, str]]
    ) -> Dict:
        """Connect nets in schematic.

        Args:
            project_id: Project ID
            connections: List of {from_pin, to_pin} connections

        Returns:
            Dict with net_count, connections_made
        """
        ...

    @abstractmethod
    async def route(self, project_id: str, params: Dict[str, Any]) -> Dict:
        """Route PCB traces.

        Args:
            project_id: Project ID
            params: Routing parameters (trace_width, via_size, etc.)

        Returns:
            Dict with traces_routed, unrouted_count, drc_errors
        """
        ...

    @abstractmethod
    async def check_drc(self, project_id: str) -> Dict:
        """Run Design Rule Check.

        Returns:
            Dict with errors, warnings, passed
        """
        ...

    @abstractmethod
    async def export(
        self, project_id: str, format: PCBFormat, output_path: str
    ) -> Dict:
        """Export project files.

        Returns:
            Dict with file_path, file_size, format
        """
        ...

    @abstractmethod
    async def generate_bom(self, project_id: str) -> Dict:
        """Generate Bill of Materials.

        Returns:
            Dict with components list, total_cost, sourceable
        """
        ...

    @abstractmethod
    async def get_schematic_info(self, project_id: str) -> Dict:
        """Get schematic information.

        Returns:
            Dict with components, nets, sheets
        """
        ...

    @abstractmethod
    async def list_projects(self, workspace: Optional[str] = None) -> List[Dict]:
        """List PCB projects.

        Returns:
            List of dicts with project_id, name, path, modified_date
        """
        ...

    async def suggest_component(
        self, params: Dict[str, Any]
    ) -> List[Dict]:
        """Suggest components based on requirements.

        Args:
            params: Requirements (type, value, voltage, package, etc.)

        Returns:
            List of matching components with specs and availability
        """
        return []

    async def calculate_trace_width(
        self, current: float, layers: int = 2, temp_rise: float = 10
    ) -> Dict:
        """Calculate PCB trace width for given current.

        Uses IPC-2221 standard.

        Returns:
            Dict with width_mm, resistance, voltage_drop
        """
        # IPC-2221 trace width calculation
        import math

        k = 0.024 if layers <= 1 else 0.048  # inner/outer layer
        b = 0.44
        c = 0.725

        area = (current / (k * temp_rise ** b)) ** (1 / c)
        width_mil = area / (1.0 * 1.0)  # 1oz copper, 1mil thickness
        width_mm = width_mil * 0.0254

        return {
            "width_mm": round(width_mm, 2),
            "width_mil": round(width_mil, 1),
            "copper_weight": "1oz",
            "temp_rise": temp_rise,
        }
