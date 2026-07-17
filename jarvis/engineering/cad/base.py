"""CAD Provider — Abstract base for 3D modeling integrations.

Supported platforms: Fusion 360, Onshape, Blender, Tinkercad, OpenSCAD
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


class CADFormat(str, Enum):
    STL = "stl"
    STEP = "step"
    OBJ = "obj"
    FBX = "fbx"
    IGES = "iges"
    PLY = "ply"
    SCAD = "scad"


class ModelType(str, Enum):
    PART = "part"
    ASSEMBLY = "assembly"
    SKETCH = "sketch"
    MESH = "mesh"


class CADProvider(ABC):
    """Abstract base class for CAD platform integrations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform name (e.g., 'fusion360', 'blender', 'openscad')."""
        ...

    @property
    @abstractmethod
    def supported_formats(self) -> List[CADFormat]:
        """List of export formats this provider supports."""
        ...

    @abstractmethod
    async def create_model(self, name: str, params: Dict[str, Any]) -> Dict:
        """Create a new 3D model.

        Args:
            name: Model name
            params: Platform-specific parameters (dimensions, features, etc.)

        Returns:
            Dict with model_id, name, path, type
        """
        ...

    @abstractmethod
    async def edit_model(self, model_id: str, changes: Dict[str, Any]) -> Dict:
        """Edit an existing model.

        Args:
            model_id: ID of model to edit
            changes: Dict of changes to apply

        Returns:
            Dict with updated model info
        """
        ...

    @abstractmethod
    async def export(
        self, model_id: str, format: CADFormat, output_path: str
    ) -> Dict:
        """Export model to specified format.

        Args:
            model_id: ID of model to export
            format: Target format (STL, STEP, OBJ, etc.)
            output_path: Output file path

        Returns:
            Dict with file_path, file_size, format
        """
        ...

    @abstractmethod
    async def get_measurements(self, model_id: str) -> Dict:
        """Get model measurements (dimensions, volume, surface area).

        Returns:
            Dict with dimensions, volume, surface_area, center_of_mass
        """
        ...

    @abstractmethod
    async def list_models(self, workspace: Optional[str] = None) -> List[Dict]:
        """List available models.

        Returns:
            List of dicts with model_id, name, type, modified_date
        """
        ...

    @abstractmethod
    async def get_model_info(self, model_id: str) -> Dict:
        """Get detailed model information.

        Returns:
            Dict with full model metadata
        """
        ...

    async def create_parametric(
        self, template: str, params: Dict[str, Any]
    ) -> Dict:
        """Create model from parametric template.

        Args:
            template: Template name (e.g., 'box', 'cylinder', 'bracket')
            params: Template parameters (width, height, depth, etc.)

        Returns:
            Dict with model_id, name, path
        """
        return {"error": "Parametric templates not supported by this provider"}

    async def check_manufacturability(self, model_id: str) -> Dict:
        """Check if model is suitable for manufacturing (3D printing, CNC, etc.).

        Returns:
            Dict with issues, warnings, recommendations
        """
        return {"issues": [], "warnings": [], "recommendations": []}
