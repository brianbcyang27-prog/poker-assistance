"""Unified configuration for JARVIS."""

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


def _secret(key: str, default: str = "") -> str:
    """Resolve a secret via SecretManager, falling back to env var."""
    try:
        from jarvis.security import get_secret

        value = get_secret(key)
        if value:
            return value
    except Exception:
        pass
    return os.environ.get(key, default)


class Config(BaseSettings):
    """JARVIS configuration settings."""

    # NVIDIA API Configuration
    nvidia_api_key: str = Field(default="")
    nvidia_model: str = Field(default="meta/llama-8b-instruct")
    nvidia_api_base: str = Field(default="https://integrate.api.nvidia.com/v1")

    # OpenCode Configuration
    opencode_model: str = Field(default="opencode/big-pickle")
    opencode_binary: str = Field(default="/Users/brianyang/.opencode/bin/opencode")

    # Workspace Configuration
    workspace_path: Path = Field(default=Path("/Users/brianyang"))

    # Web Server Configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # Voice Configuration
    whisper_model: str = Field(default="base")
    tts_enabled: bool = Field(default=True)
    stt_enabled: bool = Field(default=True)
    wake_word_enabled: bool = Field(default=False)
    tts_provider: str = Field(default="macos")  # macos|kokoro|openai|piper
    tts_voice: str = Field(default="")  # Voice ID for the provider
    tts_model: str = Field(default="tts-1")  # Model for cloud providers
    openai_api_key: str = Field(default="")  # For OpenAI TTS

    # Memory Configuration
    db_path: Path = Field(default=Path("jarvis.db"))

    # Safety Configuration
    require_confirmation: bool = Field(default=True)
    dangerous_commands: list[str] = Field(
        default=[
            "rm -rf",
            "sudo",
            "chmod 777",
            "curl | sh",
            "wget | sh",
            "format",
            "mkfs",
            "dd",
        ]
    )

    # Agent Configuration
    default_llm_temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=4096)
    confidence_threshold: float = Field(default=0.9)

    # UI Configuration
    view_mode: str = Field(default="graph")  # core|graph
    chat_mode: str = Field(default="popup")  # popup|chat

    # Logging Configuration
    log_level: str = Field(default="INFO")
    log_dir: str = Field(default="")
    log_json_file: bool = Field(default=True)
    log_json_max_bytes: int = Field(default=10 * 1024 * 1024)
    log_json_backup_count: int = Field(default=5)
    log_console: bool = Field(default=True)

    # Architecture Configuration
    active_architecture: str = Field(default="jarvis_native")
    arch_planning_depth: int = Field(default=2)
    arch_verification_strictness: float = Field(default=0.8)
    arch_auto_reflect: bool = Field(default=True)
    arch_skill_extraction: bool = Field(default=True)
    arch_memory_retention_days: int = Field(default=30)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    def model_post_init(self, __context) -> None:
        """Resolve secrets via SecretManager after pydantic init."""
        self.nvidia_api_key = _secret("NVIDIA_API_KEY", self.nvidia_api_key)
        self.openai_api_key = _secret("OPENAI_API_KEY", self.openai_api_key)


_config = None


def get_config() -> Config:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
