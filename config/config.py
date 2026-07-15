from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
import os


class Config(BaseSettings):
    """JARVIS configuration settings."""
    
    # NVIDIA API Configuration
    nvidia_api_key: str = Field(..., env="NVIDIA_API_KEY")
    nvidia_model: str = Field(default="meta/llama-8b-instruct", env="NVIDIA_MODEL")
    nvidia_api_base: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        env="NVIDIA_API_BASE"
    )
    
    # Workspace Configuration
    workspace_path: Path = Field(
        default=Path("/Users/brianyang"),
        env="WORKSPACE_PATH"
    )
    
    # Voice Configuration (Phase 3)
    whisper_model: str = Field(default="base", env="WHISPER_MODEL")
    tts_enabled: bool = Field(default=True, env="TTS_ENABLED")
    wake_word_enabled: bool = Field(default=False, env="WAKE_WORD_ENABLED")
    
    # Memory Configuration (Phase 2)
    memory_db_path: Path = Field(
        default=Path("jarvis_memory.db"),
        env="MEMORY_DB_PATH"
    )
    
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
    opencode_command: str = Field(default="opencode", env="OPENCODE_COMMAND")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


_config = None


def get_config() -> Config:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config