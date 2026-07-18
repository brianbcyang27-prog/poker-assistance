"""Vision provider system — pluggable model backends.

Supports:
  - Local: Ollama (LLaVA, Qwen2.5-VL)
  - Cloud: NVIDIA, OpenAI-compatible APIs
"""

import os
import logging
from typing import Optional

from .base import VisionProvider

log = logging.getLogger("jarvis.vision.providers")


def get_vision_provider() -> Optional[VisionProvider]:
    """Load the configured vision provider.

    Configuration via environment variables:
      VISION_PROVIDER=ollama|nvidia|openai
      VISION_MODEL=qwen2.5-vl|llava|...

    Priority:
      1. Ollama (local, if running)
      2. Cloud (if API key configured)
    """
    provider_name = os.environ.get("VISION_PROVIDER", "").lower()

    if provider_name == "ollama":
        from .local import OllamaVisionProvider
        return OllamaVisionProvider()

    if provider_name in ("nvidia", "openai"):
        from .cloud import CloudVisionProvider
        return CloudVisionProvider(provider=provider_name)

    # Auto-detect: try Ollama first, then cloud
    try:
        from .local import OllamaVisionProvider
        p = OllamaVisionProvider()
        if p._check_ollama_sync():
            return p
    except Exception:
        pass

    # Try cloud if API key is set
    nvidia_key = os.environ.get("NVIDIA_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if nvidia_key or openai_key:
        from .cloud import CloudVisionProvider
        provider = "nvidia" if nvidia_key else "openai"
        return CloudVisionProvider(provider=provider)

    log.warning("No vision provider available — vision features disabled")
    return None
