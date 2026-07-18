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
from .graph import graph, KnowledgeGraph, Node, Edge
from .note import notes, NoteManager
from .extractor import knowledge_extractor, KnowledgeExtractor
from .working import get_working_memory, WorkingMemoryManager
from .episodic import get_episodic_memory, EpisodicMemoryManager
from .personal import get_personal_memory, PersonalMemoryManager
from .importance import importance_scorer, ImportanceScorer
from .consolidation import get_consolidator, MemoryConsolidator
from .retrieval import get_retrieval_engine, MemoryRetrievalEngine
from .journal import get_journal, DailyJournal
