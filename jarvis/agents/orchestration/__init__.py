"""Agent Orchestration — King→Worker delegation, parallel execution, DAG workflows.

The orchestration layer enables:
  1. Kings delegate tasks to Workers
  2. Workers execute in parallel
  3. DAG workflows define task dependencies
  4. The pool manages worker lifecycle
"""

from .orchestration import TaskOrchestrator, DelegatedTask
from .pool import WorkerPool, WorkerSlot
from .dag import DAGWorkflow, DAGNode, DAGEdge

__all__ = [
    "TaskOrchestrator",
    "DelegatedTask",
    "WorkerPool",
    "WorkerSlot",
    "DAGWorkflow",
    "DAGNode",
    "DAGEdge",
]
