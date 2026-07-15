"""Speech-to-Text module."""

from typing import Optional
from pathlib import Path


class SpeechToText:
    """Speech-to-text interface."""
    
    def __init__(self, model: str = "base"):
        self.model_name = model
        self._model = None
    
    def load(self):
        """Load the whisper model."""
        try:
            import whisper
            self._model = whisper.load_model(self.model_name)
        except ImportError:
            print("Whisper not installed. Install with: pip install openai-whisper")
        except Exception as e:
            print(f"Failed to load whisper model: {e}")
    
    @property
    def is_available(self) -> bool:
        """Check if STT is available."""
        return self._model is not None
    
    def transcribe_file(self, file_path: str) -> Optional[str]:
        """Transcribe an audio file."""
        if not self._model:
            return None
        
        try:
            result = self._model.transcribe(file_path)
            return result.get("text", "")
        except Exception as e:
            print(f"Transcription failed: {e}")
            return None
    
    def transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        """Transcribe raw audio data."""
        if not self._model:
            return None
        
        try:
            import numpy as np
            import io
            
            # Convert to numpy array (assuming WAV format)
            audio_array = np.frombuffer(audio_data, dtype=np.float32)
            result = self._model.transcribe(audio_array)
            return result.get("text", "")
        except Exception as e:
            print(f"Transcription failed: {e}")
            return None
