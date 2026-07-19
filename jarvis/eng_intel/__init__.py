"""JARVIS Engineering Intelligence — continuous code analysis engine.

Provides eight built-in analyzers that scan Python projects for
duplication, naming issues, documentation gaps, complexity, dead code,
stale APIs, missing tests, and architectural drift.
"""

import os
from typing import Dict, List, Optional

from jarvis.eng_intel.engine import (
    ArchitectureDriftDetector,
    ComplexityAnalyzer,
    DeadCodeDetector,
    DocumentationChecker,
    DuplicationDetector,
    MissingTestDetector,
    NamingChecker,
    StaleAPIDetector,
)
from jarvis.eng_intel.models import (
    DriftIssue,
    EngineeringIssue,
    IssueCategory,
    ProjectHealth,
    Recommendation,
    Severity,
)

__all__ = [
    "EngineeringIntel",
    "EngineeringIssue",
    "Recommendation",
    "ProjectHealth",
    "DriftIssue",
    "IssueCategory",
    "Severity",
]


class EngineeringIntel:
    """High-level API for continuous code intelligence.

    Wraps the analysis engine and exposes async-compatible methods
    for file scanning, project scanning, file watching, recommendations,
    health checks, and drift detection.
    """

    def __init__(self) -> None:
        from jarvis.eng_intel.engine import EngineeringIntelEngine
        self._engine = EngineeringIntelEngine()
        self._watched_files: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def scan_file(self, file_path: str) -> List[EngineeringIssue]:
        """Analyze a single Python file and return discovered issues."""
        return self._engine.scan_file(file_path)

    async def scan_project(self, project_path: str) -> List[EngineeringIssue]:
        """Scan every Python file under *project_path* for issues."""
        return self._engine.scan_project(project_path)

    async def watch_file(self, file_path: str) -> None:
        """Register a file for change watching.

        Records the file's mtime so subsequent calls to
        :meth:`_check_watched` can detect modifications.
        """
        try:
            stat = os.stat(file_path)
            self._watched_files[file_path] = stat.st_mtime
        except OSError:
            pass

    async def get_recommendations(self, project_path: str) -> List[Recommendation]:
        """Scan the project and return prioritized improvement recommendations."""
        issues = await self.scan_project(project_path)
        return self._engine.build_recommendations(issues)

    async def get_health(self, project_path: str) -> ProjectHealth:
        """Return an aggregated health summary for the project."""
        issues = await self.scan_project(project_path)
        return self._engine.get_health(issues)

    async def detect_drift(self, project_path: str) -> List[DriftIssue]:
        """Scan the project and return architectural drift issues."""
        issues = await self.scan_project(project_path)
        return self._engine.detect_drift(issues)

    # ------------------------------------------------------------------
    # File watching helpers
    # ------------------------------------------------------------------

    async def check_watched(self) -> List[str]:
        """Return a list of watched files that have changed since last check."""
        changed: List[str] = []
        for fpath, prev_mtime in list(self._watched_files.items()):
            try:
                curr_mtime = os.stat(fpath).st_mtime
                if curr_mtime > prev_mtime:
                    self._watched_files[fpath] = curr_mtime
                    changed.append(fpath)
            except OSError:
                pass
        return changed
