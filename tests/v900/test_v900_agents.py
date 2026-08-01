"""v9.0.0 regression tests — agent hierarchy structure."""


class TestInteractionLayer:
    """InteractionLayer can be instantiated and basic methods work."""

    def test_interaction_layer_init(self):
        from jarvis.brain.interaction import InteractionLayer

        layer = InteractionLayer()
        assert layer is not None
        assert layer.classifier is not None
        assert layer.tracker is not None
        assert layer.policy is not None

    def test_interaction_layer_classify(self):
        from jarvis.brain.interaction import InteractionLayer
        from jarvis.brain.interaction.intent_classifier import IntentCategory

        layer = InteractionLayer()
        assert layer.classify("hello") == IntentCategory.CHAT
        assert layer.classify("build") == IntentCategory.TASK

    def test_interaction_layer_get_mode(self):
        from jarvis.brain.interaction import InteractionLayer
        from jarvis.brain.interaction.conversation_mode import ConversationMode
        from jarvis.brain.interaction.intent_classifier import IntentCategory

        layer = InteractionLayer()
        assert layer.get_mode() == ConversationMode.INITIAL
        layer.tracker.record("hello", IntentCategory.CHAT)
        assert layer.get_mode() == ConversationMode.CASUAL
