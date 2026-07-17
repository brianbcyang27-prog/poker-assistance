"""Settings router - Read and update JARVIS configuration."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from jarvis.core.config import get_config

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    nvidia_api_key: Optional[str] = None
    nvidia_model: Optional[str] = None
    default_llm_temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    confidence_threshold: Optional[float] = None
    require_confirmation: Optional[bool] = None
    tts_enabled: Optional[bool] = None
    stt_enabled: Optional[bool] = None
    wake_word_enabled: Optional[bool] = None
    whisper_model: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    view_mode: Optional[str] = None
    chat_mode: Optional[str] = None


def _settings_dict(config) -> dict:
    return {
        "nvidia_api_key": config.nvidia_api_key,
        "nvidia_model": config.nvidia_model,
        "default_llm_temperature": config.default_llm_temperature,
        "max_tokens": config.max_tokens,
        "confidence_threshold": config.confidence_threshold,
        "require_confirmation": config.require_confirmation,
        "tts_enabled": config.tts_enabled,
        "stt_enabled": config.stt_enabled,
        "wake_word_enabled": config.wake_word_enabled,
        "whisper_model": config.whisper_model,
        "host": config.host,
        "port": config.port,
        "view_mode": config.view_mode,
        "chat_mode": config.chat_mode,
    }


@router.get("")
async def get_settings():
    """Get current settings."""
    config = get_config()
    return _settings_dict(config)


@router.post("")
async def update_settings(update: SettingsUpdate):
    """Update settings (persists to .env file)."""
    config = get_config()
    updates = update.model_dump(exclude_none=True)

    # Update in-memory config
    for key, value in updates.items():
        if hasattr(config, key):
            setattr(config, key, value)

    # Persist non-secret settings to .env
    _save_to_env(config)

    return _settings_dict(config)


def _save_to_env(config):
    """Save current settings to .env file."""
    env_path = config.model_config.get("env_file", ".env")

    # Read existing .env to preserve keys we don't manage
    existing = {}
    try:
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    existing[k.strip()] = v.strip()
    except FileNotFoundError:
        pass

    # Update with current config values
    env_map = {
        "NVIDIA_API_KEY": config.nvidia_api_key,
        "NVIDIA_MODEL": config.nvidia_model,
        "LLM_TEMPERATURE": str(config.default_llm_temperature),
        "MAX_TOKENS": str(config.max_tokens),
        "CONFIDENCE_THRESHOLD": str(config.confidence_threshold),
        "REQUIRE_CONFIRMATION": str(config.require_confirmation).lower(),
        "TTS_ENABLED": str(config.tts_enabled).lower(),
        "STT_ENABLED": str(config.stt_enabled).lower(),
        "WAKE_WORD_ENABLED": str(config.wake_word_enabled).lower(),
        "WHISPER_MODEL": config.whisper_model,
        "HOST": config.host,
        "PORT": str(config.port),
        "VIEW_MODE": config.view_mode,
        "CHAT_MODE": config.chat_mode,
    }

    existing.update(env_map)

    with open(env_path, "w") as f:
        for key, value in existing.items():
            f.write(f"{key}={value}\n")
