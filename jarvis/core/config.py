"""Unified configuration for JARVIS."""

from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Config(BaseSettings):
    """JARVIS configuration settings."""
    
    # NVIDIA API Configuration
    nvidia_api_key: str = Field(default="", env="NVIDIA_API_KEY")
    nvidia_model: str = Field(default="meta/llama-8b-instruct", env="NVIDIA_MODEL")
    nvidia_api_base: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        env="NVIDIA_API_BASE"
    )
    
    # OpenCode Configuration
    opencode_model: str = Field(default="opencode/big-pickle", env="OPENCODE_MODEL")
    opencode_binary: str = Field(
        default="/Users/brianyang/.opencode/bin/opencode",
        env="OPENCODE_BINARY"
    )
    
    # Workspace Configuration
    workspace_path: Path = Field(
        default=Path("/Users/brianyang"),
        env="WORKSPACE_PATH"
    )
    
    # Web Server Configuration
    host: str = Field(default="127.0.0.1", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Voice Configuration
    whisper_model: str = Field(default="base", env="WHISPER_MODEL")
    tts_enabled: bool = Field(default=True, env="TTS_ENABLED")
    stt_enabled: bool = Field(default=True, env="STT_ENABLED")
    wake_word_enabled: bool = Field(default=False, env="WAKE_WORD_ENABLED")
    tts_provider: str = Field(default="macos", env="TTS_PROVIDER")  # macos|kokoro|openai|piper
    tts_voice: str = Field(default="", env="TTS_VOICE")  # Voice ID for the provider
    tts_model: str = Field(default="tts-1", env="TTS_MODEL")  # Model for cloud providers
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")  # For OpenAI TTS
    
    # Memory Configuration
    db_path: Path = Field(default=Path("jarvis.db"), env="DB_PATH")
    
    # Safety Configuration
    require_confirmation: bool = Field(default=True, env="REQUIRE_CONFIRMATION")
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
        ],
        env="DANGEROUS_COMMANDS"
    )
    
    # Agent Configuration
    default_llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    max_tokens: int = Field(default=4096, env="MAX_TOKENS")
    confidence_threshold: float = Field(default=0.9, env="CONFIDENCE_THRESHOLD")

    # UI Configuration
    view_mode: str = Field(default="graph", env="VIEW_MODE")  # core|graph
    chat_mode: str = Field(default="popup", env="CHAT_MODE")  # popup|chat
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


_config = None


def get_config() -> Config:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
