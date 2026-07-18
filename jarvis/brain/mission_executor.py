"""MissionExecutor — Wires the DAGPlanner to the JARVIS agent hierarchy.

Takes a DAG mission and executes it by delegating ready tasks to Kings,
marking them complete as they finish, and emitting mission.* events at each stage.
"""

import time
import uuid
from loguru import logger

from .dag_planner import dag_planner, DAGNode, DAGNodeStatus
from ..core.events import event_bus, Event
from ..core.models import Task, AgentState


class MissionExecutor:
    """Executes DAG missions through the JARVIS agent hierarchy."""

    def __init__(self):
        self._jarvis = None

    def set_jarvis(self, jarvis):
        """Inject the JarvisAgent instance for king delegation."""
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

    async def execute_mission(self, mission_id: str) -> dict:
        """Execute a DAG mission through the agent hierarchy.

        Loops: get ready tasks → delegate to kings → complete → check for new ready tasks.
        Returns the mission status when complete or failed.
        """
        jarvis = self._get_jarvis()

        await event_bus.emit(Event(
            type="mission.started",
            data={"mission_id": mission_id},
            source="J",
        ))

        while True:
            status = dag_planner.get_mission_status(mission_id)
            if status.get("is_complete"):
                break
            if status.get("has_failures"):
                break

            ready = dag_planner.get_ready_tasks(mission_id)
            if not ready:
                if status.get("running", 0) == 0:
                    break
                await event_bus.emit(Event(
                    type="mission.progress",
                    data={
                        "mission_id": mission_id,
                        "progress": status["progress"],
                        "running": status["running"],
                    },
                    source="J",
                ))
                break

            tasks_to_run = []
            for node in ready:
                dag_planner.start_task(mission_id, node.id)
                tasks_to_run.append(node)

            for node in tasks_to_run:
                result_text = await self._delegate_to_king(node, mission_id)

                completed_node = dag_planner.complete_task(mission_id, node.id, result_text)
                if completed_node:
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
        await event_bus.emit(Event(
            type=event_type,
            data={**final},
            source="J",
        ))
        return final

    async def _delegate_to_king(self, node: DAGNode, mission_id: str) -> str:
        """Delegate a single DAG node to the appropriate King agent."""
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

    def create_and_execute(self, description: str, tasks: list[dict]) -> dict:
        """Create a DAG mission from a list of task dicts and execute it.

        Each task dict should have:
            - name: str
            - description: str
            - assigned_to: str (king card_id)
            - priority: int (optional, default 5)
            - dependencies: list[str] (optional, IDs of tasks this depends on)

        Returns {"ok": True, "mission_id": ..., "create_result": ...} on success.
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

        return {"ok": True, "mission_id": mission_id, "create_result": create_result}

    def get_status(self, mission_id: str) -> dict:
        """Return current mission progress from the DAG planner."""
        return dag_planner.get_mission_status(mission_id)


# Module-level singleton
mission_executor = MissionExecutor()
