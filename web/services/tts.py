from typing import Optional
import uuid
from pathlib import Path
from config import VOICES_DIR, AUDIO_DIR


class VoiceEngine:
    def __init__(self):
        self.cloner = None
        self._loaded = False

    def load(self):
        if self._loaded:
            return
        try:
            from kokoclone.core.cloner import KokoClone
            self.cloner = KokoClone()
            self._loaded = True
        except ImportError:
            print("[TTS] KokoClone not installed. TTS disabled.")
            self._loaded = False

    def is_available(self) -> bool:
        return self._loaded and self.cloner is not None

    def generate(self, text: str, voice_sample_path: str) -> Optional[str]:
        if not self.is_available():
            return None

        output_name = f"{uuid.uuid4().hex[:12]}.wav"
        output_path = str(AUDIO_DIR / output_name)

        try:
            self.cloner.generate(
                text=text,
                lang="en",
                reference_audio=voice_sample_path,
                output_path=output_path,
            )
            return f"/static/audio/{output_name}"
        except Exception as e:
            print(f"[TTS] Generation failed: {e}")
            return None


voice_engine = VoiceEngine()
