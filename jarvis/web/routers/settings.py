"""Settings router - Read and update JARVIS configuration."""

from fastapi import APIRouter
from pydantic import BaseModel

from jarvis.architectures import (
    get_architecture,
    get_settings_manager,
    list_architectures,
    set_architecture,
)
from jarvis.core.config import get_config
from jarvis.core.permissions import TrinityState, permission_center

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    nvidia_api_key: str | None = None
    nvidia_model: str | None = None
    default_llm_temperature: float | None = None
    max_tokens: int | None = None
    confidence_threshold: float | None = None
    require_confirmation: bool | None = None
    tts_enabled: bool | None = None
    stt_enabled: bool | None = None
    wake_word_enabled: bool | None = None
    whisper_model: str | None = None
    host: str | None = None
    port: int | None = None
    view_mode: str | None = None
    chat_mode: str | None = None
    # Architecture settings
    active_architecture: str | None = None
    arch_planning_depth: int | None = None
    arch_verification_strictness: float | None = None
    arch_auto_reflect: bool | None = None
    arch_skill_extraction: bool | None = None
    arch_memory_retention_days: int | None = None


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
        # Architecture settings
        "active_architecture": config.active_architecture,
        "arch_planning_depth": config.arch_planning_depth,
        "arch_verification_strictness": config.arch_verification_strictness,
        "arch_auto_reflect": config.arch_auto_reflect,
        "arch_skill_extraction": config.arch_skill_extraction,
        "arch_memory_retention_days": config.arch_memory_retention_days,
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
        with open(env_path) as f:
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
        # Architecture settings
        "ACTIVE_ARCHITECTURE": config.active_architecture,
        "ARCH_PLANNING_DEPTH": str(config.arch_planning_depth),
        "ARCH_VERIFICATION_STRICTNESS": str(config.arch_verification_strictness),
        "ARCH_AUTO_REFLECT": str(config.arch_auto_reflect).lower(),
        "ARCH_SKILL_EXTRACTION": str(config.arch_skill_extraction).lower(),
        "ARCH_MEMORY_RETENTION_DAYS": str(config.arch_memory_retention_days),
    }

    existing.update(env_map)

    with open(env_path, "w") as f:
        for key, value in existing.items():
            f.write(f"{key}={value}\n")


# ------------------------------------------------------------------
# Architecture Settings
# ------------------------------------------------------------------


class ArchitectureSettingsUpdate(BaseModel):
    default_architecture: str | None = None
    experimental_mode: bool | None = None
    auto_save_plans: bool | None = None
    auto_reflect: bool | None = None
    verification_required: bool | None = None
    max_plan_steps: int | None = None
    max_execution_time_seconds: int | None = None
    working_memory_limit: int | None = None
    short_term_memory_limit: int | None = None
    long_term_memory_limit: int | None = None
    voice_feedback: bool | None = None
    voice_announce_states: bool | None = None
    show_thought_stream: bool | None = None
    show_mission_progress: bool | None = None
    show_tool_cards: bool | None = None
    show_reasoning: bool | None = None


@router.get("/architecture")
async def get_architecture_settings():
    """Get architecture settings and available architectures."""
    settings_manager = get_settings_manager()
    settings = settings_manager.get()

    architectures = list_architectures()
    current_arch = get_architecture()

    return {
        "architectures": architectures,
        "current": current_arch.name if current_arch else None,
        "settings": {
            "default_architecture": settings.default_architecture,
            "experimental_mode": settings.experimental_mode,
            "auto_save_plans": settings.auto_save_plans,
            "auto_reflect": settings.auto_reflect,
            "verification_required": settings.verification_required,
            "max_plan_steps": settings.max_plan_steps,
            "max_execution_time_seconds": settings.max_execution_time_seconds,
            "working_memory_limit": settings.working_memory_limit,
            "short_term_memory_limit": settings.short_term_memory_limit,
            "long_term_memory_limit": settings.long_term_memory_limit,
            "voice_feedback": settings.voice_feedback,
            "voice_announce_states": settings.voice_announce_states,
            "show_thought_stream": settings.show_thought_stream,
            "show_mission_progress": settings.show_mission_progress,
            "show_tool_cards": settings.show_tool_cards,
            "show_reasoning": settings.show_reasoning,
        },
    }


@router.post("/architecture")
async def update_architecture_settings(update: ArchitectureSettingsUpdate):
    """Update architecture settings."""
    settings_manager = get_settings_manager()
    settings = settings_manager.get()

    updates = update.model_dump(exclude_none=True)

    for key, value in updates.items():
        if hasattr(settings, key):
            setattr(settings, key, value)

    # If default architecture changed, switch to it
    if "default_architecture" in updates:
        new_arch = updates["default_architecture"]
        set_architecture(new_arch)
        settings.default_architecture = new_arch

    settings_manager.save(settings)

    return {"ok": True, "settings": await get_architecture_settings()}


@router.post("/architecture/switch")
async def switch_architecture(arch_name: str):
    """Switch the active architecture."""
    if set_architecture(arch_name):
        return {"ok": True, "message": f"Switched to {arch_name}", "active": arch_name}
    else:
        return {"ok": False, "error": f"Architecture {arch_name} not found"}


# ------------------------------------------------------------------
# Hermes Memory API
# ------------------------------------------------------------------


@router.get("/hermes/memory")
async def get_hermes_memory(mission_id: str):
    """Get memory state for a Hermes architecture mission."""
    arch = get_architecture()
    if (
        arch
        and arch.name == "Hermes"
        and hasattr(arch, "_current_context")
        and arch._current_context
    ):
        context = arch._current_context
        return {
            "working_memory": context.working_memory,
            "episodic_memory": context.episodic_memory,
            "semantic_memory": context.semantic_memory,
            "skills": context.skills,
        }
    return {"working_memory": {}, "episodic_memory": [], "semantic_memory": {}, "skills": {}}


# ------------------------------------------------------------------
# Permissions
# ------------------------------------------------------------------


@router.get("/permissions")
async def get_permissions():
    """Get all permission states."""
    return {"permissions": permission_center.get_all()}


class PermissionUpdate(BaseModel):
    name: str
    enabled: bool | None = None
    state: str | None = None  # "allow" | "ask" | "deny"


@router.post("/permissions")
async def update_permission(update: PermissionUpdate):
    """Update a permission state."""
    if update.state is not None:
        try:
            trinity_state = TrinityState(update.state)
        except ValueError:
            return {
                "ok": False,
                "error": f"Invalid state: {update.state}. Use allow, ask, or deny.",
            }
        ok = permission_center.set_state(update.name, trinity_state)
    elif update.enabled is not None:
        ok = permission_center.set(update.name, update.enabled)
    else:
        return {"ok": False, "error": "Provide 'state' (allow/ask/deny) or 'enabled' (true/false)"}
    if not ok:
        return {"ok": False, "error": f"Unknown permission: {update.name}"}
    return {"ok": True, "name": update.name, "state": permission_center.get(update.name)}
