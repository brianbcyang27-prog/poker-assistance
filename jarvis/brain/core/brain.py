"""JARVISBrain — the main facade for all brain operations."""
import logging
import time
from typing import Any, Dict, List, Optional

from .models import BrainContext, MemoryEntry, ReasoningResult, ActionDecision
from .context import BrainContextManager
from .memory import MemoryManager
from .reasoning import ReasoningEngine
from .decision import BrainDecisionEngine

logger = logging.getLogger(__name__)


class JARVISBrain:
    """Single entry point for all memory, knowledge, reasoning, and decision operations.

    Usage::

        brain = JARVISBrain(config={})
        ctx = await brain.think("build a robot arm")
        decision = await brain.decide("build a robot arm", ctx, options=[...])
        await brain.remember("robot arm uses 6 DOF", memory_type="fact")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._config = config or {}
        self._initialized = False

        self.memory: MemoryManager = MemoryManager()
        self.context: BrainContextManager = BrainContextManager()
        self.reasoning: ReasoningEngine = ReasoningEngine()
        self.decisions: BrainDecisionEngine = BrainDecisionEngine()

        self._started_at = time.time()

    async def initialize(
        self,
        knowledge_graph=None,
        preference_engine=None,
        decision_engine=None,
        timeline_engine=None,
        consolidation_engine=None,
        knowledge_extractor=None,
    ) -> None:
        """Wire up external engines. Call once at startup.

        If not called, the brain operates in standalone mode with local state only.
        """
        self.memory = MemoryManager(
            knowledge_graph=knowledge_graph,
            preference_engine=preference_engine,
            decision_engine=decision_engine,
            timeline_engine=timeline_engine,
            consolidation_engine=consolidation_engine,
            knowledge_extractor=knowledge_extractor,
        )

        self.context = BrainContextManager(
            preference_engine=preference_engine,
            decision_engine=decision_engine,
            timeline_engine=timeline_engine,
            knowledge_graph=knowledge_graph,
        )

        self.reasoning = ReasoningEngine(memory_manager=self.memory)

        self.decisions = BrainDecisionEngine(
            memory_manager=self.memory,
            reasoning_engine=self.reasoning,
            decisions_engine=decision_engine,
        )

        self._initialized = True
        logger.info("JARVISBrain initialized with external engines")

    async def think(
        self,
        goal: str,
        project_name: str = "",
        tools: Optional[List[str]] = None,
    ) -> BrainContext:
        """Build complete context for a goal — call before any agent runs."""
        return await self.context.build_context(goal, project_name, tools)

    async def reason(
        self, goal: str, context: BrainContext
    ) -> ReasoningResult:
        """Perform evidence-based reasoning toward a goal."""
        return await self.reasoning.reason(goal, context)

    async def decide(
        self,
        goal: str,
        context: BrainContext,
        options: Optional[List[Dict[str, Any]]] = None,
    ) -> ActionDecision:
        """Choose the best action from available options."""
        return await self.decisions.decide(goal, context, options)

    async def remember(
        self,
        content: str,
        memory_type: str = "fact",
        importance: str = "useful",
        source: str = "brain",
        related_entities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """Store a memory across all subsystems."""
        return await self.memory.remember(
            content, memory_type, importance, source,
            related_entities, metadata,
        )

    async def recall(
        self,
        query: str,
        limit: int = 10,
        memory_type: str = "",
    ) -> List[MemoryEntry]:
        """Search all memory sources."""
        return await self.memory.recall(query, limit, memory_type)

    async def explain_why(self, decision_id: str) -> str:
        """Explain why a particular decision was made."""
        return await self.decisions.explain(decision_id)

    async def get_stats(self) -> Dict[str, Any]:
        """Return brain statistics and health info."""
        mem_stats = await self.memory.get_stats()
        return {
            "initialized": self._initialized,
            "uptime_seconds": time.time() - self._started_at,
            "memory": mem_stats,
            "reasoning_history": len(self.reasoning.get_reasoning_history()),
            "decision_history": len(self.decisions._action_history),
        }

    async def consolidate(self) -> Dict[str, Any]:
        """Run memory consolidation."""
        return await self.memory.consolidate()

    async def get_status(self) -> Dict[str, Any]:
        """Brain health check — returns operational status."""
        stats = await self.get_stats()
        health = "healthy"
        issues: List[str] = []

        if not self._initialized:
            health = "degraded"
            issues.append("Not initialized with external engines")

        if stats["memory"].get("local_memories", 0) == 0 and stats["memory"].get("kg_stats", {}).get("entities", 0) == 0:
            health = "empty"
            issues.append("No memories stored yet")

        return {
            "health": health,
            "issues": issues,
            "stats": stats,
            "timestamp": time.time(),
        }
