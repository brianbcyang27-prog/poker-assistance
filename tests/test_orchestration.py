"""Tests for JARVIS Agent Orchestration (v5.0.0)."""

import pytest
import asyncio
import os
import sys
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.agents.orchestration.orchestration import (
    TaskOrchestrator, DelegatedTask, TaskStatus, TaskPriority
)
from jarvis.agents.orchestration.pool import WorkerPool, WorkerSlot, WorkerState
from jarvis.agents.orchestration.dag import DAGWorkflow, DAGNode, DAGEdge, NodeStatus


# ── Helper Functions ─────────────────────────────────────

async def mock_handler(action: str = "", **kwargs) -> dict:
    """Mock handler for testing."""
    return {"ok": True, "action": action, "result": "success"}


async def mock_failing_handler(action: str = "", **kwargs) -> dict:
    """Mock handler that always fails."""
    raise ValueError("Intentional test failure")


async def mock_slow_handler(action: str = "", delay: float = 0.1, **kwargs) -> dict:
    """Mock handler with configurable delay."""
    await asyncio.sleep(delay)
    return {"ok": True, "action": action}


# ── DelegatedTask Tests ──────────────────────────────────

class TestDelegatedTask:
    def test_creation(self):
        task = DelegatedTask(
            name="Test Task",
            king="♥K",
            worker="♥Q",
            action="test.action",
        )
        assert task.name == "Test Task"
        assert task.king == "♥K"
        assert task.worker == "♥Q"
        assert task.status == TaskStatus.PENDING
        assert task.id.startswith("task_")

    def test_to_dict(self):
        task = DelegatedTask(
            name="Test",
            king="♥K",
            worker="♥Q",
            action="test",
        )
        d = task.to_dict()
        assert d["name"] == "Test"
        assert d["king"] == "♥K"
        assert "id" in d
        assert "created_at" in d

    def test_auto_id(self):
        t1 = DelegatedTask(name="T1")
        t2 = DelegatedTask(name="T2")
        assert t1.id != t2.id


# ── TaskOrchestrator Tests ──────────────────────────────

class TestTaskOrchestrator:
    def setup_method(self):
        self.orch = TaskOrchestrator(max_concurrent=3)

    def test_init(self):
        assert self.orch.max_concurrent == 3
        stats = self.orch.get_stats()
        assert stats["total_delegated"] == 0

    def test_register_handler(self):
        self.orch.register_handler("test.action", mock_handler)
        assert "test.action" in self.orch._handlers

    @pytest.mark.asyncio
    async def test_delegate(self):
        self.orch.register_handler("test.action", mock_handler)
        task = await self.orch.delegate(
            name="Test",
            king="♥K",
            worker="♥Q",
            action="test.action",
        )
        assert task.status == TaskStatus.QUEUED
        assert task.id in self.orch._tasks

    @pytest.mark.asyncio
    async def test_execute_next(self):
        self.orch.register_handler("test.action", mock_handler)
        await self.orch.delegate(
            name="Test",
            king="♥K",
            worker="♥Q",
            action="test.action",
        )
        result = await self.orch.execute_next()
        assert result is not None
        assert result.status == TaskStatus.COMPLETED
        assert result.result["ok"] is True

    @pytest.mark.asyncio
    async def test_execute_parallel(self):
        self.orch.register_handler("test.action", mock_handler)
        tasks = [
            {"name": f"Task {i}", "king": "♥K", "worker": "♥Q", "action": "test.action"}
            for i in range(3)
        ]
        results = await self.orch.execute_parallel(tasks)
        assert len(results) == 3
        assert all(r.status == TaskStatus.COMPLETED for r in results)

    @pytest.mark.asyncio
    async def test_cancel(self):
        self.orch.register_handler("test.action", mock_handler)
        task = await self.orch.delegate(
            name="Test",
            king="♥K",
            worker="♥Q",
            action="test.action",
        )
        ok = await self.orch.cancel(task.id)
        assert ok
        assert task.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_get_tasks_by_status(self):
        self.orch.register_handler("test.action", mock_handler)
        await self.orch.delegate(
            name="Test",
            king="♥K",
            worker="♥Q",
            action="test.action",
        )
        queued = self.orch.get_tasks_by_status(TaskStatus.QUEUED)
        assert len(queued) == 1

    @pytest.mark.asyncio
    async def test_get_tasks_by_king(self):
        self.orch.register_handler("test.action", mock_handler)
        await self.orch.delegate(
            name="Test",
            king="♥K",
            worker="♥Q",
            action="test.action",
        )
        tasks = self.orch.get_tasks_by_king("♥K")
        assert len(tasks) == 1

    @pytest.mark.asyncio
    async def test_get_tasks_by_worker(self):
        self.orch.register_handler("test.action", mock_handler)
        await self.orch.delegate(
            name="Test",
            king="♥K",
            worker="♥Q",
            action="test.action",
        )
        tasks = self.orch.get_tasks_by_worker("♥Q")
        assert len(tasks) == 1

    @pytest.mark.asyncio
    async def test_stats(self):
        self.orch.register_handler("test.action", mock_handler)
        await self.orch.delegate(
            name="Test",
            king="♥K",
            worker="♥Q",
            action="test.action",
        )
        stats = self.orch.get_stats()
        assert stats["total_delegated"] == 1
        assert stats["queue_size"] == 1


