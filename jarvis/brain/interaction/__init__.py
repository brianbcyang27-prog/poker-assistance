"""Human Interaction Layer — Entry point for all user messages.

Classifies intent, tracks conversation mode, and controls response policy
before the message enters the agent pipeline.
"""

from .conversation_mode import ConversationMode, ConversationTracker
from .intent_classifier import IntentCategory, IntentClassifier
from .response_policy import ResponsePolicy


class InteractionLayer:
    """Single entry point for processing user messages before agent dispatch.

    Usage:
        layer = InteractionLayer()
        intent = layer.classify("hello")
        layer.tracker.record("hello", intent)
        show_caps = layer.should_expose_capabilities(intent)
    """

    def __init__(self):
        self.classifier = IntentClassifier()
        self.tracker = ConversationTracker()
        self.policy = ResponsePolicy()

    def classify(self, message: str) -> IntentCategory:
        """Classify a user message into an intent category."""
        return self.classifier.classify(message)

    def get_mode(self) -> ConversationMode:
        """Get the current conversation mode."""
        return self.tracker.current_mode

    def should_expose_capabilities(self, message: str) -> bool:
        """Determine whether the capability system prompt should be injected.

        Returns False for casual chat to keep responses lightweight.
        """
        intent = self.classify(message)
        mode = self.tracker.current_mode
        return self.policy.should_include_capability_dump(mode, intent)


__all__ = [
    "InteractionLayer",
    "IntentCategory",
    "IntentClassifier",
    "ConversationMode",
    "ConversationTracker",
    "ResponsePolicy",
]
