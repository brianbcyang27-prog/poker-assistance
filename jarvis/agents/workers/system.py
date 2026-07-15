"""System Workers - ♣ Suit."""

from .base import BaseWorker
from ...core.models import Suit, Rank


class FilesWorker(BaseWorker):
    """♣ Queen - File Manager."""
    
    def __init__(self):
        super().__init__(suit=Suit.CLUBS, rank=Rank.QUEEN)
    
    @property
    def name(self) -> str:
        return "Files"
    
    @property
    def title(self) -> str:
        return "File Manager"
    
    def get_system_prompt(self) -> str:
        return """You are the File Manager (♣Q).
Specialize in: file operations, directory management, organization.
Focus on: safety, backup, clear naming, organization.
Manage files safely and efficiently."""


class TerminalWorker(BaseWorker):
    """♣ Jack - Terminal Specialist."""
    
    def __init__(self):
        super().__init__(suit=Suit.CLUBS, rank=Rank.JACK)
    
    @property
    def name(self) -> str:
        return "Terminal"
    
    @property
    def title(self) -> str:
        return "Terminal Specialist"
    
    def get_system_prompt(self) -> str:
        return """You are the Terminal Specialist (♣J).
Specialize in: command line, shell scripts, automation, system commands.
Focus on: safety, efficiency, documentation, error handling.
Execute terminal operations safely."""


class ApplicationsWorker(BaseWorker):
    """♣ 10 - Application Manager."""
    
    def __init__(self):
        super().__init__(suit=Suit.CLUBS, rank=Rank.TEN)
    
    @property
    def name(self) -> str:
        return "Applications"
    
    @property
    def title(self) -> str:
        return "Application Manager"
    
    def get_system_prompt(self) -> str:
        return """You are the Application Manager (♣10).
Specialize in: application management, process control, system resources.
Focus on: performance, stability, resource efficiency.
Manage applications and system resources effectively."""
