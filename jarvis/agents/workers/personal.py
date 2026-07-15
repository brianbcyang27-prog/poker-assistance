"""Personal Workers - ♥ Suit."""

from .base import BaseWorker
from ...core.models import Suit, Rank


class CalendarWorker(BaseWorker):
    """♥ Queen - Calendar Manager."""
    
    def __init__(self):
        super().__init__(suit=Suit.HEARTS, rank=Rank.QUEEN)
    
    @property
    def name(self) -> str:
        return "Calendar"
    
    @property
    def title(self) -> str:
        return "Calendar Manager"
    
    def get_system_prompt(self) -> str:
        return """You are the Calendar Manager (♥Q).
Specialize in: scheduling, meetings, time management, reminders.
Focus on: efficiency, conflict resolution, prioritization.
Help manage time effectively."""


class EmailWorker(BaseWorker):
    """♥ Jack - Email Manager."""
    
    def __init__(self):
        super().__init__(suit=Suit.HEARTS, rank=Rank.JACK)
    
    @property
    def name(self) -> str:
        return "Email"
    
    @property
    def title(self) -> str:
        return "Email Manager"
    
    def get_system_prompt(self) -> str:
        return """You are the Email Manager (♥J).
Specialize in: email drafting, filtering, prioritization, responses.
Focus on: clarity, professionalism, conciseness.
Manage email communication effectively."""


class TasksWorker(BaseWorker):
    """♥ 10 - Task Manager."""
    
    def __init__(self):
        super().__init__(suit=Suit.HEARTS, rank=Rank.TEN)
    
    @property
    def name(self) -> str:
        return "Tasks"
    
    @property
    def title(self) -> str:
        return "Task Manager"
    
    def get_system_prompt(self) -> str:
        return """You are the Task Manager (♥10).
Specialize in: task organization, prioritization, deadlines, tracking.
Focus on: productivity, clear action items, progress tracking.
Help stay organized and productive."""


class SchedulingWorker(BaseWorker):
    """♥ 9 - Scheduling Assistant."""
    
    def __init__(self):
        super().__init__(suit=Suit.HEARTS, rank=Rank.NINE)
    
    @property
    def name(self) -> str:
        return "Scheduling"
    
    @property
    def title(self) -> str:
        return "Scheduling Assistant"
    
    def get_system_prompt(self) -> str:
        return """You are the Scheduling Assistant (♥9).
Specialize in: appointment scheduling, meeting coordination, time zones.
Focus on: convenience, accuracy, conflict avoidance.
Make scheduling effortless."""
