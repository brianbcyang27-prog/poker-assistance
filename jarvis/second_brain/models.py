"""Second brain semantic search data models."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class SearchMode(str, Enum):
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    GRAPH = "graph"
    HYBRID = "hybrid"


@dataclass
class SearchResult:
    id: str = ""
    name: str = ""
    entity_type: str = ""
    description: str = ""
    score: float = 0.0
    match_reasons: List[str] = field(default_factory=list)
    related_entities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "description": self.description,
            "score": self.score,
            "match_reasons": self.match_reasons,
            "related_entities": self.related_entities,
            "metadata": self.metadata,
        }


@dataclass
class SearchQuery:
    text: str = ""
    mode: str = "hybrid"
    entity_types: List[str] = field(default_factory=list)
    min_importance: str = ""
    min_confidence: float = 0.0
    limit: int = 20
    include_related: bool = True

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "mode": self.mode,
            "entity_types": self.entity_types,
            "min_importance": self.min_importance,
            "min_confidence": self.min_confidence,
            "limit": self.limit,
            "include_related": self.include_related,
        }


@dataclass
class SearchStats:
    total_searches: int = 0
    avg_results: float = 0.0
    top_queries: List[Dict[str, Any]] = field(default_factory=list)
    search_modes_used: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_searches": self.total_searches,
            "avg_results": self.avg_results,
            "top_queries": self.top_queries,
            "search_modes_used": self.search_modes_used,
        }
