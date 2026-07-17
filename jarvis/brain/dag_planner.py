"""DAG Task Planner — Complex multi-step mission planning with dependencies.

Creates directed acyclic graphs of tasks with dependency resolution,
parallel execution paths, and critical path analysis.
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict, deque
from loguru import logger


class DAGNodeStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DAGNode:
    """A node in the task DAG."""
    id: str
    name: str
    description: str = ""
    assigned_to: str = ""  # card_id of assigned agent
    status: DAGNodeStatus = DAGNodeStatus.PENDING
    result: str = ""
    priority: int = 5
    estimated_duration_ms: float = 0
    actual_duration_ms: float = 0
    dependencies: list[str] = field(default_factory=list)  # IDs of tasks this depends on
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: float = 0
    completed_at: float = 0

    @property
    def is_terminal(self) -> bool:
        return self.status in (DAGNodeStatus.COMPLETED, DAGNodeStatus.FAILED, DAGNodeStatus.SKIPPED)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "status": self.status.value,
            "result": self.result[:200],
            "priority": self.priority,
            "dependencies": self.dependencies,
            "actual_duration_ms": self.actual_duration_ms,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class DAGPlanner:
    """Plans and executes tasks as directed acyclic graphs."""

    def __init__(self):
        self._missions: dict[str, list[DAGNode]] = {}  # mission_id -> nodes
        self._max_missions = 50

    def create_mission(self, mission_id: str, nodes: list[DAGNode]) -> dict:
        """Create a new mission with task nodes."""
        # Validate no cycles
        if self._has_cycle(nodes):
            return {"ok": False, "error": "Cycle detected in task dependencies"}

        # Topological sort to validate
        order = self._topological_sort(nodes)
        if order is None:
            return {"ok": False, "error": "Invalid dependency graph"}

        self._missions[mission_id] = nodes

        # Mark nodes with no dependencies as ready
        for node in nodes:
            if not node.dependencies:
                node.status = DAGNodeStatus.READY

        logger.info(f"DAG mission created: {mission_id} with {len(nodes)} tasks")
        return {
            "ok": True,
            "mission_id": mission_id,
            "node_count": len(nodes),
            "execution_order": order,
            "critical_path": self._critical_path(nodes),
        }

    def get_ready_tasks(self, mission_id: str) -> list[DAGNode]:
        """Get tasks whose dependencies are all completed."""
        nodes = self._missions.get(mission_id, [])
        ready = []
        for node in nodes:
            if node.status != DAGNodeStatus.PENDING:
                continue
            deps_met = all(
                self._get_node(mission_id, dep_id) is not None
                and self._get_node(mission_id, dep_id).status == DAGNodeStatus.COMPLETED
                for dep_id in node.dependencies
            )
            if deps_met:
                node.status = DAGNodeStatus.READY
                ready.append(node)
        return sorted(ready, key=lambda n: -n.priority)

    def start_task(self, mission_id: str, node_id: str) -> Optional[DAGNode]:
        """Mark a task as running."""
        node = self._get_node(mission_id, node_id)
        if node and node.status == DAGNodeStatus.READY:
            node.status = DAGNodeStatus.RUNNING
            node.started_at = time.time()
            return node
        return None

    def complete_task(self, mission_id: str, node_id: str, result: str = "") -> Optional[DAGNode]:
        """Mark a task as completed."""
        node = self._get_node(mission_id, node_id)
        if node and node.status == DAGNodeStatus.RUNNING:
            node.status = DAGNodeStatus.COMPLETED
            node.result = result
            node.completed_at = time.time()
            node.actual_duration_ms = (node.completed_at - node.started_at) * 1000
            return node
        return None

    def fail_task(self, mission_id: str, node_id: str, error: str = "") -> Optional[DAGNode]:
        """Mark a task as failed."""
        node = self._get_node(mission_id, node_id)
        if node:
            node.status = DAGNodeStatus.FAILED
            node.result = error
            node.completed_at = time.time()
            return node
        return None

    def get_mission_status(self, mission_id: str) -> dict:
        """Get overall mission progress."""
        nodes = self._missions.get(mission_id, [])
        if not nodes:
            return {"error": "Mission not found"}

        total = len(nodes)
        completed = sum(1 for n in nodes if n.status == DAGNodeStatus.COMPLETED)
        failed = sum(1 for n in nodes if n.status == DAGNodeStatus.FAILED)
        running = sum(1 for n in nodes if n.status == DAGNodeStatus.RUNNING)
        ready = sum(1 for n in nodes if n.status == DAGNodeStatus.READY)
        pending = sum(1 for n in nodes if n.status == DAGNodeStatus.PENDING)

        progress = completed / total if total > 0 else 0

        return {
            "mission_id": mission_id,
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "ready": ready,
            "pending": pending,
            "progress": round(progress, 3),
            "is_complete": completed == total,
            "has_failures": failed > 0,
        }

    def get_next_actions(self, mission_id: str) -> list[dict]:
        """Get actionable next steps for the mission."""
        ready = self.get_ready_tasks(mission_id)
        return [
            {
                "node_id": n.id,
                "name": n.name,
                "description": n.description,
                "assigned_to": n.assigned_to,
                "priority": n.priority,
            }
            for n in ready
        ]

    def visualize(self, mission_id: str) -> dict:
        """Get graph data for visualization."""
        nodes = self._missions.get(mission_id, [])
        vis_nodes = [
            {"id": n.id, "label": n.name, "status": n.status.value, "assigned_to": n.assigned_to}
            for n in nodes
        ]
        vis_edges = []
        for n in nodes:
            for dep_id in n.dependencies:
                vis_edges.append({"source": dep_id, "target": n.id})
        return {"nodes": vis_nodes, "edges": vis_edges}

    def _get_node(self, mission_id: str, node_id: str) -> Optional[DAGNode]:
        for n in self._missions.get(mission_id, []):
            if n.id == node_id:
                return n
        return None

    def _has_cycle(self, nodes: list[DAGNode]) -> bool:
        """Detect cycles using DFS."""
        node_map = {n.id: n for n in nodes}
        visited = set()
        rec_stack = set()

        def dfs(nid):
            visited.add(nid)
            rec_stack.add(nid)
            node = node_map.get(nid)
            if node:
                for dep in node.dependencies:
                    if dep not in visited:
                        if dfs(dep):
                            return True
                    elif dep in rec_stack:
                        return True
            rec_stack.discard(nid)
            return False

        for n in nodes:
            if n.id not in visited:
                if dfs(n.id):
                    return True
        return False

    def _topological_sort(self, nodes: list[DAGNode]) -> Optional[list[str]]:
        """Topological sort of nodes."""
        node_map = {n.id: n for n in nodes}
        in_degree = defaultdict(int)
        for n in nodes:
            in_degree[n.id] = in_degree.get(n.id, 0)
            for dep in n.dependencies:
                in_degree[n.id] += 1

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        order = []

        while queue:
            nid = queue.popleft()
            order.append(nid)
            node = node_map.get(nid)
            if node:
                for n in nodes:
                    if nid in n.dependencies:
                        in_degree[n.id] -= 1
                        if in_degree[n.id] == 0:
                            queue.append(n.id)

        return order if len(order) == len(nodes) else None

    def _critical_path(self, nodes: list[DAGNode]) -> list[str]:
        """Find the critical path (longest path through the graph)."""
        node_map = {n.id: n for n in nodes}
        order = self._topological_sort(nodes)
        if not order:
            return []

        # Calculate earliest start times
        es = {nid: 0 for nid in order}
        for nid in order:
            node = node_map.get(nid)
            if node:
                for dep in node.dependencies:
                    dep_node = node_map.get(dep)
                    if dep_node:
                        duration = dep_node.estimated_duration_ms / 1000
                        es[nid] = max(es[nid], es.get(dep, 0) + duration)

        # Find the end node (max earliest start)
        if not order:
            return []
        end_node = max(order, key=lambda nid: es.get(nid, 0))

        # Trace back the critical path
        path = [end_node]
        current = end_node
        while True:
            node = node_map.get(current)
            if not node or not node.dependencies:
                break
            # Find dependency with latest finish time
            best_dep = None
            best_finish = -1
            for dep in node.dependencies:
                dep_node = node_map.get(dep)
                if dep_node:
                    finish = es.get(dep, 0) + dep_node.estimated_duration_ms / 1000
                    if finish > best_finish:
                        best_finish = finish
                        best_dep = dep
            if best_dep:
                path.append(best_dep)
                current = best_dep
            else:
                break

        return list(reversed(path))

    def get_all_missions(self) -> list[dict]:
        return [
            {"mission_id": mid, **self.get_mission_status(mid)}
            for mid in self._missions
        ]

    def get_stats(self) -> dict:
        total_missions = len(self._missions)
        total_nodes = sum(len(nodes) for nodes in self._missions.values())
        return {
            "total_missions": total_missions,
            "total_nodes": total_nodes,
        }


# Module-level singleton
dag_planner = DAGPlanner()
