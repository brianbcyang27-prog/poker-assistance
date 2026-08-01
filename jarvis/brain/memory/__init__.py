"""JARVIS Memory System — Human-like layered memory architecture.

Layers:
  Working    — Real-time context (7 slots, like RAM)
  Episodic   — Autobiographical events
  Personal   — User preferences, rules, goals
  Journal    — Daily narrative summaries
  Archive    — Historical, rarely accessed

Supporting:
  Importance  — Signal-based scoring
  Consolidation — Background compression ("sleep")
  Retrieval   — Multi-source context assembly
"""

from .consolidation import MemoryConsolidator, get_consolidator
from .episodic import EpisodicMemoryManager, get_episodic_memory
from .extractor import KnowledgeExtractor, knowledge_extractor
from .graph import Edge, KnowledgeGraph, Node, graph
from .importance import ImportanceScorer, importance_scorer
from .journal import DailyJournal, get_journal
from .note import NoteManager, notes
from .personal import PersonalMemoryManager, get_personal_memory
from .retrieval import MemoryRetrievalEngine, get_retrieval_engine
from .working import WorkingMemoryManager, get_working_memory

__all__ = [
    "MemoryConsolidator",
    "get_consolidator",
    "EpisodicMemoryManager",
    "get_episodic_memory",
    "KnowledgeExtractor",
    "knowledge_extractor",
    "Edge",
    "KnowledgeGraph",
    "Node",
    "graph",
    "ImportanceScorer",
    "importance_scorer",
    "DailyJournal",
    "get_journal",
    "NoteManager",
    "notes",
    "PersonalMemoryManager",
    "get_personal_memory",
    "MemoryRetrievalEngine",
    "get_retrieval_engine",
    "WorkingMemoryManager",
    "get_working_memory",
]
