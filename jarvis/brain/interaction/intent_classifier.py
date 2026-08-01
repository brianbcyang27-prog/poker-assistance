"""Intent Classification — Fast pattern-based message classification.

Classifies messages into intent categories before they enter the agent pipeline.
Uses keyword/regex matching only — no LLM calls.
"""

from __future__ import annotations

import re
from enum import StrEnum


class IntentCategory(StrEnum):
    """Intent categories for user messages."""

    CHAT = "chat"  # Casual conversation, greetings, social
    TASK = "task"  # Build, implement, fix, create
    PROJECT = "project"  # Continue/resume project work
    COMMAND = "command"  # System commands, open/launch/run
    AUTOMATION = "automation"  # Daily briefing, routines, scheduled
    QUESTION = "question"  # Informational questions, what/how/why
    UNKNOWN = "unknown"  # Fallback


# Greeting / social patterns
_CHAT_PATTERNS = re.compile(
    r"^(hi|hey|hello|yo|sup|howdy|greetings|good\s*(morning|afternoon|evening)|"
    r"what'?s\s*up|how\s*(are|'re|is)\s*(you|it\s*going)|"
    r"nice\s*to\s*meet|thank(s| you)|thanks|cheers|"
    r"bye|goodbye|see\s*ya|later|talk\s*soon|"
    r"how\s*(are|'re)\s*you\s*(doing|feeling)?|"
    r"what'?s?\s*new|what'?s?\s*happening|"
    r"(i'?m|i\s*am)\s*(good|fine|great|ok|okay|doing\s*well)"
    r")\s*[.!?]*\s*$",
    re.IGNORECASE,
)

# Task patterns — user wants JARVIS to do something
_TASK_PATTERNS = re.compile(
    r"\b(build|create|implement|develop|write\s+code|add\s+feature|"
    r"fix|repair|resolve|debug|refactor|rewrite|optimize|"
    r"migrate|update|upgrade|deploy|release|"
    r"setup|configure|install|scaffold|"
    r"generate|produce|make|render|"
    r"investigate|research|find\s+out|analyze|"
    r"test|verify|validate|check|ensure)\b",
    re.IGNORECASE,
)

# Project / continuation patterns
_PROJECT_PATTERNS = re.compile(
    r"\b(continue|resume|proceed|carry\s*on|go\s*ahead|"
    r"open\s+project|load\s+project|switch\s+to|"
    r"show\s+project|project\s+status|"
    r"where\s+was\s+we?|what\s+was\s+i\s+doing)\b",
    re.IGNORECASE,
)

# Command patterns — direct system actions
_COMMAND_PATTERNS = re.compile(
    r"^(open|launch|run|start|stop|restart|close|quit|exit)\s+\w|"
    r"\b(open\s+(safari|chrome|firefox|terminal|finder|spotlight)|"
    r"take\s+(a\s+)?screenshot|screenshot|"
    r"click\s+(on\s+)?|type\s+|press\s+|"
    r"volume\s+(up|down|mute)|brightness|"
    r"lock\s+(screen|computer)|sleep|shutdown|restart)\b",
    re.IGNORECASE,
)

# Automation / routine patterns
_AUTOMATION_PATTERNS = re.compile(
    r"\b(daily\s*(briefing|summary|report|digest)|"
    r"good\s*morning|good\s*night|"
    r"briefing|rundown|"
    r"morning\s*routine|evening\s*routine|"
    r"(what'?s|what\s+is)\s+(today|my)\s+(schedule|plan|agenda)|"
    r"remind\s+me|set\s+(a\s+)?reminder|"
    r"what(\s+else)?\s*(is\s+)?(on\s+)?(my\s+)?(plate|todo|list))\b",
    re.IGNORECASE,
)

# Question patterns
_QUESTION_PATTERNS = re.compile(
    r"^(what|how|why|when|where|who|which|whose|whom)|"
    r"\b(can\s+you|could\s+you|would\s+you|will\s+you|do\s+you|"
    r"is\s+it|are\s+they|does\s+it|tell\s+me|explain|describe|"
    r"what\s+(is|are|does|was|were))\b",
    re.IGNORECASE,
)


class IntentClassifier:
    """Classifies messages by intent using pattern matching.

    This is intentionally stateless. Stateful conversation tracking
    belongs in ConversationTracker.
    """

    def classify(self, message: str) -> IntentCategory:
        """Classify a single message into an IntentCategory.

        Checks patterns in order of specificity. Falls back to UNKNOWN.
        """
        stripped = message.strip()
        if not stripped:
            return IntentCategory.UNKNOWN

        if _CHAT_PATTERNS.match(stripped):
            return IntentCategory.CHAT

        if _AUTOMATION_PATTERNS.search(stripped):
            return IntentCategory.AUTOMATION

        if _COMMAND_PATTERNS.search(stripped):
            return IntentCategory.COMMAND

        if _PROJECT_PATTERNS.search(stripped):
            return IntentCategory.PROJECT

        if _TASK_PATTERNS.search(stripped):
            return IntentCategory.TASK

        if _QUESTION_PATTERNS.match(stripped):
            return IntentCategory.QUESTION

        return IntentCategory.UNKNOWN
