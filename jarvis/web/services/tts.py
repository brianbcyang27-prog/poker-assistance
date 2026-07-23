"""Voice engine service for web interface with provider pattern."""

from typing import Optional
from pathlib import Path
import subprocess
import platform
import os
import hashlib
import time


class TTSProvider:
    """Base class for TTS providers."""
    
    def generate(self, text: str, output_path: str, voice: str = "") -> Optional[str]:
        """Generate speech audio file. Returns path to generated file or None."""
        raise NotImplementedError
    
    def get_voices(self) -> list[dict]:
        """Get available voices for this provider."""
        return []
    
    @property
    def name(self) -> str:
        return "base"


class MacosProvider(TTSProvider):
    """macOS native TTS using 'say' command."""
    
    @property
    def name(self) -> str:
        return "macos"
    
    def generate(self, text: str, output_path: str, voice: str = "") -> Optional[str]:
        try:
            # macOS say requires .aiff extension for output
            p = Path(output_path)
            if p.suffix in (".wav", ".mp3", ".aiff"):
                aiff_path = str(p.with_suffix(".aiff"))
            else:
                aiff_path = str(p) + ".aiff"
            
            cmd = ["say", "-o", aiff_path]
            if voice:
                cmd.extend(["-v", voice])
            cmd.append(text)
            subprocess.run(cmd, check=True, timeout=30)
            
            # Convert to WAV using ffmpeg if available
            wav_path = str(p.with_suffix(".wav"))
            try:
                subprocess.run(["ffmpeg", "-i", aiff_path, "-y", wav_path], 
                             capture_output=True, timeout=30)
                os.remove(aiff_path)
                return wav_path
            except FileNotFoundError:
                # ffmpeg not available, return aiff file
                return aiff_path
        except Exception as e:
            print(f"macOS TTS failed: {e}")
            return None
    
    def get_voices(self) -> list[dict]:
        try:
            result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, timeout=5)
            voices = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        voices.append({"id": parts[0], "name": parts[0], "language": parts[1] if len(parts) > 1 else ""})
            return voices
        except Exception:
            return []


class KokoroProvider(TTSProvider):
    """Kokoro TTS - local neural TTS.
    
    First import takes 10-30s due to torch/transformers loading.
    Subsequent uses are fast.
    """
    
    def __init__(self):
        self._pipeline = None
        self._load_attempted = False
        self._load_error = None
    
    @property
    def name(self) -> str:
        return "kokoro"
    
    def _load_pipeline(self):
        if self._pipeline is not None:
            return
        if self._load_attempted:
            return
        self._load_attempted = True
        
        try:
            from kokoro import KPipeline
            self._pipeline = KPipeline(lang_code="a")  # Default to English
            print("[Kokoro] Pipeline loaded successfully")
        except ImportError as e:
            self._load_error = f"Kokoro not installed: {e}"
            print(f"[Kokoro] {self._load_error}")
        except Exception as e:
            self._load_error = f"Kokoro failed to load: {e}"
            print(f"[Kokoro] {self._load_error}")
    
    def generate(self, text: str, output_path: str, voice: str = "") -> Optional[str]:
        self._load_pipeline()
        
        if self._pipeline is None:
            return None
        
        try:
            import soundfile as sf
            import numpy as np
            
            voice = voice or "af_heart"  # Default Kokoro voice
            wav_path = output_path if output_path.endswith(".wav") else output_path.replace(".mp3", ".wav")
            
            # Generate audio
            generator = self._pipeline(text, voice=voice)
            audio_data = []
            for _, _, audio in generator:
                audio_data.append(audio)
            
            full_audio = np.concatenate(audio_data)
            sf.write(wav_path, full_audio, 24000)
            return wav_path
        except Exception as e:
            print(f"[Kokoro] Generation failed: {e}")
            return None
    
    def get_voices(self) -> list[dict]:
        return [
            {"id": "af_heart", "name": "Heart (Female)", "language": "en-US"},
            {"id": "af_bella", "name": "Bella (Female)", "language": "en-US"},
            {"id": "af_nicole", "name": "Nicole (Female)", "language": "en-US"},
            {"id": "af_sarah", "name": "Sarah (Female)", "language": "en-US"},
            {"id": "am_adam", "name": "Adam (Male)", "language": "en-US"},
            {"id": "am_michael", "name": "Michael (Male)", "language": "en-US"},
        ]


