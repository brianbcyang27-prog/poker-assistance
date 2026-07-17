"""Agent Communication Interface (ACI) — Structured inter-agent messaging.

Provides typed messages, priority queues, message history, and
broadcast capabilities for agent-to-agent communication.
"""

import time
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable
from loguru import logger


class MessageType(str, Enum):
    """Typed messages for structured communication."""
    TASK_ASSIGN = "task_assign"
    TASK_RESULT = "task_result"
    TASK_UPDATE = "task_update"
    QUERY = "query"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    HEARTBEAT = "heartbeat"
    STATUS = "status"
    ALERT = "alert"
    DELEGATION = "delegation"


class MessagePriority(int, Enum):
    """Message priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class ACIMessage:
    """Structured message for inter-agent communication."""
    id: str
    msg_type: MessageType
    sender: str
    receiver: str  # card_id or "*" for broadcast
    payload: dict = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    reply_to: Optional[str] = None  # ID of message being replied to
    ttl: float = 300.0  # Time to live in seconds
    delivered: bool = False
    read: bool = False

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > self.ttl

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.msg_type.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "payload": self.payload,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "reply_to": self.reply_to,
            "delivered": self.delivered,
            "read": self.read,
        }


class MessageQueue:
    """Priority message queue for a single agent."""

    def __init__(self, agent_id: str, max_size: int = 100):
        self.agent_id = agent_id
        self._queue: list[ACIMessage] = []
        self._max_size = max_size

    async def enqueue(self, msg: ACIMessage) -> bool:
        """Add a message to the queue. Returns False if queue is full."""
        if len(self._queue) >= self._max_size:
            logger.warning(f"Queue full for {self.agent_id}, dropping message")
            return False
        self._queue.append(msg)
        self._queue.sort(key=lambda m: m.priority.value, reverse=True)
        return True

    async def dequeue(self) -> Optional[ACIMessage]:
        """Get the highest-priority non-expired message."""
        while self._queue:
            msg = self._queue[0]
            if msg.is_expired:
                self._queue.pop(0)
                continue
            return self._queue.pop(0)
        return None

    def peek(self) -> list[ACIMessage]:
        """Preview queued messages without removing."""
        return [m for m in self._queue if not m.is_expired]

    def size(self) -> int:
        return len([m for m in self._queue if not m.is_expired])


class ACI:
    """Agent Communication Interface — central message bus."""

    _msg_counter = 0

    def __init__(self):
        self._queues: dict[str, MessageQueue] = {}
        self._history: list[ACIMessage] = []
        self._max_history = 500
        self._handlers: dict[str, list[Callable]] = {}  # msg_type -> handlers
        self._subscribers: dict[str, list[Callable]] = {}  # agent_id -> handlers

    def _next_id(self) -> str:
        ACI._msg_counter += 1
        return f"msg_{ACI._msg_counter}_{int(time.time())}"

    def _get_queue(self, agent_id: str) -> MessageQueue:
        if agent_id not in self._queues:
            self._queues[agent_id] = MessageQueue(agent_id)
        return self._queues[agent_id]

    async def send(
        self,
        sender: str,
        receiver: str,
        msg_type: MessageType,
        payload: dict = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        reply_to: Optional[str] = None,
        ttl: float = 300.0,
    ) -> ACIMessage:
        """Send a message from one agent to another."""
        msg = ACIMessage(
            id=self._next_id(),
            msg_type=msg_type,
            sender=sender,
            receiver=receiver,
            payload=payload or {},
            priority=priority,
            reply_to=reply_to,
            ttl=ttl,
        )

        if receiver == "*":
            # Broadcast to all queues
            for agent_id in self._queues:
                if agent_id != sender:
                    await self._queues[agent_id].enqueue(msg)
            msg.delivered = True
        else:
            queue = self._get_queue(receiver)
            msg.delivered = await queue.enqueue(msg)

        # Record in history
        self._history.append(msg)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Notify type handlers
        for handler in self._handlers.get(msg_type.value, []):
            try:
                await handler(msg)
            except Exception as e:
                logger.error(f"Handler error: {e}")

        # Notify agent subscribers
        for handler in self._subscribers.get(receiver, []):
            try:
                await handler(msg)
            except Exception as e:
                logger.error(f"Subscriber error: {e}")

        logger.debug(f"ACI: {sender} → {receiver} [{msg_type.value}] priority={priority.value}")
        return msg

    async def receive(self, agent_id: str) -> Optional[ACIMessage]:
        """Receive the next message for an agent."""
        queue = self._get_queue(agent_id)
        msg = await queue.dequeue()
        if msg:
            msg.read = True
        return msg

    async def receive_all(self, agent_id: str) -> list[ACIMessage]:
        """Receive all pending messages for an agent."""
        queue = self._get_queue(agent_id)
        messages = []
        while True:
            msg = await queue.dequeue()
            if not msg:
                break
            msg.read = True
            messages.append(msg)
        return messages

    def peek(self, agent_id: str) -> list[ACIMessage]:
        """Preview pending messages without consuming."""
        return self._get_queue(agent_id).peek()

    async def broadcast(
        self,
        sender: str,
        payload: dict = None,
        msg_type: MessageType = MessageType.BROADCAST,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> ACIMessage:
        """Broadcast a message to all agents."""
        return await self.send(
            sender=sender,
            receiver="*",
            msg_type=msg_type,
            payload=payload or {},
            priority=priority,
        )

    def get_history(
        self,
        sender: Optional[str] = None,
        receiver: Optional[str] = None,
        msg_type: Optional[MessageType] = None,
        limit: int = 50,
    ) -> list[ACIMessage]:
        """Get message history with optional filters."""
        msgs = self._history
        if sender:
            msgs = [m for m in msgs if m.sender == sender]
        if receiver:
            msgs = [m for m in msgs if m.receiver == receiver]
        if msg_type:
            msgs = [m for m in msgs if m.msg_type == msg_type]
        return msgs[-limit:]

    def subscribe(self, agent_id: str, handler: Callable[[ACIMessage], Awaitable]):
        """Subscribe to messages for an agent."""
        if agent_id not in self._subscribers:
            self._subscribers[agent_id] = []
        self._subscribers[agent_id].append(handler)

    def on_type(self, msg_type: MessageType, handler: Callable[[ACIMessage], Awaitable]):
        """Subscribe to all messages of a type."""
        if msg_type.value not in self._handlers:
            self._handlers[msg_type.value] = []
        self._handlers[msg_type.value].append(handler)

    def get_stats(self) -> dict:
        queue_sizes = {aid: q.size() for aid, q in self._queues.items()}
        return {
            "total_messages": len(self._history),
            "queues": queue_sizes,
            "total_subscribers": sum(len(h) for h in self._subscribers.values()),
            "type_handlers": {k: len(v) for k, v in self._handlers.items()},
        }


# Module-level singleton
aci = ACI()
