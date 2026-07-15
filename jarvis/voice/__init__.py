"""Voice module - Speech I/O."""

from .stt import SpeechToText
from .tts import TextToSpeech

__all__ = ["SpeechToText", "TextToSpeech"]
