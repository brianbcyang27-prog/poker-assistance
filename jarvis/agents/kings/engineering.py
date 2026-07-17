"""Engineering King - ♠ King of Spades."""

from .base import BaseKing
from ...core.models import Suit


class EngineeringKing(BaseKing):
    """♠ King - Engineering Division Director.
    
    Personality: Perfectionist, strict, code quality focused.
    Responsible for: Software development, hardware engineering, architecture, testing.
    Now covers: CAD, PCB, embedded systems, mechanical engineering, hardware testing.
    """
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES)
        self._register_engineering_workers()
    
    def _register_engineering_workers(self):
        """Register all engineering workers including new hardware specialists."""
        from ..workers.engineering import (
            ArchitectWorker, BackendWorker, FrontendWorker, ReactWorker,
            PythonWorker, TestingWorker, DocsWorker, A11yWorker,
            CADWorker, PCBWorker, FirmwareWorker, MechanicalWorker,
            HardwareTestWorker,
        )
        
        # Software workers
        self.register_worker(ArchitectWorker())
        self.register_worker(BackendWorker())
        self.register_worker(FrontendWorker())
        self.register_worker(ReactWorker())
        self.register_worker(PythonWorker())
        self.register_worker(TestingWorker())
        self.register_worker(DocsWorker())
        self.register_worker(A11yWorker())
        
        # Hardware engineering workers
        self.register_worker(CADWorker())
        self.register_worker(PCBWorker())
        self.register_worker(FirmwareWorker())
        self.register_worker(MechanicalWorker())
        self.register_worker(HardwareTestWorker())
    
    @property
    def name(self) -> str:
        return "Engineering King"
    
    @property
    def title(self) -> str:
        return "Director of Engineering"
    
    @property
    def personality(self) -> str:
        return (
            "Perfectionist and strict. "
            "Obsessed with code quality, testing, and clean architecture. "
            "Now also covers hardware engineering: CAD, PCB, embedded, mechanical. "
            "Will not approve work that doesn't meet high standards."
        )
    
    def _get_worker_for_task(self, task_description: str) -> str:
        """Select the appropriate worker based on task description."""
        desc = task_description.lower()
        
        # Hardware engineering tasks
        if any(kw in desc for kw in ["cad", "3d model", "stl", "parametric", "fusion", "blender", "openscad", "solidworks"]):
            return "♠4M"  # MechanicalWorker (CAD)
        if any(kw in desc for kw in ["pcb", "circuit board", "schematic", "gerber", "kicad", "eagle", "layout"]):
            return "♠3"   # PCBWorker
        if any(kw in desc for kw in ["firmware", "arduino", "esp32", "embedded", "platformio", "micropython", "upload code"]):
            return "♠2"   # FirmwareWorker
        if any(kw in desc for kw in ["mechanical", "stress", "deflection", "gear", "bearing", "material strength", "thermal analysis"]):
            return "♠4M"  # MechanicalWorker
        if any(kw in desc for kw in ["test", "oscilloscope", "multimeter", "validation", "measure", "calibration"]):
            return "♠3T"  # HardwareTestWorker
        
        # Software tasks (delegate to parent)
        return super()._get_worker_for_task(task_description)
    
    def get_model_config(self) -> dict:
        """Engineering-specific model configuration."""
        return {
            "temperature": 0.3,  # Lower temperature for engineering precision
            "max_tokens": 4096,
        }
