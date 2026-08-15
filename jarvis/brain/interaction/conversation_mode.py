"""Conversation Mode — Tracks stateful conversation context.

Maintains a rolling window of recent intents and determines the
current conversational mode (casual, working, command, project-focused).
"""

from __future__ import annotations

from collections import deque
from enum import StrEnum

from .intent_classifier import IntentCategory


class ConversationMode(StrEnum):
    """High-level conversation mode derived from recent intent history."""

    CASUAL = "casual"  # Chitchat, greetings, social
    WORKING = "working"  # Active task execution
    COMMAND = "command"  # System operation mode
    PROJECT_FOCUSED = "project"  # Engaged in project work
    QUESTIONING = "questioning"  # Asking informational questions
    INITIAL = "initial"  # First interaction (no history)


class ConversationTracker:
    """Tracks recent conversation history and derives current mode.

    Maintains a rolling window of classified intents. Mode transitions
    are driven by patterns in the recent intent sequence.

    Usage:
        tracker = ConversationTracker()
        tracker.record("hello", IntentCategory.CHAT)
        tracker.record("build a website", IntentCategory.TASK)
        assert tracker.current_mode == ConversationMode.WORKING
    """

    def __init__(self, window_size: int = 5):
        self._window_size = window_size
        self._history: deque[tuple[str, IntentCategory]] = deque(maxlen=window_size)
        self._current_mode: ConversationMode = ConversationMode.INITIAL

    @property
    def current_mode(self) -> ConversationMode:
        """Get the current derived conversation mode."""
        return self._current_mode

    def record(self, message: str, intent: IntentCategory) -> None:
        """Record a message and its intent, then update the current mode."""
        self._history.append((message, intent))
        self._derive_mode()

    def _derive_mode(self) -> None:
        """Derive conversation mode from recent intent history."""
        if not self._history:
            self._current_mode = ConversationMode.INITIAL
            return

        recent_intents = [intent for _, intent in self._history]
        last_intent = recent_intents[-1]

        # Single-message check for unambiguous intents
        if len(recent_intents) == 1:
            if last_intent == IntentCategory.CHAT:
                self._current_mode = ConversationMode.CASUAL
            elif last_intent == IntentCategory.TASK:
                self._current_mode = ConversationMode.WORKING
            elif last_intent == IntentCategory.COMMAND:
                self._current_mode = ConversationMode.COMMAND
            elif last_intent == IntentCategory.PROJECT:
                self._current_mode = ConversationMode.PROJECT_FOCUSED
            elif last_intent == IntentCategory.QUESTION:
                self._current_mode = ConversationMode.QUESTIONING
            else:
                self._current_mode = ConversationMode.INITIAL
            return

        # Multi-message transition rules
        consecutive_chat = self._count_consecutive(IntentCategory.CHAT)
        consecutive_task = self._count_consecutive(IntentCategory.TASK)

        # 2+ casual messages in a row → stay casual
        if consecutive_chat >= 2 and last_intent == IntentCategory.CHAT:
            self._current_mode = ConversationMode.CASUAL
        # Active task mode
        elif consecutive_task >= 1 and last_intent in (IntentCategory.TASK, IntentCategory.PROJECT):
            self._current_mode = ConversationMode.WORKING
        elif last_intent == IntentCategory.COMMAND:
            self._current_mode = ConversationMode.COMMAND
        elif last_intent == IntentCategory.PROJECT:
            self._current_mode = ConversationMode.PROJECT_FOCUSED
        elif last_intent == IntentCategory.QUESTION:
            self._current_mode = ConversationMode.QUESTIONING
        else:
            # Fall back to last-intent logic
            self._current_mode = self._mode_from_intent(last_intent)

    def _count_consecutive(self, intent: IntentCategory) -> int:
        """Count how many consecutive messages match the given intent (from end)."""
        count = 0
        for _, i in reversed(self._history):
            if i == intent:
                count += 1
            else:
                break
        return count

    @staticmethod
    def _mode_from_intent(intent: IntentCategory) -> ConversationMode:
        mapping = {
            IntentCategory.CHAT: ConversationMode.CASUAL,
            IntentCategory.TASK: ConversationMode.WORKING,
            IntentCategory.PROJECT: ConversationMode.PROJECT_FOCUSED,
            IntentCategory.COMMAND: ConversationMode.COMMAND,
            IntentCategory.QUESTION: ConversationMode.QUESTIONING,
            IntentCategory.AUTOMATION: ConversationMode.WORKING,
        }
        return mapping.get(intent, ConversationMode.INITIAL)

    def last_n_intents(self, n: int | None = None) -> list[IntentCategory]:
        """Get the last N intents (or all if None)."""
        intents = [i for _, i in self._history]
        if n:
            return intents[-n:]
        return list(intents)

    def reset(self) -> None:
        """Reset conversation history and mode."""
        self._history.clear()
        self._current_mode = ConversationMode.INITIAL

    @property
    def message_count(self) -> int:
        """Total messages tracked."""
        return len(self._history)
