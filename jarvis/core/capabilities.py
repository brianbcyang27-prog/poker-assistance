"""Capability Registry — Centralized registry of all tools, workers, and capabilities.

Kings use this to select the right worker/tool for a task.
Every capability exposes: name, owner, type, description, latency, cost,
success_rate, required_permissions.

Usage:
    from jarvis.core.capabilities import registry

    # Register a capability
    await registry.register(Capability(
        name="browser_navigate",
        owner="♣K",
        type="tool",
        description="Navigate to a URL",
    ))

    # Query capabilities
    tools = await registry.query(type="tool", owner="♣K")
    best = await registry.find_best(type="tool", description="open a website")
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

log = logging.getLogger("jarvis.capabilities")


class CapType(str, Enum):
    TOOL = "tool"
    WORKER = "worker"
    ACTION = "action"
    SKILL = "skill"
    MEMORY = "memory"


@dataclass
class Capability:
    """A registered capability with full metadata for intelligent selection."""

    name: str
    owner: str
    type: CapType
    description: str = ""
    version: str = "1.0.0"
    latency_ms: float = 0.0
    cost: float = 0.0
    success_rate: float = 1.0
    total_calls: int = 0
    total_failures: int = 0
    required_permissions: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    enabled: bool = True
    registered_at: float = field(default_factory=time.time)
    last_used: float = 0.0

    # v6.1.0: Enhanced metadata for intelligent tool selection
    failure_modes: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    compatible_workers: list[str] = field(default_factory=list)
    preferred_models: list[str] = field(default_factory=list)
    required_context: list[str] = field(default_factory=list)
    max_concurrent: int = 1
    timeout_seconds: float = 30.0
    retry_count: int = 3
    category: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "owner": self.owner,
            "type": self.type.value,
            "description": self.description,
            "version": self.version,
            "latency_ms": self.latency_ms,
            "cost": self.cost,
            "success_rate": self.success_rate,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "required_permissions": self.required_permissions,
            "tags": self.tags,
            "enabled": self.enabled,
            "registered_at": self.registered_at,
            "last_used": self.last_used,
            "failure_modes": self.failure_modes,
            "examples": self.examples,
            "compatible_workers": self.compatible_workers,
            "preferred_models": self.preferred_models,
            "required_context": self.required_context,
            "max_concurrent": self.max_concurrent,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Capability":
        d = dict(d)
        d["type"] = CapType(d.get("type", "tool"))
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class CapabilityRegistry:
    """Centralized registry of all capabilities.

    Stored in-memory with optional DB persistence.
    Supports querying by type, owner, tags, and description matching.
    """

    def __init__(self):
        self._caps: dict[str, Capability] = {}

    async def register(self, cap: Capability) -> dict:
        """Register a capability."""
        self._caps[cap.name] = cap
        log.debug(f"Registered capability: {cap.name} ({cap.type.value}) by {cap.owner}")
        return {"ok": True, "name": cap.name}

    async def unregister(self, name: str) -> dict:
        """Remove a capability."""
        if name in self._caps:
            del self._caps[name]
            return {"ok": True}
        return {"ok": False, "error": f"Capability '{name}' not found"}

    async def get(self, name: str) -> Optional[Capability]:
        """Get a capability by name."""
        return self._caps.get(name)

    async def query(
        self,
        type: Optional[CapType] = None,
        owner: Optional[str] = None,
        tags: Optional[list[str]] = None,
        enabled_only: bool = True,
    ) -> list[Capability]:
        """Query capabilities by filters."""
        result = list(self._caps.values())
        if type:
            result = [c for c in result if c.type == type]
        if owner:
            result = [c for c in result if c.owner == owner]
        if tags:
            result = [c for c in result if any(t in c.tags for t in tags)]
        if enabled_only:
            result = [c for c in result if c.enabled]
        return result

    async def find_best(
        self,
        type: Optional[CapType] = None,
        owner: Optional[str] = None,
        description: str = "",
    ) -> Optional[Capability]:
        """Find the best capability matching criteria.

        Selection considers: success_rate (high), latency (low), cost (low).
        Description matching is keyword-based (no embeddings).
        """
        candidates = await self.query(type=type, owner=owner)
        if not candidates:
            return None

        # Score each candidate
        scored = []
        for cap in candidates:
            score = cap.success_rate * 0.5  # 50% weight on success
            if cap.latency_ms > 0:
                score += max(0, 1.0 - cap.latency_ms / 5000) * 0.25  # 25% latency
            if cap.cost > 0:
                score += max(0, 1.0 - cap.cost) * 0.25  # 25% cost
            else:
                score += 0.25  # Free = max cost score

            # Bonus for description match
            if description:
                desc_lower = description.lower()
                cap_words = set(cap.description.lower().split())
                query_words = set(desc_lower.split())
                overlap = len(cap_words & query_words)
                score += min(overlap * 0.1, 0.3)

            scored.append((score, cap))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    async def record_call(self, name: str, success: bool, latency_ms: float = 0) -> None:
        """Record a capability usage for tracking."""
        cap = self._caps.get(name)
        if not cap:
            return
        cap.total_calls += 1
        cap.last_used = time.time()
        cap.latency_ms = (cap.latency_ms * 0.9) + (latency_ms * 0.1)  # EWMA
        if not success:
            cap.total_failures += 1
        if cap.total_calls > 0:
            cap.success_rate = 1.0 - (cap.total_failures / cap.total_calls)

    async def get_all(self) -> list[dict]:
        """Get all capabilities as dicts."""
        return [c.to_dict() for c in self._caps.values()]

    async def get_stats(self) -> dict:
        """Get registry statistics."""
        caps = list(self._caps.values())
        by_type = {}
        for c in caps:
            by_type.setdefault(c.type.value, 0)
            by_type[c.type.value] += 1
        by_owner = {}
        for c in caps:
            by_owner.setdefault(c.owner, 0)
            by_owner[c.owner] += 1
        return {
            "total": len(caps),
            "by_type": by_type,
            "by_owner": by_owner,
            "avg_success_rate": (
                sum(c.success_rate for c in caps) / len(caps) if caps else 0
            ),
        }

    async def generate_capability_prompt(self) -> str:
        """Generate a system prompt section describing available capabilities.
        
        This is injected into chat requests so the LLM knows what tools it has.
        """
        caps = [c for c in self._caps.values() if c.enabled]
        if not caps:
            return ""
        
        # Group by category
        categories = {}
        for cap in caps:
            cat = cap.category or cap.type.value
            categories.setdefault(cat, []).append(cap)
        
        lines = [
            "## Available Capabilities",
            "You are JARVIS, an AI assistant with the following capabilities:",
            ""
        ]
        
        category_labels = {
            "computer": "Computer Control",
            "browser": "Browser Control", 
            "memory": "Memory System",
            "engineering": "Engineering Tools",
            "tool": "General Tools",
            "worker": "Agent Workers",
            "action": "System Actions",
            "skill": "Learned Skills",
        }
        
        for cat, cat_caps in categories.items():
            label = category_labels.get(cat, cat.title())
            lines.append(f"### {label}")
            for cap in cat_caps:
                lines.append(f"- **{cap.name}**: {cap.description}")
            lines.append("")
        
        lines.append("Use these capabilities to help the user. Always check what tools are available before saying you cannot do something.")
        
        return "\n".join(lines)


# Module-level singleton
registry = CapabilityRegistry()
