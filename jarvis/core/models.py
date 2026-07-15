"""Core data models for JARVIS agents."""

from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid


class Suit(str, Enum):
    """Card suits representing agent divisions."""
    SPADES = "spades"      # Engineering
    HEARTS = "hearts"      # Personal
    DIAMONDS = "diamonds"  # Research
    CLUBS = "clubs"        # System
    
    @property
    def symbol(self) -> str:
        return {"spades": "♠", "hearts": "♥", "diamonds": "♦", "clubs": "♣"}[self.value]
    
    @property
    def color(self) -> str:
        return {"spades": "#00d4ff", "hearts": "#ff4466", "diamonds": "#ffaa00", "clubs": "#00ff88"}[self.value]


class Rank(str, Enum):
    """Card ranks representing agent hierarchy."""
    KING = "king"
    QUEEN = "queen"
    JACK = "jack"
    TEN = "ten"
    NINE = "nine"
    EIGHT = "eight"
    SEVEN = "seven"
    SIX = "six"
    FIVE = "five"
    FOUR = "four"
    THREE = "three"
    TWO = "two"
    
    @property
    def symbol(self) -> str:
        return {
            "king": "K", "queen": "Q", "jack": "J",
            "ten": "10", "nine": "9", "eight": "8",
            "seven": "7", "six": "6", "five": "5",
            "four": "4", "three": "3", "two": "2"
        }[self.value]


class AgentRole(str, Enum):
    """Agent roles in the hierarchy."""
    JARVIS = "jarvis"
    KING = "king"
    WORKER = "worker"


class AgentState(str, Enum):
    """Current state of an agent."""
    IDLE = "idle"
    THINKING = "thinking"
    PLANNING = "planning"
    WORKING = "working"
    REVIEWING = "reviewing"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


class AgentMessage(BaseModel):
    """Structured communication between agents."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender: str
    receiver: str
    task_id: str
    content: str
    status: str = "pending"
    confidence: float = 0.0
    issues: list[str] = Field(default_factory=list)
    result: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "task_id": self.task_id,
            "content": self.content,
            "status": self.status,
            "confidence": self.confidence,
            "issues": self.issues,
            "result": self.result,
            "timestamp": self.timestamp.isoformat(),
        }


class Task(BaseModel):
    """A unit of work assigned to an agent."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: str
    assigned_to: str
    status: AgentState = AgentState.IDLE
    priority: int = 5  # 1-10, 10 being highest
    dependencies: list[str] = Field(default_factory=list)
    result: Optional[str] = None
    confidence: float = 0.0
    issues: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    @property
    def card_id(self) -> str:
        """Get the card notation for the assigned agent."""
        return self.assigned_to


class Workspace(BaseModel):
    """A mission workspace tracking a user request."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str
    owner: str  # Agent card_id (e.g., "♠K")
    tasks: list[Task] = Field(default_factory=list)
    status: AgentState = AgentState.PLANNING
    progress: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def update_progress(self):
        """Calculate progress based on task completion."""
        if not self.tasks:
            self.progress = 0.0
            return
        completed = sum(1 for t in self.tasks if t.status == AgentState.COMPLETED)
        self.progress = (completed / len(self.tasks)) * 100
