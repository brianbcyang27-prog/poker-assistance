import whisper
import numpy as np
from typing import Optional
import tempfile
import os

from ..config import get_config


class SpeechToText:
    """Whisper-based speech-to-text conversion."""
    
    def __init__(self):
        config = get_config()
        self.model_name = config.whisper_model
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the Whisper model."""
        try:
            self.model = whisper.load_model(self.model_name)
        except Exception as e:
            print(f"Warning: Could not load Whisper model: {e}")
            print("Voice input will be disabled.")
            self.model = None
    
    def transcribe_file(self, file_path: str) -> Optional[str]:
        """Transcribe an audio file."""
        if not self.model:
            return None
        
        try:
            result = self.model.transcribe(file_path)
            return result["text"].strip()
        except Exception as e:
            print(f"Transcription error: {e}")
            return None
    
    def transcribe_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        """Transcribe raw audio data."""
        if not self.model:
            return None
        
        try:
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32) / 32768.0
            
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)
            
            result = self.model.transcribe(audio_data)
            return result["text"].strip()
        except Exception as e:
            print(f"Transcription error: {e}")
            return None
    
    def transcribe_microphone(self, duration: int = 5) -> Optional[str]:
        """Record from microphone and transcribe."""
        try:
            import pyaudio
            
            chunk = 1024
            sample_format = pyaudio.paInt16
            channels = 1
            sample_rate = 16000
            
            p = pyaudio.PyAudio()
            
            stream = p.open(
                format=sample_format,
                channels=channels,
                rate=sample_rate,
                input=True,
                frames_per_buffer=chunk,
            )
            
            print(f"Recording for {duration} seconds...")
            
            frames = []
            for _ in range(0, int(sample_rate / chunk * duration)):
                data = stream.read(chunk)
                frames.append(data)
            
            print("Recording complete.")
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
            
            return self.transcribe_audio(audio_data, sample_rate)
            
        except ImportError:
            print("PyAudio not installed. Install with: pip install pyaudio")
            return None
        except Exception as e:
            print(f"Microphone recording error: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if speech-to-text is available."""
        return self.model is not None