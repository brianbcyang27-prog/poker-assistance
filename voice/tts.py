import subprocess
import platform
from typing import Optional
from pathlib import Path
import tempfile
import os

from ..config import get_config


class TextToSpeech:
    """Text-to-speech conversion using macOS native TTS or Piper."""
    
    def __init__(self):
        config = get_config()
        self.enabled = config.tts_enabled
        self.backend = self._detect_backend()
    
    def _detect_backend(self) -> str:
        """Detect the available TTS backend."""
        system = platform.system()
        
        if system == "Darwin":
            return "macos"
        
        try:
            subprocess.run(["piper", "--help"], capture_output=True)
            return "piper"
        except FileNotFoundError:
            pass
        
        try:
            subprocess.run(["espeak", "--version"], capture_output=True)
            return "espeak"
        except FileNotFoundError:
            pass
        
        return "none"
    
    def speak(self, text: str, voice: Optional[str] = None) -> bool:
        """Convert text to speech and play it."""
        if not self.enabled:
            return False
        
        if self.backend == "macos":
            return self._speak_macos(text, voice)
        elif self.backend == "piper":
            return self._speak_piper(text, voice)
        elif self.backend == "espeak":
            return self._speak_espeak(text)
        else:
            print(f"[TTS unavailable] {text}")
            return False
    
    def _speak_macos(self, text: str, voice: Optional[str] = None) -> bool:
        """Use macOS native say command."""
        try:
            cmd = ["say"]
            if voice:
                cmd.extend(["-v", voice])
            cmd.append(text)
            
            subprocess.run(cmd, check=True)
            return True
        except Exception as e:
            print(f"macOS TTS error: {e}")
            return False
    
    def _speak_piper(self, text: str, voice: Optional[str] = None) -> bool:
        """Use Piper TTS."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
            
            cmd = ["piper", "--output_file", temp_path]
            if voice:
                cmd.extend(["--model", voice])
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            process.communicate(input=text.encode())
            
            if os.path.exists(temp_path):
                subprocess.run(["aplay", temp_path], check=True)
                os.unlink(temp_path)
                return True
            
            return False
        except Exception as e:
            print(f"Piper TTS error: {e}")
            return False
    
    def _speak_espeak(self, text: str) -> bool:
        """Use espeak TTS."""
        try:
            subprocess.run(["espeak", text], check=True)
            return True
        except Exception as e:
            print(f"espeak TTS error: {e}")
            return False
    
    def save_to_file(self, text: str, output_path: str, voice: Optional[str] = None) -> bool:
        """Save text to audio file."""
        if self.backend == "macos":
            try:
                cmd = ["say", "-o", output_path]
                if voice:
                    cmd.extend(["-v", voice])
                cmd.append(text)
                
                subprocess.run(cmd, check=True)
                return True
            except Exception as e:
                print(f"Save audio error: {e}")
                return False
        
        return False
    
    def get_voices(self) -> list[str]:
        """Get available voices."""
        if self.backend == "macos":
            try:
                result = subprocess.run(
                    ["say", "-v", "?"],
                    capture_output=True,
                    text=True
                )
                voices = []
                for line in result.stdout.split('\n'):
                    if line.strip():
                        voice_name = line.split()[0]
                        voices.append(voice_name)
                return voices
            except Exception:
                return []
        
        return []
    
    def is_available(self) -> bool:
        """Check if text-to-speech is available."""
        return self.backend != "none" and self.enabled