"""Base agent classes for the JARVIS card hierarchy."""

from abc import ABC, abstractmethod
from typing import Optional, Any
from datetime import datetime
import asyncio

from ..core.models import (
    AgentRole, AgentState, AgentMessage, Task, Suit, Rank
)
from ..core.config import get_config


class BaseAgent(ABC):
    """Base class for all JARVIS agents."""
    
    def __init__(self):
        self.state = AgentState.IDLE
        self._config = get_config()
        self._message_history: list[AgentMessage] = []
        self._bg_tasks: set = set()
    
    @property
    @abstractmethod
    def card_id(self) -> str:
        """Unique card identifier (e.g., '♠K', '♥Q', '♣10')."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""
        pass
    
    @property
    @abstractmethod
    def role(self) -> AgentRole:
        """Agent role in hierarchy."""
        pass
    
    @property
    @abstractmethod
    def title(self) -> str:
        """Official title/description."""
        pass
    
    @property
    def suit(self) -> Optional[Suit]:
        """Card suit (None for JARVIS)."""
        return None
    
    @property
    def rank(self) -> Optional[Rank]:
        """Card rank (None for JARVIS)."""
        return None
    
    @property
    def personality(self) -> str:
        """Internal personality that influences decisions."""
        return "Professional and efficient"
    
    def set_state(self, state: AgentState):
        """Update agent state and persist to database."""
        self.state = state
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                task = asyncio.ensure_future(self._persist_state(state))
                self._bg_tasks.add(task)
                task.add_done_callback(self._bg_tasks.discard)
            else:
                loop.run_until_complete(self._persist_state(state))
        except RuntimeError:
            pass
    
    async def _persist_state(self, state: AgentState):
        """Persist agent state to database."""
        try:
            from ..core.database import get_db
            db = await get_db()
            await db.save_agent_state(self.card_id, state.value)
        except Exception:
            pass
    
    def receive_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Receive a message from another agent."""
        self._message_history.append(message)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                task = asyncio.ensure_future(self._persist_message(message))
                self._bg_tasks.add(task)
                task.add_done_callback(self._bg_tasks.discard)
            else:
                loop.run_until_complete(self._persist_message(message))
        except RuntimeError:
            pass
        return self.process_message(message)
    
    async def _persist_message(self, message: AgentMessage):
        """Persist agent message to database."""
        try:
            from ..core.database import get_db
            db = await get_db()
            await db.save_agent_message(message.to_dict())
        except Exception:
            pass  # Don't fail on persistence errors
    
    @abstractmethod
    def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process an incoming message and optionally respond."""
        pass
    
    @abstractmethod
    async def execute_task(self, task: Task) -> AgentMessage:
        """Execute an assigned task and return result."""
        pass
    
    def to_dict(self) -> dict:
        """Serialize agent to dictionary."""
        return {
            "card_id": self.card_id,
            "name": self.name,
            "role": self.role.value,
            "title": self.title,
            "suit": self.suit.value if self.suit else None,
            "rank": self.rank.value if self.rank else None,
            "state": self.state.value,
            "personality": self.personality,
        }


class CardAgent(BaseAgent):
    """Base class for agents represented by playing cards."""
    
    def __init__(self, suit: Suit, rank: Rank):
        super().__init__()
        self._suit = suit
        self._rank = rank
    
    @property
    def suit(self) -> Optional[Suit]:
        return self._suit
    
    @property
    def rank(self) -> Optional[Rank]:
        return self._rank
    
    @property
    def card_id(self) -> str:
        return f"{self._suit.symbol}{self._rank.symbol}"
    
    @property
    def is_king(self) -> bool:
        return self._rank == Rank.KING
    
    @property
    def is_face_card(self) -> bool:
        return self._rank in (Rank.KING, Rank.QUEEN, Rank.JACK)
