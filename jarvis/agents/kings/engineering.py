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
    

