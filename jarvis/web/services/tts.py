"""Voice engine service for web interface."""

from typing import Optional
from pathlib import Path
import subprocess
import platform


class VoiceEngine:
    """Voice engine for TTS in web interface."""
    
    def __init__(self):
        self.backend = self._detect_backend()
        self._loaded = False
    
    def _detect_backend(self) -> str:
        """Detect available TTS backend."""
        system = platform.system()
        
        if system == "Darwin":
            return "macos"
        
        # Check for piper
        try:
            result = subprocess.run(
                ["piper", "--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return "piper"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        return "none"
    
    def load(self):
        """Load the voice engine."""
        self._loaded = True
    
    @property
    def is_available(self) -> bool:
        """Check if voice engine is available."""
        return self.backend != "none" and self._loaded
    
    def generate(self, text: str, output_path: str) -> Optional[str]:
        """Generate speech audio file."""
        if not self.is_available:
            return None
        
        try:
            if self.backend == "macos":
                wav_path = output_path.replace(".mp3", ".wav")
                subprocess.run(
                    ["say", "-o", wav_path, text],
                    check=True,
                    timeout=30,
                )
                return wav_path
        
        except Exception as e:
            print(f"TTS generation failed: {e}")
            return None
        
        return None


# Singleton
voice_engine = VoiceEngine()
