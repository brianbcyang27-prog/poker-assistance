"""Importance Scorer — Decides what deserves memory.

Not everything should be remembered. This module scores the importance
of information to decide what gets stored in long-term memory.

Scoring signals:
- User explicitly says "remember" (+100)
- Major architectural decision (+80)
- Project context (+70)
- User preference (+60)
- Completed mission (+50)
- Normal conversation (+10)
- Temporary information (0)
"""

import re
import logging
from typing import Optional

log = logging.getLogger("jarvis.memory.importance")


class ImportanceScorer:
    """Scores the importance of content for memory storage decisions.

    Usage:
        scorer = ImportanceScorer()
        score = scorer.score(
            text="We decided to use FastAPI for the backend",
            context={"type": "conversation", "has_decision": True}
        )
        # score: ~75

        if score >= 50:
            # Store in long-term memory
            pass
    """

    # Explicit signals that boost importance
    EXPLICIT_SIGNALS = {
        "remember": 100,
        "don't forget": 100,
        "never forget": 100,
        "important": 80,
        "critical": 75,
        "always": 60,
        "never": 60,
        "rule": 70,
        "preference": 60,
        "i like": 55,
        "i prefer": 60,
        "i hate": 55,
        "i want": 40,
        "i need": 45,
    }

    # Topic signals
    TOPIC_SIGNALS = {
        "architecture": 70,
        "design": 60,
        "decision": 75,
        "bug": 50,
        "fix": 40,
        "launch": 65,
        "deploy": 60,
        "milestone": 65,
        "completed": 55,
        "goal": 50,
        "plan": 45,
        "problem": 40,
        "solution": 45,
        "security": 70,
        "privacy": 75,
        "api": 30,
        "database": 35,
        "performance": 45,
    }

    # Content type multipliers
    TYPE_MULTIPLIERS = {
        "decision": 1.5,
        "mission": 1.3,
        "milestone": 1.4,
        "error": 0.8,  # Errors are often temporary
        "conversation": 1.0,
        "learning": 1.2,
    }

    def score(
        self,
        text: str,
        context: Optional[dict] = None,
    ) -> float:
        """Compute importance score for content.

        Args:
            text: The content to score
            context: Optional context about the content
                - type: content type (conversation, decision, mission, etc.)
                - has_decision: whether it contains a decision
                - has_outcome: whether it has a clear outcome
                - user_sentiment: positive/negative/neutral

        Returns:
            Score from 0 to 100
        """
        context = context or {}
        text_lower = text.lower()
        score = 10.0  # baseline

        # 1. Explicit signals
        for signal, boost in self.EXPLICIT_SIGNALS.items():
            if signal in text_lower:
                score += boost

        # 2. Topic signals
        for topic, boost in self.TOPIC_SIGNALS.items():
            if topic in text_lower:
                score += boost * 0.5  # weight topics lower than explicit signals

        # 3. Content structure signals
        if context.get("has_decision"):
            score += 20
        if context.get("has_outcome"):
            score += 10

        # 4. Length signal — very short content is usually less important
        words = len(text.split())
        if words < 5:
            score *= 0.5
        elif words > 50:
            score *= 1.1

        # 5. Question detection — questions are often less important than answers
        if text.strip().endswith("?"):
            score *= 0.7

        # 6. Code blocks — code decisions are important
        if "```" in text or "def " in text or "class " in text:
            score *= 1.2

        # 7. Type multiplier
        content_type = context.get("type", "conversation")
        multiplier = self.TYPE_MULTIPLIERS.get(content_type, 1.0)
        score *= multiplier

        # 8. Sentiment signal
        sentiment = context.get("user_sentiment", "neutral")
        if sentiment == "positive":
            score *= 1.1
        elif sentiment == "negative":
            score *= 1.05  # Negative experiences are worth remembering too

        return min(100.0, max(0.0, score))

    def should_store(self, score: float, threshold: float = 50.0) -> bool:
        """Decide whether content should be stored in long-term memory."""
        return score >= threshold

    def score_batch(
        self,
        items: list[dict],
        threshold: float = 50.0,
    ) -> list[dict]:
        """Score a batch of items and filter by threshold.

        Each item should have 'text' and optional 'context' keys.
        Returns items with 'importance' added and filtered by threshold.
        """
        results = []
        for item in items:
            score = self.score(item.get("text", ""), item.get("context", {}))
            if score >= threshold:
                results.append({**item, "importance": score})
        return sorted(results, key=lambda x: -x["importance"])

    def extract_signals(self, text: str) -> dict:
        """Extract importance signals from text for debugging/display."""
        text_lower = text.lower()
        signals = {
            "explicit": [],
            "topics": [],
            "structure": {},
        }

        for signal in self.EXPLICIT_SIGNALS:
            if signal in text_lower:
                signals["explicit"].append(signal)

        for topic in self.TOPIC_SIGNALS:
            if topic in text_lower:
                signals["topics"].append(topic)

        signals["structure"]["word_count"] = len(text.split())
        signals["structure"]["is_question"] = text.strip().endswith("?")
        signals["structure"]["has_code"] = "```" in text or "def " in text

        return signals


# Module-level singleton
importance_scorer = ImportanceScorer()
