"""Response Policy — Controls response behavior based on context.

Determines when to include capability dumps, how to style responses,
and what information to expose to the user.
"""

from __future__ import annotations

from .conversation_mode import ConversationMode
from .intent_classifier import IntentCategory


class ResponsePolicy:
    """Controls response behavior based on conversation context.

    The primary function is to gate the capability system prompt —
    casual chat should never dump all available tools to the user.
    """

    def should_include_capability_dump(
        self,
        mode: ConversationMode,
        intent: IntentCategory,
    ) -> bool:
        """Determine whether the capability system prompt should be injected.

        Returns True (include capabilities) when the conversation is in
        a working/task-oriented state. Returns False for casual chat.

        Rules:
        - CASUAL/INITIAL with CHAT intent → False (no dump)
        - WORKING/COMMAND/PROJECT_FOCUSED → True
        - CASUAL mode but TASK intent → True (mode didn't switch yet)
        - QUESTIONING mode → False (just answer the question)
        """
        # Always include capabilities when working or commanding
        if mode in (
            ConversationMode.WORKING,
            ConversationMode.COMMAND,
            ConversationMode.PROJECT_FOCUSED,
        ):
            return True

        # Always exclude for pure chat/unknown intents in casual mode
        if mode == ConversationMode.CASUAL and intent in (
            IntentCategory.CHAT,
            IntentCategory.UNKNOWN,
        ):
            return False

        # Always exclude in questioning mode
        if mode == ConversationMode.QUESTIONING:
            return False

        # Exclude at initial state unless it's clearly a task
        if mode == ConversationMode.INITIAL:
            return intent in (
                IntentCategory.TASK,
                IntentCategory.PROJECT,
                IntentCategory.COMMAND,
                IntentCategory.AUTOMATION,
            )

        # Default: include capabilities (safe — over-expose rather than under)
        return True

    def get_response_style(self, mode: ConversationMode) -> str:
        """Return style guidance for the current mode."""
        styles = {
            ConversationMode.CASUAL: (
                "Respond conversationally and concisely. Do not list tools or capabilities."
            ),
            ConversationMode.WORKING: (
                "Respond as a capable AI assistant. "
                "You have tools available — use them proactively."
            ),
            ConversationMode.COMMAND: (
                "Execute the requested command. Be brief and confirm the action."
            ),
            ConversationMode.PROJECT_FOCUSED: (
                "You are in an active project context. "
                "Reference the current project and continue work."
            ),
            ConversationMode.QUESTIONING: (
                "Answer the question directly. Be informative but don't offer unsolicited actions."
            ),
            ConversationMode.INITIAL: (
                "This is the first interaction. Be welcoming but don't overwhelm with capabilities."
            ),
        }
        return styles.get(mode, "Respond helpfully and concisely.")
