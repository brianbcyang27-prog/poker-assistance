"""Text-to-Speech module."""

import subprocess
import platform
from typing import Optional
from pathlib import Path


class TextToSpeech:
    """Text-to-speech interface supporting multiple backends."""
    
    def __init__(self):
        self.backend = self._detect_backend()
        self._available = False
    
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
        
        # Check for espeak
        try:
            result = subprocess.run(
                ["espeak", "--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return "espeak"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        return "none"
    
    @property
    def is_available(self) -> bool:
        """Check if TTS is available."""
        return self.backend != "none"
    
    def speak(self, text: str) -> bool:
        """Speak text using available backend."""
        if not self.is_available:
            return False
        
        try:
            if self.backend == "macos":
                subprocess.run(
                    ["say", text],
                    check=True,
                    timeout=30,
                )
                return True
            
            elif self.backend == "piper":
                # Piper TTS
                result = subprocess.run(
                    ["piper", "--output_file", "/tmp/jarvis_tts.wav"],
                    input=text.encode(),
                    check=True,
                    timeout=30,
                )
                # Play the audio
                subprocess.run(
                    ["afplay", "/tmp/jarvis_tts.wav"] if platform.system() == "Darwin"
                    else ["aplay", "/tmp/jarvis_tts.wav"],
                    check=True,
                    timeout=30,
                )
                return True
            
            elif self.backend == "espeak":
                subprocess.run(
                    ["espeak", text],
                    check=True,
                    timeout=30,
                )
                return True
        
        except Exception as e:
            print(f"TTS failed: {e}")
            return False
        
        return False
    
    def generate_file(self, text: str, output_path: str) -> bool:
        """Generate speech audio file."""
        if not self.is_available:
            return False
        
        try:
            if self.backend == "macos":
                subprocess.run(
                    ["say", "-o", output_path, text],
                    check=True,
                    timeout=30,
                )
                return True
            
            elif self.backend == "piper":
                subprocess.run(
                    ["piper", "--output_file", output_path],
                    input=text.encode(),
                    check=True,
                    timeout=30,
                )
                return True
        
        except Exception as e:
            print(f"TTS generation failed: {e}")
            return False
        
        return False
