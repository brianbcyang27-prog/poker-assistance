"""v9.0.0 regression tests — interaction layer response policy."""


class TestResponsePolicy:
    """ResponsePolicy correctly gates capability exposure."""

    def _make_policy(self):
        from jarvis.brain.interaction.conversation_mode import ConversationMode
        from jarvis.brain.interaction.intent_classifier import IntentCategory
        from jarvis.brain.interaction.response_policy import ResponsePolicy

        return ResponsePolicy(), ConversationMode, IntentCategory

    def test_casual_chat_excludes_caps(self):
        policy, Mode, Cat = self._make_policy()
        assert policy.should_include_capability_dump(Mode.CASUAL, Cat.CHAT) is False

    def test_casual_unknown_excludes_caps(self):
        policy, Mode, Cat = self._make_policy()
        assert policy.should_include_capability_dump(Mode.CASUAL, Cat.UNKNOWN) is False

    def test_working_mode_includes_caps(self):
        policy, Mode, Cat = self._make_policy()
        assert policy.should_include_capability_dump(Mode.WORKING, Cat.TASK) is True
        assert policy.should_include_capability_dump(Mode.WORKING, Cat.CHAT) is True

    def test_command_mode_includes_caps(self):
        policy, Mode, Cat = self._make_policy()
        assert policy.should_include_capability_dump(Mode.COMMAND, Cat.COMMAND) is True

    def test_project_focused_includes_caps(self):
        policy, Mode, Cat = self._make_policy()
        assert policy.should_include_capability_dump(Mode.PROJECT_FOCUSED, Cat.PROJECT) is True

    def test_questioning_excludes_caps(self):
        policy, Mode, Cat = self._make_policy()
        assert policy.should_include_capability_dump(Mode.QUESTIONING, Cat.QUESTION) is False

    def test_initial_with_task_includes_caps(self):
        policy, Mode, Cat = self._make_policy()
        assert policy.should_include_capability_dump(Mode.INITIAL, Cat.TASK) is True

    def test_initial_with_chat_excludes_caps(self):
        policy, Mode, Cat = self._make_policy()
        assert policy.should_include_capability_dump(Mode.INITIAL, Cat.CHAT) is False

    def test_initial_with_question_excludes_caps(self):
        policy, Mode, Cat = self._make_policy()
        assert policy.should_include_capability_dump(Mode.INITIAL, Cat.QUESTION) is False

    def test_get_response_style_returns_string(self):
        policy, Mode, _ = self._make_policy()
        style = policy.get_response_style(Mode.CASUAL)
        assert isinstance(style, str)
        assert len(style) > 10

    def test_get_response_style_all_modes(self):
        policy, Mode, _ = self._make_policy()
        for mode in Mode:
            style = policy.get_response_style(mode)
            assert isinstance(style, str), f"no style for {mode}"
            assert len(style) > 10, f"style too short for {mode}"
