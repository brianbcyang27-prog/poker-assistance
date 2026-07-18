"""Monitoring data models — health, metrics, component snapshots."""

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


class ComponentStatus(str, enum.Enum):
    """Per-component health level."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


@dataclass
class MetricSnapshot:
    """A single metric reading from a component."""
    component: str
    metric_name: str
    value: float
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ComponentHealth:
    """Health report for one component."""
    name: str
    status: ComponentStatus = ComponentStatus.HEALTHY
    metrics: Dict[str, Any] = field(default_factory=dict)
    last_check: Optional[datetime] = None
    issues: List[str] = field(default_factory=list)


@dataclass
class HealthStatus:
    """Aggregated health status of the entire system."""
    overall: ComponentStatus = ComponentStatus.HEALTHY
    components: Dict[str, ComponentHealth] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
