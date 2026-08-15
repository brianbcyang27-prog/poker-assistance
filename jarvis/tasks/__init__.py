"""JARVIS V10 task layer — task lifecycle, concurrency, global kill switch.

Usage:
    from jarvis.tasks import task_manager

    task = await task_manager.submit(plan, user_request="...")
    task = await task_manager.execute(task.id)
"""

from .task import Task, TaskManager, TaskStatus, task_manager

__all__ = ["Task", "TaskManager", "TaskStatus", "task_manager"]
