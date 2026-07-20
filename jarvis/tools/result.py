"""Structured result from every tool execution (v6.3.0).

Every tool returns a ToolResult with consistent metadata.
The Review Engine consumes this automatically.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolResult:
    """Structured result from tool execution with verification metadata."""

    ok: bool
    data: Any = None
    error: Optional[str] = None
    tool: str = ""
    duration_ms: float = 0.0
    confidence: float = 1.0
    warnings: List[str] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    recovery: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "data": self.data,
            "error": self.error,
            "tool": self.tool,
            "duration_ms": self.duration_ms,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "artifacts": self.artifacts,
            "screenshots": self.screenshots,
            "logs": self.logs,
            "errors": self.errors,
            "recovery": self.recovery,
        }

    def __repr__(self) -> str:
        status = "OK" if self.ok else "FAIL"
        return f"ToolResult({status}, {self.tool}, {self.duration_ms:.0f}ms)"


def timed(func):
    """Decorator that wraps a tool method to return ToolResult with timing."""
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.monotonic()
        try:
            result = await func(*args, **kwargs)
            elapsed = (time.monotonic() - start) * 1000
            if isinstance(result, ToolResult):
                result.duration_ms = elapsed
                return result
            return ToolResult(ok=True, data=result, tool=func.__name__, duration_ms=elapsed)
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return ToolResult(
                ok=False,
                error=str(e),
                tool=func.__name__,
                duration_ms=elapsed,
                recovery=f"Check logs for {func.__name__} error details",
            )

    return wrapper
