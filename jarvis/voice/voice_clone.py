"""Voice Cloning module using Coqui TTS XTTS v2."""

import os
import time
import hashlib
from pathlib import Path
from typing import Optional, Dict, List
import json


class VoiceProfile:
    """Voice profile for cloned voice."""
    
    def __init__(self, name: str, audio_path: str, profile_id: str = ""):
        self.name = name
        self.audio_path = audio_path
        self.profile_id = profile_id or self._generate_id()
        self.created_at = time.time()
        self.metadata: Dict = {}
    
    def _generate_id(self) -> str:
        """Generate unique profile ID."""
        content = f"{self.name}:{self.audio_path}:{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "audio_path": self.audio_path,
            "created_at": self.created_at,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VoiceProfile':
        """Create from dictionary."""
        profile = cls(
            name=data["name"],
            audio_path=data["audio_path"],
            profile_id=data.get("profile_id", "")
        )
        profile.created_at = data.get("created_at", time.time())
        profile.metadata = data.get("metadata", {})
        return profile


class VoiceCloner:
    """Voice cloning engine using Coqui TTS XTTS v2."""
    
    def __init__(self, profiles_dir: str = "~/.jarvis/voice_profiles"):
        self.profiles_dir = Path(profiles_dir).expanduser()
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._load_attempted = False
        self._load_error = None
        self.profiles: Dict[str, VoiceProfile] = {}
        self._load_profiles()
    
    def _load_profiles(self):
        """Load saved voice profiles."""
        profiles_file = self.profiles_dir / "profiles.json"
        if profiles_file.exists():
            try:
                with open(profiles_file) as f:
                    data = json.load(f)
                    for profile_data in data.get("profiles", []):
                        profile = VoiceProfile.from_dict(profile_data)
                        self.profiles[profile.profile_id] = profile
            except Exception as e:
                print(f"[VoiceClone] Failed to load profiles: {e}")
    
    def _save_profiles(self):
        """Save voice profiles to disk."""
        profiles_file = self.profiles_dir / "profiles.json"
        try:
            data = {
                "profiles": [p.to_dict() for p in self.profiles.values()]
            }
            with open(profiles_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[VoiceClone] Failed to save profiles: {e}")
    
    def _load_model(self):
        """Load XTTS v2 model."""
        if self._model is not None:
            return True
        if self._load_attempted:
            return False
        self._load_attempted = True
        
        try:
            import torch

            original_torch_load = torch.load

            def patched_torch_load(*args, **kwargs):
                kwargs.setdefault("weights_only", False)
                return original_torch_load(*args, **kwargs)

            torch.load = patched_torch_load

            import os
            os.environ["COQUI_TOS_AGREED"] = "1"
            from TTS.api import TTS
            for model_name, label in [
                ("tts_models/multilingual/multi-dataset/your_tts", "YourTTS"),
                ("xtts", "XTTS v2"),
            ]:
                try:
                    print(f"[VoiceClone] Loading {label} model...")
                    self._model = TTS(model_name)
                    print(f"[VoiceClone] {label} model loaded successfully")
                    return True
                except Exception as e:
                    self._load_error = f"Failed to load {label}: {e}"
                    print(f"[VoiceClone] {self._load_error}")
                    self._model = None
            return False
        except ImportError as e:
            self._load_error = f"TTS not installed: {e}"
            print(f"[VoiceClone] {self._load_error}")
            return False
        except Exception as e:
            self._load_error = f"Failed to initialize voice cloning: {e}"
            print(f"[VoiceClone] {self._load_error}")
            return False
    
    @property
    def is_available(self) -> bool:
        """Check if voice cloning is available."""
        return self._load_model()
    
    @property
    def error(self) -> Optional[str]:
        """Get last error message."""
        return self._load_error
    
    def create_profile(self, name: str, audio_path: str) -> Optional[VoiceProfile]:
        """Create a new voice profile from reference audio.
        
        Args:
            name: Profile name (e.g., "John's Voice")
            audio_path: Path to reference audio file (6-30 seconds recommended)
        
        Returns:
            VoiceProfile if successful, None otherwise
        """
        if not os.path.exists(audio_path):
            print(f"[VoiceClone] Audio file not found: {audio_path}")
            return None
        
        # Create profile
        profile = VoiceProfile(name=name, audio_path=audio_path)
        
        # Copy audio to profiles directory
        dest_path = self.profiles_dir / f"{profile.profile_id}.wav"
        try:
            import shutil
            shutil.copy2(audio_path, dest_path)
            profile.audio_path = str(dest_path)
        except Exception as e:
            print(f"[VoiceClone] Failed to copy audio: {e}")
            return None
        
        # Save profile
        self.profiles[profile.profile_id] = profile
        self._save_profiles()
        
        print(f"[VoiceClone] Created profile '{name}' with ID {profile.profile_id}")
        return profile
    
    def delete_profile(self, profile_id: str) -> bool:
        """Delete a voice profile."""
        if profile_id not in self.profiles:
            return False
        
        profile = self.profiles[profile_id]
        
        # Remove audio file
        try:
            if os.path.exists(profile.audio_path):
                os.remove(profile.audio_path)
        except Exception as e:
            print(f"[VoiceClone] Failed to remove audio: {e}")
        
        # Remove profile
        del self.profiles[profile_id]
        self._save_profiles()
        
        print(f"[VoiceClone] Deleted profile {profile_id}")
        return True
    
    def get_profile(self, profile_id: str) -> Optional[VoiceProfile]:
        """Get a voice profile by ID."""
        return self.profiles.get(profile_id)
    
    def list_profiles(self) -> List[VoiceProfile]:
        """List all voice profiles."""
        return list(self.profiles.values())
    
    def clone_voice(self, text: str, profile_id: str, output_path: str, 
                   language: str = "en") -> Optional[str]:
        """Generate speech using a cloned voice.
        
        Args:
            text: Text to speak
            profile_id: Voice profile ID to use
            output_path: Path to save generated audio
            language: Language code (en, es, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh, ja, ko, hu, hi)
        
        Returns:
            Path to generated audio file, or None if failed
        """
        if not self._load_model():
            return None
        
        profile = self.profiles.get(profile_id)
        if not profile:
            print(f"[VoiceClone] Profile not found: {profile_id}")
            return None
        
        if not os.path.exists(profile.audio_path):
            print(f"[VoiceClone] Reference audio not found: {profile.audio_path}")
            return None
        
        try:
            wav_path = output_path if output_path.endswith(".wav") else output_path.replace(".mp3", ".wav")
            
            # Generate speech
            self._model.tts_to_file(
                text=text,
                file_path=wav_path,
                speaker_wav=profile.audio_path,
                language=language
            )
            
            print(f"[VoiceClone] Generated speech for '{text[:50]}...' using profile '{profile.name}'")
            return wav_path
        except Exception as e:
            print(f"[VoiceClone] Generation failed: {e}")
            return None
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get supported languages for voice cloning."""
        return [
            {"code": "en", "name": "English"},
            {"code": "es", "name": "Spanish"},
            {"code": "fr", "name": "French"},
            {"code": "de", "name": "German"},
            {"code": "it", "name": "Italian"},
            {"code": "pt", "name": "Portuguese"},
            {"code": "pl", "name": "Polish"},
            {"code": "tr", "name": "Turkish"},
            {"code": "ru", "name": "Russian"},
            {"code": "nl", "name": "Dutch"},
            {"code": "cs", "name": "Czech"},
            {"code": "ar", "name": "Arabic"},
            {"code": "zh", "name": "Chinese"},
            {"code": "ja", "name": "Japanese"},
            {"code": "ko", "name": "Korean"},
            {"code": "hu", "name": "Hungarian"},
            {"code": "hi", "name": "Hindi"},
        ]


# Singleton
voice_cloner = VoiceCloner()
