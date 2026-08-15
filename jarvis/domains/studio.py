"""3D Studio domain — modeling, rendering, animation, fabrication (new in v10).

Studio workers build on the existing CAD/Blender assets:
jarvis.engineering.cad.base (CADProvider: Fusion 360, Onshape, Blender,
Tinkercad, OpenSCAD) and jarvis.computer.applications.blender/fusion360.
"""

from .base import DomainMaster, DomainWorker
from .models import Domain


class ModelingWorker(DomainWorker):
    """Parametric and organic 3D modeling via the CAD providers."""

    def get_system_prompt(self) -> str:
        return (
            "You are the 3D Modeler. Create and edit 3D models using the available "
            "CAD providers (Fusion 360, Onshape, Blender, Tinkercad, OpenSCAD). "
            "Prefer parametric, dimension-driven design and production-ready geometry."
        )


class RenderingWorker(DomainWorker):
    """Photorealistic and stylized rendering."""

    def get_system_prompt(self) -> str:
        return (
            "You are the 3D Renderer. Produce high-quality renders: set up cameras, "
            "lighting, materials, and scene composition (Blender Cycles/EEVEE). "
            "Deliver render settings and batch scripts with every output."
        )


class AnimationWorker(DomainWorker):
    """3D animation, rigging, and camera motion."""

    def get_system_prompt(self) -> str:
        return (
            "You are the 3D Animator. Create keyframed and procedural animation, "
            "rigging, and camera motion in Blender. Keep motion readable and "
            "production-ready; document frame ranges and output formats."
        )


class FabricationWorker(DomainWorker):
    """Manufacturing readiness: slicing, toolpaths, and export formats."""

    def get_system_prompt(self) -> str:
        return (
            "You are the Fabrication Specialist. Prepare models for manufacturing: "
            "check manifold geometry, tolerances, and wall thickness, then export "
            "fabrication-ready formats (STL, STEP, G-code-oriented toolpaths)."
        )


class StudioMaster(DomainMaster):
    """3D Studio domain master — head of 3D creation and fabrication."""

    def __init__(self):
        super().__init__(Domain.STUDIO, "studio.master")

    @property
    def name(self) -> str:
        return "3D Master"

    @property
    def title(self) -> str:
        return "Head of 3D Creation & Fabrication"

    def _build_members(self) -> None:
        self.register_member(ModelingWorker(Domain.STUDIO, "studio.modeling"))
        self.register_member(RenderingWorker(Domain.STUDIO, "studio.rendering"))
        self.register_member(AnimationWorker(Domain.STUDIO, "studio.animation"))
        self.register_member(FabricationWorker(Domain.STUDIO, "studio.fabrication"))