# ── WorkerPool Tests ─────────────────────────────────────

class TestWorkerPool:
    def setup_method(self):
        self.pool = WorkerPool()

    def test_register_worker(self):
        worker = self.pool.register_worker(
            card_id="♥Q",
            name="Personal Assistant",
            suit="hearts",
            rank="Q",
            role="Personal",
            capabilities=["chat", "research"],
        )
        assert worker.card_id == "♥Q"
        assert "chat" in worker.capabilities

    def test_unregister_worker(self):
        self.pool.register_worker(
            card_id="♥Q",
            name="PA",
            suit="hearts",
            rank="Q",
            role="Personal",
        )
        ok = self.pool.unregister_worker("♥Q")
        assert ok
        assert self.pool.get_worker("♥Q") is None

    def test_get_idle_workers(self):
        self.pool.register_worker(
            card_id="♥Q",
            name="PA",
            suit="hearts",
            rank="Q",
            role="Personal",
        )
        idle = self.pool.get_idle_workers()
        assert len(idle) == 1

    def test_get_workers_by_capability(self):
        self.pool.register_worker(
            card_id="♥Q",
            name="PA",
            suit="hearts",
            rank="Q",
            role="Personal",
            capabilities=["chat", "research"],
        )
        self.pool.register_worker(
            card_id="♦Q",
            name="Research",
            suit="diamonds",
            rank="Q",
            role="Research",
            capabilities=["research", "analysis"],
        )
        workers = self.pool.get_workers_by_capability("research")
        assert len(workers) == 2

    def test_get_best_worker(self):
        self.pool.register_worker(
            card_id="♥Q",
            name="PA",
            suit="hearts",
            rank="Q",
            role="Personal",
            capabilities=["chat"],
        )
        self.pool.register_worker(
            card_id="♦Q",
            name="Research",
            suit="diamonds",
            rank="Q",
            role="Research",
            capabilities=["research"],
        )
        best = self.pool.get_best_worker("chat")
        assert best is not None
        assert best.card_id == "♥Q"

    def test_get_pool_status(self):
        self.pool.register_worker(
            card_id="♥Q",
            name="PA",
            suit="hearts",
            rank="Q",
            role="Personal",
        )
        status = self.pool.get_pool_status()
        assert status["total_workers"] == 1
        assert status["idle"] == 1

    def test_release_worker(self):
        self.pool.register_worker(
            card_id="♥Q",
            name="PA",
            suit="hearts",
            rank="Q",
            role="Personal",
        )
        worker = self.pool.get_worker("♥Q")
        worker.state = WorkerState.BUSY
        self.pool.release_worker("♥Q")
        assert worker.state == WorkerState.IDLE

    def test_set_worker_offline(self):
        self.pool.register_worker(
            card_id="♥Q",
            name="PA",
            suit="hearts",
            rank="Q",
            role="Personal",
        )
        self.pool.set_worker_offline("♥Q")
        worker = self.pool.get_worker("♥Q")
        assert worker.state == WorkerState.OFFLINE

    def test_stats(self):
        self.pool.register_worker(
            card_id="♥Q",
            name="PA",
            suit="hearts",
            rank="Q",
            role="Personal",
        )
        stats = self.pool.get_stats()
        assert stats["total_workers"] == 1
        assert stats["total_completed"] == 0


# ── DAGWorkflow Tests ────────────────────────────────────

