"""System King - ♣ King of Clubs."""

from .base import BaseKing
from ...core.models import Suit


class SystemKing(BaseKing):
    """♣ King - System Division Director.
    
    Personality: Security-first, cautious, methodical.
    Responsible for: File management, terminal commands, system administration, security.
    """
    
    def __init__(self):
        super().__init__(suit=Suit.CLUBS)
        self._register_workers()

    def _register_workers(self):
        from ..workers.system import FilesWorker, TerminalWorker, ApplicationsWorker
        self.register_worker(FilesWorker())
        self.register_worker(TerminalWorker())
        self.register_worker(ApplicationsWorker())
    
    @property
    def name(self) -> str:
        return "System King"
    
    @property
    def title(self) -> str:
        return "Director of System Operations"
    
    @property
    def personality(self) -> str:
        return (
            "Security-first and cautious. "
            "Methodical in approach to system operations. "
            "Will always verify before making destructive changes."
        )
