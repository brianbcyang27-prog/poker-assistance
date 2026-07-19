"""Second Brain — semantic search over the knowledge graph.

Provides keyword, graph-traversal, and hybrid search modes with
scoring based on relevance, recency, importance, and relationship distance.

Usage:
    graph = KnowledgeGraph()
    brain = SecondBrainSearch(graph)
    results = await brain.search(SearchQuery(text="machine learning"))
    context = await brain.get_context("project_jarvis", depth=2)
"""

from .models import (
    SearchMode,
    SearchQuery,
    SearchResult,
    SearchStats,
)

__all__ = [
    "SearchMode",
    "SearchQuery",
    "SearchResult",
    "SearchStats",
]
