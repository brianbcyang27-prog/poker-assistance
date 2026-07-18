"""Data models for the Architecture Graph engine."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GraphNode:
    """A node in the architecture graph."""

    id: str
    label: str
    type: str  # module/class/function/route/table/config/agent/worker/king/tool/memory
    layer: str = "infrastructure"  # presentation/business/data/infrastructure
    metadata: Dict[str, Any] = field(default_factory=dict)
    size: int = 0  # lines of code
    health_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "layer": self.layer,
            "metadata": self.metadata,
            "size": self.size,
            "health_score": self.health_score,
        }


@dataclass
class GraphEdge:
    """An edge in the architecture graph."""

    source: str
    target: str
    type: str  # imports/calls/depends/extends/implements/uses/api/database/event
    weight: float = 1.0
    bidirectional: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "weight": self.weight,
            "bidirectional": self.bidirectional,
        }


@dataclass
class GraphMetrics:
    """Metrics computed from the architecture graph."""

    node_count: int = 0
    edge_count: int = 0
    density: float = 0.0
    avg_degree: float = 0.0
    max_degree: int = 0
    centrality: Dict[str, float] = field(default_factory=dict)
    clusters: List[List[str]] = field(default_factory=list)
    layers: Dict[str, List[str]] = field(default_factory=dict)
    critical_path: List[str] = field(default_factory=list)
    cyclomatic_complexity: int = 0
    coupling_score: float = 0.0
    cohesion_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "density": self.density,
            "avg_degree": self.avg_degree,
            "max_degree": self.max_degree,
            "centrality": self.centrality,
            "clusters": self.clusters,
            "layers": self.layers,
            "critical_path": self.critical_path,
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "coupling_score": self.coupling_score,
            "cohesion_score": self.cohesion_score,
        }


@dataclass
class SubGraph:
    """A subgraph extracted from the main graph."""

    nodes: List[str] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    label: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": self.nodes,
            "edges": [e.to_dict() for e in self.edges],
            "label": self.label,
            "description": self.description,
        }