class TestDAGWorkflow:
    def setup_method(self):
        self.dag = DAGWorkflow(name="Test Workflow")

    def test_add_node(self):
        node = self.dag.add_node(
            node_id="n1",
            name="Node 1",
            action="test.action",
        )
        assert node.id == "n1"
        assert "n1" in self.dag._nodes

    def test_add_edge(self):
        self.dag.add_node("n1", "Node 1", "test")
        self.dag.add_node("n2", "Node 2", "test")
        edge = self.dag.add_edge("n1", "n2")
        assert edge.from_node == "n1"
        assert edge.to_node == "n2"

    def test_cycle_detection(self):
        self.dag.add_node("n1", "N1", "test")
        self.dag.add_node("n2", "N2", "test")
        self.dag.add_edge("n1", "n2")
        with pytest.raises(ValueError, match="cycle"):
            self.dag.add_edge("n2", "n1")

    def test_get_ready_nodes(self):
        self.dag.add_node("n1", "N1", "test")
        self.dag.add_node("n2", "N2", "test")
        self.dag.add_edge("n1", "n2")
        ready = self.dag.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].id == "n1"

    def test_get_roots_and_leaves(self):
        self.dag.add_node("n1", "N1", "test")
        self.dag.add_node("n2", "N2", "test")
        self.dag.add_node("n3", "N3", "test")
        self.dag.add_edge("n1", "n2")
        self.dag.add_edge("n2", "n3")
        roots = self.dag.get_roots()
        leaves = self.dag.get_leaves()
        assert len(roots) == 1
        assert roots[0].id == "n1"
        assert len(leaves) == 1
        assert leaves[0].id == "n3"

    def test_get_predecessors_and_successors(self):
        self.dag.add_node("n1", "N1", "test")
        self.dag.add_node("n2", "N2", "test")
        self.dag.add_node("n3", "N3", "test")
        self.dag.add_edge("n1", "n2")
        self.dag.add_edge("n2", "n3")
        preds = self.dag.get_predecessors("n2")
        succs = self.dag.get_successors("n2")
        assert preds == ["n1"]
        assert succs == ["n3"]

    @pytest.mark.asyncio
    async def test_execute_linear(self):
        self.dag.add_node("n1", "Step 1", "test.action")
        self.dag.add_node("n2", "Step 2", "test.action")
        self.dag.add_edge("n1", "n2")
        self.dag.register_handler("test.action", mock_handler)
        summary = await self.dag.execute()
        assert summary["status"] == "completed"
        assert summary["completed"] == 2

    @pytest.mark.asyncio
    async def test_execute_parallel(self):
        self.dag.add_node("n1", "Step 1", "test.action")
        self.dag.add_node("n2", "Step 2", "test.action")
        self.dag.add_node("n3", "Step 3", "test.action")
        self.dag.add_edge("n1", "n3")
        self.dag.add_edge("n2", "n3")
        self.dag.register_handler("test.action", mock_handler)
        summary = await self.dag.execute()
        assert summary["status"] == "completed"
        assert summary["completed"] == 3

    @pytest.mark.asyncio
    async def test_execute_with_failure(self):
        self.dag.add_node("n1", "Step 1", "failing.action")
        self.dag.register_handler("failing.action", mock_failing_handler)
        summary = await self.dag.execute()
        assert summary["status"] == "failed"
        assert summary["failed"] == 1

    def test_visualize(self):
        self.dag.add_node("n1", "Step 1", "test")
        self.dag.add_node("n2", "Step 2", "test")
        self.dag.add_edge("n1", "n2")
        viz = self.dag.visualize()
        assert "Step 1" in viz
        assert "Step 2" in viz

    def test_summary(self):
        self.dag.add_node("n1", "N1", "test")
        summary = self.dag.get_summary()
        assert summary["total_nodes"] == 1
        assert summary["name"] == "Test Workflow"


# ── WorkerSlot Tests ─────────────────────────────────────

class TestWorkerSlot:
    def test_creation(self):
        slot = WorkerSlot(
            card_id="♥Q",
            name="PA",
            suit="hearts",
            rank="Q",
            role="Personal",
        )
        assert slot.card_id == "♥Q"
        assert slot.state == WorkerState.IDLE

    def test_to_dict(self):
        slot = WorkerSlot(
            card_id="♥Q",
            name="PA",
            suit="hearts",
            rank="Q",
            role="Personal",
            capabilities=["chat"],
        )
        d = slot.to_dict()
        assert d["card_id"] == "♥Q"
        assert "chat" in d["capabilities"]
