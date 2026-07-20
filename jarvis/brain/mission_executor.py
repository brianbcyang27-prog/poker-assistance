"""MissionExecutor — Unified mission execution with workspace tracking (v6.1.0).

Wires the DAGPlanner to the agent hierarchy AND creates persistent workspaces.
Every mission now auto-creates a workspace with file structure.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from loguru import logger

from .dag_planner import dag_planner, DAGNode, DAGNodeStatus
from ..core.events import event_bus, Event
from ..core.models import Task, AgentState


class MissionExecutor:
    """Executes missions through the JARVIS agent hierarchy with workspace tracking."""

    def __init__(self):
        self._jarvis = None
        self._workspace_root = Path(__file__).parent.parent.parent / "workspaces"
        self._bg_tasks = set()

    def set_jarvis(self, jarvis):
        self._jarvis = jarvis

    def _get_jarvis(self):
        if self._jarvis is not None:
            return self._jarvis
        try:
            from ..web.main import jarvis as web_jarvis
            if web_jarvis:
                self._jarvis = web_jarvis
                return self._jarvis
        except Exception:
            pass
        return None

    async def execute_mission(self, mission_id: str, workspace_id: str = None) -> dict:
        """Execute a DAG mission with workspace tracking."""
        jarvis = self._get_jarvis()

        await event_bus.emit(Event(
            type="mission.started",
            data={"mission_id": mission_id, "workspace_id": workspace_id},
            source="J",
        ))

        # Record stage in workspace
        if workspace_id:
            await self._record_workspace_stage(workspace_id, "execute", "start")
            await self._add_timeline(workspace_id, "mission.started", "J", f"Mission {mission_id} started")

        while True:
            status = dag_planner.get_mission_status(mission_id)
            if status.get("is_complete") or status.get("has_failures"):
                break

            ready = dag_planner.get_ready_tasks(mission_id)
            if not ready:
                if status.get("running", 0) == 0:
                    break
                await event_bus.emit(Event(
                    type="mission.progress",
                    data={"mission_id": mission_id, "progress": status["progress"], "running": status["running"]},
                    source="J",
                ))
                break

            for node in ready:
                dag_planner.start_task(mission_id, node.id)

            for node in ready:
                # Gather peer context from completed tasks
                peer_context = await self._gather_peer_context(mission_id, node.id)

                result_text = await self._delegate_to_king(node, mission_id, peer_context)

                completed_node = dag_planner.complete_task(mission_id, node.id, result_text)
                if completed_node:
                    # Record in workspace
                    if workspace_id:
                        await self._record_task_result(workspace_id, node, result_text)
                        await self._add_timeline(
                            workspace_id, "task.completed", node.assigned_to,
                            f"Completed: {node.name}", task_id=node.id, confidence=0.8,
                        )

                    await event_bus.emit(Event(
                        type="mission.task_completed",
                        data={
                            "mission_id": mission_id,
                            "task_id": node.id,
                            "task_name": node.name,
                            "assigned_to": node.assigned_to,
                            "result": result_text[:200],
                        },
                        source="J",
                    ))

            updated_status = dag_planner.get_mission_status(mission_id)
            await event_bus.emit(Event(
                type="mission.progress",
                data={
                    "mission_id": mission_id,
                    "progress": updated_status["progress"],
                    "completed": updated_status["completed"],
                    "total": updated_status["total"],
                },
                source="J",
            ))

        final = dag_planner.get_mission_status(mission_id)
        event_type = "mission.completed" if final.get("is_complete") else "mission.failed"

        # Complete workspace
        if workspace_id:
            await self._record_workspace_stage(workspace_id, "execute", "complete")
            await self._add_timeline(
                workspace_id, event_type, "J",
                f"Mission {'completed' if final.get('is_complete') else 'failed'}",
            )

            try:
                from ..web.main import workspace_manager
                if final.get("is_complete"):
                    await workspace_manager.complete_workspace(workspace_id)
                else:
                    await workspace_manager.add_error(workspace_id, "Mission failed")
            except Exception as e:
                logger.warning(f"Failed to complete workspace: {e}")

        await event_bus.emit(Event(
            type=event_type,
            data={**final},
            source="J",
        ))
        return final

    async def _gather_peer_context(self, mission_id: str, current_node_id: str) -> str:
        """Gather results from completed predecessors for peer context."""
        mission = dag_planner.get_mission(mission_id)
        if not mission:
            return ""

        current_node = dag_planner._get_node(mission_id, current_node_id)
        if not current_node or not current_node.dependencies:
            return ""

        context_parts = []
        for dep_id in current_node.dependencies:
            dep_node = dag_planner._get_node(mission_id, dep_id)
            if dep_node and dep_node.status == DAGNodeStatus.COMPLETED and dep_node.result:
                context_parts.append(f"Worker {dep_node.assigned_to} ({dep_node.name}): {dep_node.result[:300]}")

        return "\n".join(context_parts) if context_parts else ""

    async def _delegate_to_king(self, node: DAGNode, mission_id: str, peer_context: str = "") -> str:
        """Delegate a single DAG node to the appropriate King."""
        jarvis = self._get_jarvis()
        if not jarvis:
            return "JARVIS agent not available"

        king_card = node.assigned_to or "♠K"
        king = jarvis.get_king(king_card)

        if king is None:
            return f"No King registered for {king_card}"

        task = Task(
            name=node.name,
            description=node.description,
            assigned_to=king_card,
            priority=node.priority,
        )

        try:
            agent_msg = await king.execute_task(task)
            return agent_msg.content
        except Exception as e:
            logger.error(f"King {king_card} failed task {node.id}: {e}")
            dag_planner.fail_task(mission_id, node.id, str(e))
            return f"Error: {e}"

    def create_and_execute(self, description: str, tasks: list[dict], user_request: str = "") -> dict:
        """Create a DAG mission with workspace and execute it.

        Returns {"ok": True, "mission_id": ..., "workspace_id": ...} on success.
        """
        mission_id = f"mission_{uuid.uuid4().hex[:8]}"

        nodes = []
        for i, task_dict in enumerate(tasks):
            task_id = task_dict.get("id", f"task_{i}")
            nodes.append(DAGNode(
                id=task_id,
                name=task_dict.get("name", f"Task {i + 1}"),
                description=task_dict.get("description", description),
                assigned_to=task_dict.get("assigned_to", "♠K"),
                priority=task_dict.get("priority", 5),
                dependencies=task_dict.get("dependencies", []),
            ))

        create_result = dag_planner.create_mission(mission_id, nodes)
        if not create_result.get("ok"):
            return {"ok": False, "error": create_result.get("error", "Failed to create mission")}

        # Create workspace synchronously (returns workspace_id for the async executor)
        workspace_id = f"ws_{uuid.uuid4().hex[:8]}"

        return {
            "ok": True,
            "mission_id": mission_id,
            "workspace_id": workspace_id,
            "create_result": create_result,
        }

    async def create_workspace_and_execute(
        self,
        goal: str,
        user_request: str,
        owner: str = "J",
        tasks: list[dict] = None,
    ) -> dict:
        """Create a workspace with file structure and execute the mission."""
        try:
            from ..web.main import workspace_manager
        except ImportError:
            workspace_manager = None

        workspace_id = None
        if workspace_manager:
            ws = await workspace_manager.create_workspace(
                goal=goal, owner=owner, user_request=user_request,
            )
            workspace_id = ws.id

            # Generate workspace file structure
            self._generate_workspace_files(workspace_id, goal, user_request)

        mission_id = f"mission_{uuid.uuid4().hex[:8]}"

        if tasks:
            nodes = []
            for i, t in enumerate(tasks):
                nodes.append(DAGNode(
                    id=t.get("id", f"task_{i}"),
                    name=t.get("name", f"Task {i + 1}"),
                    description=t.get("description", goal),
                    assigned_to=t.get("assigned_to", "♠K"),
                    priority=t.get("priority", 5),
                    dependencies=t.get("dependencies", []),
                ))
            dag_planner.create_mission(mission_id, nodes)

        # Execute asynchronously (track to prevent silent loss)
        task = asyncio.create_task(self.execute_mission(mission_id, workspace_id))
        self._bg_tasks.add(task)
        task.add_done_callback(lambda t: self._bg_tasks.discard(t))

        return {
            "ok": True,
            "mission_id": mission_id,
            "workspace_id": workspace_id,
        }

    def _generate_workspace_files(self, workspace_id: str, goal: str, user_request: str):
        """Auto-generate workspace directory with documentation files."""
        ws_dir = self._workspace_root / workspace_id
        ws_dir.mkdir(parents=True, exist_ok=True)
        (ws_dir / "deliverables").mkdir(exist_ok=True)
        (ws_dir / "logs").mkdir(exist_ok=True)
        (ws_dir / "generated").mkdir(exist_ok=True)
        (ws_dir / "artifacts").mkdir(exist_ok=True)
        (ws_dir / "tests").mkdir(exist_ok=True)

        files = {
            "README.md": f"# Workspace: {goal}\n\n> Created: {datetime.now().isoformat()}\n> ID: {workspace_id}\n\n## Goal\n\n{goal}\n\n## User Request\n\n{user_request}\n",
            "mission.md": f"# Mission Plan\n\n## Goal\n{goal}\n\n## Status\n- [ ] Research\n- [ ] Planning\n- [ ] Execution\n- [ ] Verification\n- [ ] Review\n",
            "research.md": "# Research Findings\n\n*No research findings yet.*\n",
            "architecture.md": "# Architecture Plan\n\n*No architecture plan yet.*\n",
            "todo.md": "# TODO\n\n- [ ] Define tasks\n- [ ] Assign workers\n- [ ] Execute\n- [ ] Verify\n- [ ] Review\n",
            "timeline.md": "# Mission Timeline\n\n*No events yet.*\n",
            "review.md": "# Review\n\n*No review yet.*\n",
            "notes.md": "# Notes\n\n*No notes yet.*\n",
        }

        for filename, content in files.items():
            (ws_dir / filename).write_text(content)

    async def _record_workspace_stage(self, workspace_id: str, stage: str, action: str):
        try:
            from ..web.main import workspace_manager
            await workspace_manager.record_stage(workspace_id, stage, action)
        except Exception as e:
            logger.warning(f"Failed to record workspace stage: {e}")

    async def _record_task_result(self, workspace_id: str, node: DAGNode, result: str):
        try:
            from ..web.main import workspace_manager
            ws = await workspace_manager.get_workspace(workspace_id)
            if ws:
                ws.execution_results.append({
                    "task_id": node.id,
                    "task_name": node.name,
                    "assigned_to": node.assigned_to,
                    "result": result[:1000],
                    "completed_at": datetime.now().isoformat(),
                })
                from ..core.database import get_db
                db = await get_db()
                await db.save_workspace(ws.model_dump())
        except Exception as e:
            logger.warning(f"Failed to record task result: {e}")

    async def _add_timeline(self, workspace_id: str, event_type: str, source: str, description: str, **extra):
        try:
            from ..web.main import workspace_manager
            await workspace_manager.add_timeline_event(workspace_id, event_type, source, description, **extra)
        except Exception as e:
            logger.warning(f"Failed to add timeline event: {e}")

    def get_status(self, mission_id: str) -> dict:
        return dag_planner.get_mission_status(mission_id)


mission_executor = MissionExecutor()
