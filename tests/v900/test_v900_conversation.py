"""v9.0.0 regression tests — conversation privacy and intent classification."""


class TestIntentClassification:
    """Intent classifier correctly categorizes messages."""

    def _make_classifier(self):
        from jarvis.brain.interaction.intent_classifier import IntentCategory, IntentClassifier

        return IntentClassifier(), IntentCategory

    def test_chat_intent(self):
        clf, Cat = self._make_classifier()
        assert clf.classify("hi") == Cat.CHAT
        assert clf.classify("hello") == Cat.CHAT
        assert clf.classify("how are you") == Cat.CHAT
        assert clf.classify("good morning") == Cat.CHAT
        assert clf.classify("thanks") == Cat.CHAT

    def test_task_intent(self):
        clf, Cat = self._make_classifier()
        assert clf.classify("build a website") == Cat.TASK
        assert clf.classify("implement login") == Cat.TASK
        assert clf.classify("fix the bug") == Cat.TASK
        assert clf.classify("create a component") == Cat.TASK
        assert clf.classify("refactor the module") == Cat.TASK

    def test_project_intent(self):
        clf, Cat = self._make_classifier()
        assert clf.classify("continue the project") == Cat.PROJECT
        assert clf.classify("resume where I left off") == Cat.PROJECT

    def test_command_intent(self):
        clf, Cat = self._make_classifier()
        assert clf.classify("open safari") == Cat.COMMAND
        assert clf.classify("take a screenshot") == Cat.COMMAND

    def test_question_intent(self):
        clf, Cat = self._make_classifier()
        assert clf.classify("what is the weather") == Cat.QUESTION
        assert clf.classify("how does this work") == Cat.QUESTION

    def test_automation_intent(self):
        clf, Cat = self._make_classifier()
        assert clf.classify("daily briefing") == Cat.AUTOMATION
        assert clf.classify("good morning") == Cat.CHAT  # greets match CHAT first


class TestConversationPrivacy:
    """Capability system prompt is not exposed during casual chat."""

    def test_should_expose_capabilities_chat(self):
        from jarvis.brain.interaction import InteractionLayer

        layer = InteractionLayer()
        # A casual greeting should NOT expose capabilities
        assert layer.should_expose_capabilities("hello") is False
        assert layer.should_expose_capabilities("how are you") is False

    def test_should_expose_capabilities_task(self):
        from jarvis.brain.interaction import InteractionLayer

        layer = InteractionLayer()
        # A task request SHOULD expose capabilities
        assert layer.should_expose_capabilities("build a website") is True
        assert layer.should_expose_capabilities("implement login") is True

    def test_should_expose_capabilities_command(self):
        from jarvis.brain.interaction import InteractionLayer

        layer = InteractionLayer()
        assert layer.should_expose_capabilities("open safari") is True

    def test_should_expose_capabilities_question(self):
        from jarvis.brain.interaction import InteractionLayer

        layer = InteractionLayer()
        assert layer.should_expose_capabilities("what is the weather") is False

    def test_casual_mode_does_not_expose_caps(self):
        from jarvis.brain.interaction import InteractionLayer
        from jarvis.brain.interaction.conversation_mode import ConversationMode
        from jarvis.brain.interaction.intent_classifier import IntentCategory

        layer = InteractionLayer()
        # Simulate multi-turn casual conversation
        tracker = layer.tracker
        tracker.record("hi", IntentCategory.CHAT)
        tracker.record("how are you", IntentCategory.CHAT)

        assert tracker.current_mode == ConversationMode.CASUAL
        assert (
            layer.policy.should_include_capability_dump(
                ConversationMode.CASUAL, IntentCategory.CHAT
            )
            is False
        )

    def test_working_mode_exposes_caps(self):
        from jarvis.brain.interaction import InteractionLayer
        from jarvis.brain.interaction.conversation_mode import ConversationMode
        from jarvis.brain.interaction.intent_classifier import IntentCategory

        layer = InteractionLayer()
        tracker = layer.tracker
        tracker.record("build a website", IntentCategory.TASK)

        assert tracker.current_mode == ConversationMode.WORKING
        assert (
            layer.policy.should_include_capability_dump(
                ConversationMode.WORKING, IntentCategory.TASK
            )
            is True
        )


class TestConversationTracker:
    """ConversationTracker tracks mode transitions."""

    def test_initial_mode(self):
        from jarvis.brain.interaction.conversation_mode import ConversationMode, ConversationTracker

        tracker = ConversationTracker()
        assert tracker.current_mode == ConversationMode.INITIAL

    def test_single_chat_transitions_to_casual(self):
        from jarvis.brain.interaction.conversation_mode import ConversationMode, ConversationTracker
        from jarvis.brain.interaction.intent_classifier import IntentCategory

        tracker = ConversationTracker()
        tracker.record("hi", IntentCategory.CHAT)
        assert tracker.current_mode == ConversationMode.CASUAL

    def test_task_transitions_to_working(self):
        from jarvis.brain.interaction.conversation_mode import ConversationMode, ConversationTracker
        from jarvis.brain.interaction.intent_classifier import IntentCategory

        tracker = ConversationTracker()
        tracker.record("build a website", IntentCategory.TASK)
        assert tracker.current_mode == ConversationMode.WORKING

    def test_message_count(self):
        from jarvis.brain.interaction.conversation_mode import ConversationTracker
        from jarvis.brain.interaction.intent_classifier import IntentCategory

        tracker = ConversationTracker()
        assert tracker.message_count == 0
        tracker.record("hi", IntentCategory.CHAT)
        tracker.record("hello", IntentCategory.CHAT)
        assert tracker.message_count == 2

    def test_reset(self):
        from jarvis.brain.interaction.conversation_mode import ConversationMode, ConversationTracker
        from jarvis.brain.interaction.intent_classifier import IntentCategory

        tracker = ConversationTracker()
        tracker.record("hi", IntentCategory.CHAT)
        assert tracker.current_mode != ConversationMode.INITIAL
        tracker.reset()
        assert tracker.current_mode == ConversationMode.INITIAL
        assert tracker.message_count == 0
