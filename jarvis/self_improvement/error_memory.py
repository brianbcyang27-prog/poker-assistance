"""Error memory — persistent error storage and pattern recognition."""
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from .models import ErrorRecord

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = os.path.join(os.path.expanduser("~"), ".jarvis", "memory_store")
ERRORS_FILE = "errors.json"


class ErrorMemory:
    """Persistent error memory backed by JSON storage."""

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self._storage_dir = storage_dir or DEFAULT_STORAGE_DIR
        self._store_path = os.path.join(self._storage_dir, ERRORS_FILE)
        self._errors: Dict[str, ErrorRecord] = {}
        self._loaded = False

    async def load(self) -> None:
        """Load errors from disk."""
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._store_path):
            self._errors = {}
            self._loaded = True
            return
        try:
            with open(self._store_path, "r") as f:
                data = json.load(f)
            self._errors = {
                k: ErrorRecord.from_dict(v) for k, v in data.items()
            }
            self._loaded = True
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load error memory: %s", exc)
            self._errors = {}
        self._loaded = True

    async def save(self) -> None:
        """Persist errors to disk."""
        self._save()

    def _save(self) -> None:
        os.makedirs(self._storage_dir, exist_ok=True)
        data = {k: v.to_dict() for k, v in self._errors.items()}
        try:
            with open(self._store_path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as exc:
            logger.error("Failed to save error memory: %s", exc)

    async def record(
        self,
        error_type: str,
        message: str,
        module: str = "",
        function: str = "",
        severity: str = "medium",
        stack_trace: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> ErrorRecord:
        """Record a new error."""
        record = ErrorRecord(
            error_type=error_type,
            message=message,
            module=module,
            function=function,
            severity=severity,
            stack_trace=stack_trace,
            context=context or {},
        )
        self._errors[record.id] = record
        await self.save()
        logger.info(
            "Error recorded: %s [%s] in %s.%s",
            record.error_type, record.severity, record.module, record.function,
        )
        return record

    async def get(self, error_id: str) -> Optional[ErrorRecord]:
        """Retrieve an error by ID."""
        return self._errors.get(error_id)

    async def search(
        self,
        query: str,
        error_type: str = "",
        module: str = "",
    ) -> List[ErrorRecord]:
        """Search errors by query, type, and/or module."""
        results: List[ErrorRecord] = []
        q_lower = query.lower() if query else ""
        for err in self._errors.values():
            if error_type and err.error_type != error_type:
                continue
            if module and err.module != module:
                continue
            if q_lower:
                searchable = f"{err.message} {err.error_type} {err.module} {err.function} {err.stack_trace}".lower()
                if q_lower not in searchable:
                    continue
            results.append(err)
        results.sort(key=lambda e: e.occurred_at, reverse=True)
        return results

    async def get_recent(self, n: int = 10) -> List[ErrorRecord]:
        """Return the N most recent errors."""
        sorted_e = sorted(
            self._errors.values(),
            key=lambda e: e.occurred_at,
            reverse=True,
        )
        return sorted_e[:n]

    async def resolve(
        self,
        error_id: str,
        solution: str,
        resolution: str,
    ) -> Optional[ErrorRecord]:
        """Mark an error as resolved with its solution."""
        record = self._errors.get(error_id)
        if not record:
            return None
        record.resolved = True
        record.solution = solution
        record.resolution = resolution
        await self.save()
        return record

    async def get_solutions(self, error_type: str) -> List[str]:
        """Return all known solutions for a given error type."""
        solutions: List[str] = []
        for err in self._errors.values():
            if err.error_type == error_type and err.resolved and err.solution:
                if err.solution not in solutions:
                    solutions.append(err.solution)
        return solutions

    async def get_unresolved(self) -> List[ErrorRecord]:
        """Return all unresolved errors."""
        return [e for e in self._errors.values() if not e.resolved]

    async def get_stats(self) -> Dict[str, Any]:
        """Return error statistics."""
        all_errors = list(self._errors.values())
        resolved = [e for e in all_errors if e.resolved]
        unresolved = [e for e in all_errors if not e.resolved]

        type_counts: Dict[str, int] = {}
        severity_counts: Dict[str, int] = {}
        module_counts: Dict[str, int] = {}
        for e in all_errors:
            type_counts[e.error_type] = type_counts.get(e.error_type, 0) + 1
            severity_counts[e.severity] = severity_counts.get(e.severity, 0) + 1
            if e.module:
                module_counts[e.module] = module_counts.get(e.module, 0) + 1

        return {
            "total": len(all_errors),
            "resolved": len(resolved),
            "unresolved": len(unresolved),
            "by_type": type_counts,
            "by_severity": severity_counts,
            "by_module": module_counts,
        }
