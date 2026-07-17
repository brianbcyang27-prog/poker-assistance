"""Mechanical Provider — Abstract base for mechanical engineering support.

Covers: materials, fasteners, bearings, gears, motion, calculations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


class MaterialCategory(str, Enum):
    METAL = "metal"
    POLYMER = "polymer"
    CERAMIC = "ceramic"
    COMPOSITE = "composite"
    ELASTOMER = "elastomer"
    WOOD = "wood"


class MechanicalProvider(ABC):
    """Abstract base class for mechanical engineering support."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        ...

    @abstractmethod
    async def get_material(self, material_id: str) -> Dict:
        """Get material properties.

        Returns:
            Dict with name, category, density, yield_strength, etc.
        """
        ...

    @abstractmethod
    async def search_materials(
        self,
        category: Optional[MaterialCategory] = None,
        min_strength: Optional[float] = None,
        max_density: Optional[float] = None,
        max_cost: Optional[str] = None,
    ) -> List[Dict]:
        """Search materials by properties.

        Returns:
            List of matching materials with properties
        """
        ...

    @abstractmethod
    async def select_fastener(
        self, load: float, material: str, environment: str
    ) -> List[Dict]:
        """Select appropriate fasteners.

        Args:
            load: Expected load in Newtons
            material: Mating material
            environment: Operating environment (indoor, outdoor, marine, etc.)

        Returns:
            List of recommended fasteners with specs
        """
        ...

    @abstractmethod
    async def select_bearing(
        self, load: float, speed: float, shaft_diameter: float
    ) -> List[Dict]:
        """Select appropriate bearings.

        Args:
            load: Radial/axial load in Newtons
            speed: Rotational speed in RPM
            shaft_diameter: Shaft diameter in mm

        Returns:
            List of recommended bearings with specs
        """
        ...

    @abstractmethod
    async def design_gear_train(
        self,
        input_speed: float,
        output_speed: float,
        torque: float,
        ratio_tolerance: float = 0.01,
    ) -> Dict:
        """Design a gear train.

        Args:
            input_speed: Input RPM
            output_speed: Desired output RPM
            torque: Required output torque in Nm

        Returns:
            Dict with gear_ratio, gears, efficiency, layout
        """
        ...

    @abstractmethod
    async def calculate_motion(
        self,
        mass: float,
        distance: float,
        time: float,
        friction_coefficient: float = 0.3,
    ) -> Dict:
        """Calculate motion parameters (force, power, energy).

        Returns:
            Dict with force, power, energy, acceleration
        """
        ...

    @abstractmethod
    async def calculate_beam(
        self,
        beam_type: str,
        length: float,
        load: float,
        material: str,
        cross_section: Dict[str, float],
    ) -> Dict:
        """Calculate beam deflection and stress.

        Args:
            beam_type: 'cantilever', 'simply_supported', 'fixed'
            length: Beam length in meters
            load: Applied load in Newtons
            material: Material ID
            cross_section: Cross-section dimensions

        Returns:
            Dict with deflection, stress, safety_factor
        """
        ...

    async def get_material_comparison(
        self, material_ids: List[str], property: str
    ) -> Dict:
        """Compare materials by a specific property.

        Returns:
            Dict with comparison data
        """
        materials = []
        for mid in material_ids:
            mat = await self.get_material(mid)
            if mat:
                materials.append({
                    "id": mid,
                    "name": mat.get("name", mid),
                    "value": mat.get(property, None),
                })
        return {"property": property, "materials": materials}
