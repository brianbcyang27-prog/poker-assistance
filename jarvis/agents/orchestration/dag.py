"""DAG Workflow Engine — Define and execute task dependencies."""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, List, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

log = logging.getLogger("jarvis.dag")


class NodeStatus(str, Enum):
    """Status of a DAG node."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DAGNode:
    """A node in the DAG workflow."""
    id: str
    name: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    worker: Optional[str] = None  # Card ID of assigned worker
    status: str = NodeStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "action": self.action,
            "params": self.params,
            "worker": self.worker,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
        }


@dataclass
class DAGEdge:
    """An edge in the DAG workflow (dependency)."""
    from_node: str  # Source node ID
    to_node: str    # Target node ID
    condition: Optional[str] = None  # Optional condition for edge

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_node,
            "to": self.to_node,
            "condition": self.condition,
        }


class DAGWorkflow:
    """Directed Acyclic Graph workflow engine.

    Supports:
        - Parallel execution of independent nodes
        - Sequential execution of dependent nodes
        - Conditional edges
        - Error handling and retry
        - Workflow visualization
    """

    def __init__(self, workflow_id: str = "", name: str = ""):
        self.id = workflow_id or f"dag_{int(time.time() * 1000)}"
        self.name = name
        self._nodes: Dict[str, DAGNode] = {}
        self._edges: List[DAGEdge] = []
        self._handlers: Dict[str, Callable] = {}
        self._created_at = datetime.now()
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        self._status = "created"

    def add_node(
        self,
        node_id: str,
        name: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        worker: Optional[str] = None,
        timeout: int = 300,
    ) -> DAGNode:
        """Add a node to the workflow."""
        node = DAGNode(
            id=node_id,
            name=name,
            action=action,
            params=params or {},
            worker=worker,
            timeout_seconds=timeout,
        )
        self._nodes[node_id] = node
        return node

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        condition: Optional[str] = None,
    ) -> DAGEdge:
        """Add a dependency edge (from_node must complete before to_node)."""
        if from_node not in self._nodes:
            raise ValueError(f"Source node not found: {from_node}")
        if to_node not in self._nodes:
            raise ValueError(f"Target node not found: {to_node}")

        # Check for cycles
        if self._would_create_cycle(from_node, to_node):
            raise ValueError(f"Adding edge {from_node}→{to_node} would create a cycle")

        edge = DAGEdge(from_node=from_node, to_node=to_node, condition=condition)
        self._edges.append(edge)
        return edge

    def register_handler(self, action: str, handler: Callable):
        """Register a handler for a node action."""
        self._handlers[action] = handler

    def get_ready_nodes(self) -> List[DAGNode]:
        """Get nodes that are ready to execute (all dependencies met)."""
        ready = []
        for node in self._nodes.values():
            if node.status != NodeStatus.PENDING:
                continue

            # Check all incoming edges
            dependencies_met = True
            for edge in self._edges:
                if edge.to_node == node.id:
                    source = self._nodes.get(edge.from_node)
                    if source and source.status != NodeStatus.COMPLETED:
                        dependencies_met = False
                        break

            if dependencies_met:
                ready.append(node)

        return ready

    def get_predecessors(self, node_id: str) -> List[str]:
        """Get all predecessor node IDs."""
        return [
            edge.from_node for edge in self._edges
            if edge.to_node == node_id
        ]

    def get_successors(self, node_id: str) -> List[str]:
        """Get all successor node IDs."""
        return [
            edge.to_node for edge in self._edges
            if edge.from_node == node_id
        ]

    def get_roots(self) -> List[DAGNode]:
        """Get root nodes (no incoming edges)."""
        nodes_with_incoming = {edge.to_node for edge in self._edges}
        return [
            node for node in self._nodes.values()
            if node.id not in nodes_with_incoming
        ]

    def get_leaves(self) -> List[DAGNode]:
        """Get leaf nodes (no outgoing edges)."""
        nodes_with_outgoing = {edge.from_node for edge in self._edges}
        return [
            node for node in self._nodes.values()
            if node.id not in nodes_with_outgoing
        ]

    async def execute(self) -> Dict[str, Any]:
        """Execute the entire workflow.

        Returns:
            Workflow execution summary
        """
        self._status = "running"
        self._started_at = datetime.now()

        try:
            # Execute in topological order with parallelism
            while True:
                ready = self.get_ready_nodes()
                if not ready:
                    break

                # Check if any nodes are still running
                running = [
                    n for n in self._nodes.values()
                    if n.status == NodeStatus.RUNNING
                ]
                if running:
                    await asyncio.sleep(0.1)
                    continue

                # Execute ready nodes in parallel
                coros = [self._execute_node(node) for node in ready]
                await asyncio.gather(*coros, return_exceptions=True)

            # Check final status
            failed = [n for n in self._nodes.values() if n.status == NodeStatus.FAILED]
            if failed:
                self._status = "failed"
            else:
                self._status = "completed"

        except Exception as e:
            self._status = "failed"
            log.error(f"Workflow {self.id} failed: {e}")

        finally:
            self._completed_at = datetime.now()

        return self.get_summary()

    async def _execute_node(self, node: DAGNode):
        """Execute a single node."""
        node.status = NodeStatus.RUNNING
        node.started_at = datetime.now()

        handler = self._handlers.get(node.action)
        if not handler:
            node.status = NodeStatus.FAILED
            node.error = f"No handler for action: {node.action}"
            return

        try:
            result = await asyncio.wait_for(
                handler(**node.params),
                timeout=node.timeout_seconds,
            )
            node.result = result
            node.status = NodeStatus.COMPLETED

        except asyncio.TimeoutError:
            node.status = NodeStatus.FAILED
            node.error = f"Node timed out after {node.timeout_seconds}s"

        except Exception as e:
            node.status = NodeStatus.FAILED
            node.error = str(e)

            # Retry logic
            if node.retry_count < node.max_retries:
                node.retry_count += 1
                node.status = NodeStatus.PENDING
                node.error = None

        finally:
            node.completed_at = datetime.now()
            if node.started_at:
                node.duration_ms = (node.completed_at - node.started_at).total_seconds() * 1000

    def _would_create_cycle(self, from_node: str, to_node: str) -> bool:
        """Check if adding an edge would create a cycle.

        When adding edge A→B, a cycle exists if B can reach A
        through existing edges (forward traversal from B).
        """
        # Forward traversal from to_node
        visited = set()
        queue = [to_node]

        while queue:
            current = queue.pop(0)
            if current == from_node:
                return True
            if current in visited:
                continue
            visited.add(current)

            # Get successors (nodes that current points to)
            for successor in self.get_successors(current):
                queue.append(successor)

        return False

    def get_summary(self) -> Dict[str, Any]:
        """Get workflow execution summary."""
        nodes = list(self._nodes.values())
        duration = 0.0
        if self._started_at and self._completed_at:
            duration = (self._completed_at - self._started_at).total_seconds() * 1000

        return {
            "id": self.id,
            "name": self.name,
            "status": self._status,
            "total_nodes": len(nodes),
            "completed": len([n for n in nodes if n.status == NodeStatus.COMPLETED]),
            "failed": len([n for n in nodes if n.status == NodeStatus.FAILED]),
            "pending": len([n for n in nodes if n.status == NodeStatus.PENDING]),
            "total_edges": len(self._edges),
            "duration_ms": round(duration, 2),
            "created_at": self._created_at.isoformat(),
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "completed_at": self._completed_at.isoformat() if self._completed_at else None,
        }

    def visualize(self) -> str:
        """Generate a text visualization of the workflow."""
        lines = [f"Workflow: {self.name} ({self.id})"]
        lines.append(f"Status: {self._status}")
        lines.append(f"Nodes: {len(self._nodes)}, Edges: {len(self._edges)}")
        lines.append("")

        # Topological sort for display
        visited = set()
        order = []

        def dfs(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)
            for successor in self.get_successors(node_id):
                dfs(successor)
            order.append(node_id)

        for root in self.get_roots():
            dfs(root.id)

        for node_id in order:
            node = self._nodes[node_id]
            status_icon = {
                NodeStatus.PENDING: "○",
                NodeStatus.RUNNING: "●",
                NodeStatus.COMPLETED: "✓",
                NodeStatus.FAILED: "✗",
                NodeStatus.SKIPPED: "–",
            }.get(node.status, "?")

            predecessors = self.get_predecessors(node_id)
            pred_str = f" ← {', '.join(predecessors)}" if predecessors else ""

            lines.append(f"  {status_icon} {node.name} ({node.action}){pred_str}")

        return "\n".join(lines)
