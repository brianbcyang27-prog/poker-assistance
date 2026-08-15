"""V10 Tool System — Base abstractions (PHASE B).

Defines the execution-oriented tool contract for JARVIS V10:

- ``ToolSpec``: declarative metadata for a tool (name, description, parameters,
  permission LEVEL 0-3, Trinity capability, risk category, examples).
- ``ParamSpec``: a single parameter definition (LLM-friendly, JSON-Schema subset).
- ``ToolError``: typed error raised by tools, with a stable error code so the
  executor (PHASE E) and UI can react programmatically.
- ``Tool``: abstract base class every executable tool implements. Tools are
  async, take a ``dict`` of parameters, and return a ``ToolResult``.

Result contract (CRITICAL): the result type is the existing v6.3.0
``ToolResult`` from :mod:`jarvis.tools.result`. It is imported and re-exported
here — there is exactly ONE canonical result type in the codebase. New tools
must NOT define their own result classes; they must return ``ToolResult`` so
the Review Engine and existing callers keep working unchanged.

Permission vocabulary: ``permission_level`` uses the V10 LEVEL 0-3 scale
(0 = SAFE, 1 = LOW_RISK, 2 = CONFIRMATION, 3 = HIGH_RISK). The PHASE D
PermissionManager maps these onto the existing Trinity capabilities and the
computer risk classifier — this module only declares intent, it never enforces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# Re-export the canonical v6.3.0 result contract. Field-compatible by construction.
from .result import ToolResult, timed  # noqa: F401  (re-exported for tool authors)

__all__ = [
    "ParamSpec",
    "ToolSpec",
    "ToolError",
    "ToolResult",
    "Tool",
    "timed",
]


@dataclass(frozen=True)
class ParamSpec:
    """Definition of a single tool parameter (JSON-Schema subset).

    Intended to be rendered into LLM tool-call prompts / API schemas.
    """

    name: str
    type: str = "string"  # string | integer | number | boolean | array | object
    description: str = ""
    required: bool = False
    default: Any = None
    enum: tuple[str, ...] = ()
    items: str = ""  # element type when type == "array"

    def to_dict(self) -> dict:
        d: dict = {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
        }
        if self.default is not None:
            d["default"] = self.default
        if self.enum:
            d["enum"] = list(self.enum)
        if self.items:
            d["items"] = self.items
        return d


@dataclass(frozen=True)
class ToolSpec:
    """Declarative metadata for an executable V10 tool.

    ``permission_level`` is the V10 LEVEL this tool requires (0-3). It is
    declarative only — enforcement happens in the PermissionManager (PHASE D).
    """

    name: str
    description: str
    parameters: tuple[ParamSpec, ...] = ()
    permission_level: int = 0  # 0 SAFE | 1 LOW_RISK | 2 CONFIRMATION | 3 HIGH_RISK
    capability: str = ""  # Trinity capability name (jarvis/core/permissions.py)
    risk_level: str = "safe"  # computer RiskLevel: safe/low/medium/high/dangerous
    category: str = "general"
    examples: tuple[str, ...] = ()
    version: str = "1.0.0"

    @property
    def required_params(self) -> list[str]:
        return [p.name for p in self.parameters if p.required]

    def param(self, name: str) -> ParamSpec | None:
        for p in self.parameters:
            if p.name == name:
                return p
        return None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [p.to_dict() for p in self.parameters],
            "permission_level": self.permission_level,
            "capability": self.capability,
            "risk_level": self.risk_level,
            "category": self.category,
            "examples": list(self.examples),
            "version": self.version,
        }


class ToolError(Exception):
    """Typed error raised by a tool or detected by the executor.

    ``code`` is a stable machine-readable identifier; ``tool`` names the
    failing tool; ``recoverable`` hints whether a retry or user action can fix
    the failure. The executor converts any uncaught exception into a failed
    ``ToolResult`` — tools may raise ``ToolError`` for precise control.
    """

    # Stable error codes
    INVALID_PARAMS = "invalid_params"
    PERMISSION_DENIED = "permission_denied"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    EXECUTION_ERROR = "execution_error"
    NOT_FOUND = "not_found"
    UNAVAILABLE = "unavailable"

    def __init__(
        self,
        message: str,
        *,
        code: str = EXECUTION_ERROR,
        tool: str = "",
        recoverable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.tool = tool
        self.recoverable = recoverable

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": str(self),
            "tool": self.tool,
            "recoverable": self.recoverable,
        }


class Tool(ABC):
    """Abstract base class for every executable V10 tool.

    Implementations are stateless by convention: all per-call state flows
    through the ``params`` dict and is returned inside the ``ToolResult``.
    This keeps the registry/executor able to run tools concurrently without
    shared-mutable-state hazards.
    """

    #: Static, immutable spec for this tool.
    spec: ToolSpec = field(init=False)  # type: ignore[assignment]

    @property
    def name(self) -> str:
        return self.spec.name

    async def validate(self, params: dict[str, Any]) -> None:
        """Validate parameters against the spec; raise ``ToolError`` on failure.

        Default implementation checks required params and type tags. Tools
        with stricter needs should override and call ``super().validate``.
        """
        missing = [p.name for p in self.spec.parameters if p.required and p.name not in params]
        if missing:
            raise ToolError(
                f"Missing required parameters: {', '.join(missing)}",
                code=ToolError.INVALID_PARAMS,
                tool=self.name,
            )
        for p in self.spec.parameters:
            if p.name not in params:
                continue
            value = params[p.name]
            if p.type == "string" and not isinstance(value, str):
                raise ToolError(
                    f"Parameter '{p.name}' must be a string, got {type(value).__name__}",
                    code=ToolError.INVALID_PARAMS,
                    tool=self.name,
                )
            if p.type in ("integer", "number") and not isinstance(value, (int, float)):
                raise ToolError(
                    f"Parameter '{p.name}' must be numeric, got {type(value).__name__}",
                    code=ToolError.INVALID_PARAMS,
                    tool=self.name,
                )
            if p.type == "boolean" and not isinstance(value, bool):
                raise ToolError(
                    f"Parameter '{p.name}' must be a boolean, got {type(value).__name__}",
                    code=ToolError.INVALID_PARAMS,
                    tool=self.name,
                )
            if p.enum and value not in p.enum:
                raise ToolError(
                    f"Parameter '{p.name}' must be one of: {', '.join(p.enum)}",
                    code=ToolError.INVALID_PARAMS,
                    tool=self.name,
                )

    @abstractmethod
    async def run(self, params: dict[str, Any]) -> ToolResult:
        """Execute the tool with validated ``params`` and return a ``ToolResult``.

        Implementations should prefer returning ``ToolResult(ok=False, error=...)``
        over raising for expected failures, and raise ``ToolError`` only for
        conditions the executor should treat specially (cancellation, timeout,
        permission). Unexpected exceptions are caught by the executor.
        """
        raise NotImplementedError

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Validate + run in one step. This is the method the executor calls."""
        try:
            await self.validate(params)
        except ToolError as e:
            return ToolResult(
                ok=False,
                error=str(e),
                tool=self.name,
                errors=[e.to_dict()],
            )
        return await self.run(params)
