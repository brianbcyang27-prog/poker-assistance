"""Workers module - Specialized task executors."""

from .base import BaseWorker
from .engineering import (
    ArchitectWorker, BackendWorker, FrontendWorker,
    ReactWorker, PythonWorker, TestingWorker, DocsWorker, A11yWorker
)
from .personal import CalendarWorker, EmailWorker, TasksWorker, SchedulingWorker
from .research import WebResearchWorker, DocumentationWorker, FactCheckWorker
from .system import FilesWorker, TerminalWorker, ApplicationsWorker

__all__ = [
    "BaseWorker",
    "ArchitectWorker", "BackendWorker", "FrontendWorker",
    "ReactWorker", "PythonWorker", "TestingWorker", "DocsWorker", "A11yWorker",
    "CalendarWorker", "EmailWorker", "TasksWorker", "SchedulingWorker",
    "WebResearchWorker", "DocumentationWorker", "FactCheckWorker",
    "FilesWorker", "TerminalWorker", "ApplicationsWorker",
]
