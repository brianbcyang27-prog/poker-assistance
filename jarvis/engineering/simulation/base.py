"""Simulation Provider — Abstract base for engineering simulation.

Covers: thermal, stress, kinematic, circuit simulation.
Initial version defines interfaces for future implementation.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


class SimulationType(str, Enum):
    THERMAL = "thermal"
    STRESS = "stress"
    KINEMATIC = "kinematic"
    CIRCUIT = "circuit"
    CFD = "cfd"
    ELECTROMAGNETIC = "electromagnetic"


class SimulationStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SimulationProvider(ABC):
    """Abstract base class for simulation engines.

    This is an interface definition for future simulation integrations.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Simulation engine name."""
        ...

    @property
    @abstractmethod
    def supported_types(self) -> List[SimulationType]:
        """Types of simulation this engine supports."""
        ...

    @abstractmethod
    async def create_simulation(
        self, sim_type: SimulationType, params: Dict[str, Any]
    ) -> Dict:
        """Create a new simulation.

        Returns:
            Dict with simulation_id, type, status
        """
        ...

    @abstractmethod
    async def run(self, simulation_id: str) -> Dict:
        """Run simulation.

        Returns:
            Dict with status, progress, estimated_time
        """
        ...

    @abstractmethod
    async def get_results(self, simulation_id: str) -> Dict:
        """Get simulation results.

        Returns:
            Dict with results, metrics, visualization_data
        """
        ...

    @abstractmethod
    async def list_simulations(self) -> List[Dict]:
        """List all simulations.

        Returns:
            List of dicts with simulation_id, type, status, created_at
        """
        ...

    async def estimate_compute(self, sim_type: SimulationType, params: Dict) -> Dict:
        """Estimate compute requirements for a simulation.

        Returns:
            Dict with estimated_time, memory_required, cpu_cores
        """
        return {
            "estimated_time": "unknown",
            "memory_required": "unknown",
            "cpu_cores": "unknown",
            "note": "Estimation not available for this engine",
        }
