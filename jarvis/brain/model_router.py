"""Model Router — Intelligent task-to-model routing for JARVIS.

Routes tasks to the best model based on task type, latency, cost,
and historical success rates. Integrates with the Capability Registry.
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger


class TaskType(str, Enum):
    """Classification of task types for routing."""
    CODING = "coding"
    REASONING = "reasoning"
    WRITING = "writing"
    ANALYSIS = "analysis"
    SEARCH = "search"
    CASUAL = "casual"
    TOOL_USE = "tool_use"
    PLANNING = "planning"
    CREATIVE = "creative"


@dataclass
class ModelProfile:
    """Profile for an available model."""
    model_id: str
    display_name: str
    api_base: str
    api_key: str = ""
    cost_per_1k_tokens: float = 0.0  # $ per 1k tokens
    max_tokens: int = 4096
    supports_tools: bool = False
    supports_streaming: bool = False
    context_window: int = 8192

    # Performance tracking (EWMA)
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    total_calls: int = 0
    total_failures: int = 0
    _ewma_latency: float = 0.0

    # Task affinity (higher = better for this task type)
    task_affinity: dict = field(default_factory=lambda: {
        TaskType.CODING: 0.5,
        TaskType.REASONING: 0.5,
        TaskType.WRITING: 0.5,
        TaskType.ANALYSIS: 0.5,
        TaskType.SEARCH: 0.5,
        TaskType.CASUAL: 0.5,
        TaskType.TOOL_USE: 0.5,
        TaskType.PLANNING: 0.5,
        TaskType.CREATIVE: 0.5,
    })

    def record_call(self, latency_ms: float, success: bool):
        """Record a call and update EWMA metrics."""
        self.total_calls += 1
        if not success:
            self.total_failures += 1
        # EWMA with alpha=0.3
        alpha = 0.3
        if self._ewma_latency == 0:
            self._ewma_latency = latency_ms
        else:
            self._ewma_latency = alpha * latency_ms + (1 - alpha) * self._ewma_latency
        self.avg_latency_ms = self._ewma_latency
        self.success_rate = (self.total_calls - self.total_failures) / self.total_calls

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "display_name": self.display_name,
            "cost_per_1k_tokens": self.cost_per_1k_tokens,
            "max_tokens": self.max_tokens,
            "supports_tools": self.supports_tools,
            "context_window": self.context_window,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "success_rate": round(self.success_rate, 3),
            "total_calls": self.total_calls,
            "task_affinity": {k.value: v for k, v in self.task_affinity.items()},
        }


class ModelRouter:
    """Routes tasks to optimal models based on type, cost, and performance."""

    def __init__(self):
        self._models: dict[str, ModelProfile] = {}
        self._routing_history: list[dict] = []
        self._max_history = 200

    def register(self, profile: ModelProfile):
        """Register a model."""
        self._models[profile.model_id] = profile
        logger.info(f"Model registered: {profile.display_name}")

    def get(self, model_id: str) -> Optional[ModelProfile]:
        return self._models.get(model_id)

    def list_models(self) -> list[ModelProfile]:
        return list(self._models.values())

    def classify_task(self, task_description: str) -> TaskType:
        """Classify a task description into a TaskType using heuristics."""
        lower = task_description.lower()

        # Code-related keywords
        code_kw = ["code", "function", "class", "bug", "debug", "refactor",
                    "implement", "script", "python", "javascript", "typescript",
                    "api", "endpoint", "sql", "database", "test", "compile",
                    "error", "traceback", "import", "variable", "loop"]
        # Reasoning keywords
        reason_kw = ["why", "how does", "explain", "analyze", "reason",
                     "compare", "evaluate", "trade-off", " pros", "cons",
                     "architecture", "design decision"]
        # Writing keywords
        write_kw = ["write", "draft", "compose", "email", "letter", "essay",
                    "summarize", "rewrite", "edit", "proofread", "blog"]
        # Planning keywords
        plan_kw = ["plan", "roadmap", "phase", "milestone", "schedule",
                   "next steps", "prioritize", "strategy", "timeline"]
        # Tool/execution keywords
        tool_kw = ["open", "run", "execute", "launch", "start", "stop",
                   "install", "search", "navigate", "click", "type", "scroll",
                   "screenshot", "screen", "browser", "terminal"]

        scores = {
            TaskType.CODING: sum(1 for kw in code_kw if kw in lower),
            TaskType.REASONING: sum(1 for kw in reason_kw if kw in lower),
            TaskType.WRITING: sum(1 for kw in write_kw if kw in lower),
            TaskType.PLANNING: sum(1 for kw in plan_kw if kw in lower),
            TaskType.TOOL_USE: sum(1 for kw in tool_kw if kw in lower),
            TaskType.CASUAL: 1 if any(w in lower for w in ["hello", "hi", "thanks", "ok"]) else 0,
        }

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return TaskType.ANALYSIS  # default
        return best

    def route(
        self,
        task_type: Optional[TaskType] = None,
        task_description: str = "",
        prefer_low_cost: bool = False,
        require_tools: bool = False,
    ) -> Optional[ModelProfile]:
        """Find the best model for a task.

        Scoring: task_affinity * 40% + success_rate * 30% + (1/latency) * 15% + (1/cost) * 15%
        """
        if task_type is None and task_description:
            task_type = self.classify_task(task_description)

        candidates = list(self._models.values())
        if not candidates:
            return None

        # Filter
        if require_tools:
            candidates = [m for m in candidates if m.supports_tools] or candidates

        scored = []
        for m in candidates:
            affinity = m.task_affinity.get(task_type, 0.5) if task_type else 0.5
            latency_score = 1.0 / (1.0 + m.avg_latency_ms / 1000) if m.avg_latency_ms > 0 else 0.8
            cost_score = 1.0 / (1.0 + m.cost_per_1k_tokens) if m.cost_per_1k_tokens > 0 else 0.8
            if prefer_low_cost:
                cost_score *= 1.5

            score = (
                affinity * 0.40
                + m.success_rate * 0.30
                + latency_score * 0.15
                + cost_score * 0.15
            )
            scored.append((m, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        best_model, best_score = scored[0]

        self._routing_history.append({
            "model": best_model.model_id,
            "task_type": task_type.value if task_type else "unknown",
            "score": round(best_score, 3),
            "timestamp": time.time(),
        })
        if len(self._routing_history) > self._max_history:
            self._routing_history = self._routing_history[-self._max_history:]

        logger.info(f"Routed to {best_model.display_name} (score={best_score:.3f}, type={task_type})")
        return best_model

    def record_outcome(self, model_id: str, latency_ms: float, success: bool):
        """Record a routing outcome for learning."""
        if model_id in self._models:
            self._models[model_id].record_call(latency_ms, success)

    def get_routing_stats(self) -> dict:
        """Get routing statistics."""
        return {
            "total_routings": len(self._routing_history),
            "models": {m.model_id: m.to_dict() for m in self._models.values()},
            "recent_routes": self._routing_history[-10:],
            "routing_distribution": self._get_distribution(),
        }

    def _get_distribution(self) -> dict:
        dist = {}
        for r in self._routing_history:
            t = r.get("task_type", "unknown")
            dist[t] = dist.get(t, 0) + 1
        return dist


# Module-level singleton
router = ModelRouter()


def _register_defaults():
    """Register default models from config."""
    from ..core.config import get_config
    config = get_config()

    if config.nvidia_api_key:
        router.register(ModelProfile(
            model_id="llama-3.1-8b",
            display_name="Llama 3.1 8B (NVIDIA)",
            api_base=config.nvidia_api_base,
            api_key=config.nvidia_api_key,
            cost_per_1k_tokens=0.0,  # Free tier
            max_tokens=4096,
            context_window=8192,
            task_affinity={
                TaskType.CODING: 0.6,
                TaskType.REASONING: 0.5,
                TaskType.WRITING: 0.7,
                TaskType.ANALYSIS: 0.5,
                TaskType.SEARCH: 0.4,
                TaskType.CASUAL: 0.8,
                TaskType.TOOL_USE: 0.5,
                TaskType.PLANNING: 0.4,
                TaskType.CREATIVE: 0.6,
            },
        ))

    # Ollama fallback
    router.register(ModelProfile(
        model_id="ollama-llama3.2",
        display_name="Llama 3.2 (Ollama Local)",
        api_base="http://localhost:11434/v1",
        cost_per_1k_tokens=0.0,
        max_tokens=4096,
        context_window=8192,
        task_affinity={
            TaskType.CODING: 0.5,
            TaskType.REASONING: 0.4,
            TaskType.WRITING: 0.6,
            TaskType.ANALYSIS: 0.4,
            TaskType.SEARCH: 0.3,
            TaskType.CASUAL: 0.7,
            TaskType.TOOL_USE: 0.4,
            TaskType.PLANNING: 0.3,
            TaskType.CREATIVE: 0.5,
        },
    ))


# Auto-register on import
_register_defaults()