class OpenAIProvider(TTSProvider):
    """OpenAI TTS API - cloud-based."""
    
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    
    @property
    def name(self) -> str:
        return "openai"
    
    def generate(self, text: str, output_path: str, voice: str = "") -> Optional[str]:
        if not self.api_key:
            raise RuntimeError("OpenAI API key not configured")
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            voice = voice or "alloy"
            mp3_path = output_path if output_path.endswith(".mp3") else output_path.replace(".wav", ".mp3")
            
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text,
            )
            response.stream_to_file(mp3_path)
            
            # Convert to WAV if needed
            if output_path.endswith(".wav"):
                wav_path = output_path
                subprocess.run(["ffmpeg", "-i", mp3_path, "-y", wav_path], 
                             capture_output=True, timeout=30)
                os.remove(mp3_path)
                return wav_path
            
            return mp3_path
        except Exception as e:
            print(f"OpenAI TTS failed: {e}")
            return None
    
    def get_voices(self) -> list[dict]:
        return [
            {"id": "alloy", "name": "Alloy", "language": "en-US"},
            {"id": "echo", "name": "Echo", "language": "en-US"},
            {"id": "fable", "name": "Fable", "language": "en-US"},
            {"id": "onyx", "name": "Onyx", "language": "en-US"},
            {"id": "nova", "name": "Nova", "language": "en-US"},
            {"id": "shimmer", "name": "Shimmer", "language": "en-US"},
        ]


class VoiceEngine:
    """Voice engine for TTS in web interface with provider pattern."""
    
    def __init__(self):
        self.providers: dict[str, TTSProvider] = {}
        self._loaded = False
        self._init_providers()
    
    def _init_providers(self):
        """Initialize available TTS providers."""
        # Always register macOS provider on macOS
        if platform.system() == "Darwin":
            self.providers["macos"] = MacosProvider()
        
        # Register Kokoro — lazy-loads torch on first use (not at import time)
        self.providers["kokoro"] = KokoroProvider()
        print("[TTS] Kokoro provider registered (lazy-load)")
        
        # Register OpenAI if API key is available
        from jarvis.core.config import get_config
        config = get_config()
        if config.openai_api_key:
            self.providers["openai"] = OpenAIProvider(config.openai_api_key)
    
    def load(self):
        """Load the voice engine."""
        self._loaded = True
    
    @property
    def is_available(self) -> bool:
        """Check if voice engine is available."""
        return len(self.providers) > 0 and self._loaded
    
    def get_provider(self, name: Optional[str] = None) -> Optional[TTSProvider]:
        """Get a specific provider or the default one."""
        if name and name in self.providers:
            return self.providers[name]
        
        # Default priority: kokoro > openai > macos
        for priority in ["kokoro", "openai", "macos"]:
            if priority in self.providers:
                return self.providers[priority]
        
        return None
    
    def generate(self, text: str, output_path: str, voice: str = "", provider: str = "") -> Optional[str]:
        """Generate speech audio file.
        
        If voice starts with "clone:", it will use the voice cloner with the profile ID.
        Format: "clone:<profile_id>" or "clone:<profile_id>:<language>"
        """
        # Check if this is a cloned voice
        if voice.startswith("clone:"):
            return self._generate_cloned(text, output_path, voice)
        
        tts_provider = self.get_provider(provider)
        if not tts_provider:
            return None
        
        return tts_provider.generate(text, output_path, voice)
    
    def _generate_cloned(self, text: str, output_path: str, voice: str) -> Optional[str]:
        """Generate speech using a cloned voice."""
        try:
            from jarvis.voice.voice_clone import voice_cloner
            
            # Parse voice string: "clone:<profile_id>" or "clone:<profile_id>:<language>"
            parts = voice.split(":")
            if len(parts) < 2:
                print("[TTS] Invalid clone voice format. Expected: clone:<profile_id>")
                return None
            
            profile_id = parts[1]
            language = parts[2] if len(parts) > 2 else "en"
            
            if not voice_cloner.is_available:
                print(f"[TTS] Voice cloning not available: {voice_cloner.error}")
                return None
            
            return voice_cloner.clone_voice(
                text=text,
                profile_id=profile_id,
                output_path=output_path,
                language=language
            )
        except Exception as e:
            print(f"[TTS] Cloned voice generation failed: {e}")
            return None
    
    def get_all_voices(self) -> dict[str, list[dict]]:
        """Get all available voices from all providers."""
        voices = {}
        for name, provider in self.providers.items():
            voices[name] = provider.get_voices()
        return voices


# Singleton
voice_engine = VoiceEngine()
