"""Cloud vision provider — NVIDIA and OpenAI-compatible APIs.

Supports:
  - NVIDIA vision models (via build.nvidia.com)
  - OpenAI-compatible APIs (GPT-4V, etc.)
"""

import asyncio
import json
import logging
import os
import time
import base64
from typing import Optional

from .base import VisionProvider, VisionResult, DetectedObject

log = logging.getLogger("jarvis.vision.providers.cloud")


class CloudVisionProvider(VisionProvider):
    """Cloud vision provider for NVIDIA and OpenAI-compatible APIs.

    Configuration:
      NVIDIA_API_KEY=... or OPENAI_API_KEY=...
      VISION_MODEL=qwen2.5-vl-7b-instruct or gpt-4o
      VISION_PROVIDER=nvidia or openai

    Supports any OpenAI-compatible vision API endpoint.
    """

    NVIDIA_BASE = "https://integrate.api.nvidia.com/v1"
    OPENAI_BASE = "https://api.openai.com/v1"

    def __init__(self, provider: str = ""):
        self._provider_name = provider or os.environ.get("VISION_PROVIDER", "nvidia")
        self._api_key = ""
        self._base_url = ""
        self._model = ""
        self._initialized = False

        if self._provider_name == "nvidia":
            self._api_key = os.environ.get("NVIDIA_API_KEY", "")
            self._base_url = os.environ.get("NVIDIA_API_BASE", self.NVIDIA_BASE)
            self._model = os.environ.get("VISION_MODEL", "qwen2.5-vl-7b-instruct")
        elif self._provider_name == "openai":
            self._api_key = os.environ.get("OPENAI_API_KEY", "")
            self._base_url = os.environ.get("OPENAI_API_BASE", self.OPENAI_BASE)
            self._model = os.environ.get("VISION_MODEL", "gpt-4o")
        else:
            # Generic OpenAI-compatible
            self._api_key = os.environ.get("VISION_API_KEY", "")
            self._base_url = os.environ.get("VISION_API_BASE", self.OPENAI_BASE)
            self._model = os.environ.get("VISION_MODEL", "gpt-4o")

    @property
    def name(self) -> str:
        return self._provider_name

    @property
    def model(self) -> str:
        return self._model

    async def initialize(self) -> dict:
        """Verify API key and model availability."""
        if self._initialized:
            return {"ok": True, "provider": self.name, "model": self._model}

        if not self._api_key:
            return {
                "ok": False,
                "error": f"No API key for {self._provider_name}. "
                         f"Set {'NVIDIA_API_KEY' if self._provider_name == 'nvidia' else 'OPENAI_API_KEY'}.",
            }

        self._initialized = True
        return {
            "ok": True,
            "provider": self.name,
            "model": self._model,
            "base_url": self._base_url,
        }

    async def _call_api(self, messages: list) -> dict:
        """Call the vision API via curl (no httpx dependency)."""
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.1,
        }

        payload_json = json.dumps(payload)
        auth_header = f"Bearer {self._api_key}"

        proc = await asyncio.create_subprocess_exec(
            "curl", "-s", "-X", "POST",
            f"{self._base_url}/chat/completions",
            "-H", "Content-Type: application/json",
            "-H", f"Authorization: {auth_header}",
            "-d", payload_json,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        return json.loads(stdout.decode())

    async def analyze_image(
        self,
        image_path: str = "",
        image_base64: str = "",
        prompt: str = "",
    ) -> VisionResult:
        """Analyze an image using cloud vision model."""
        start = time.time()

        if not image_base64 and image_path:
            try:
                with open(image_path, "rb") as f:
                    image_base64 = base64.b64encode(f.read()).decode()
            except Exception as e:
                return VisionResult(
                    success=False, error=f"Failed to read image: {e}",
                    provider=self.name, model=self._model,
                )

        if not image_base64:
            return VisionResult(
                success=False, error="No image provided",
                provider=self.name, model=self._model,
            )

        prompt = prompt or (
            "Analyze this screenshot. Return a JSON object with:\n"
            '1. "application": the app name\n'
            '2. "description": brief description of what\'s on screen\n'
            '3. "objects": array of UI elements with type, name, x, y, width, height, confidence\n'
            '4. "text": any visible text\n'
            '5. "layout": layout structure description\n'
            "Return ONLY valid JSON, no markdown."
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}",
                        },
                    },
                ],
            }
        ]

        try:
            response = await self._call_api(messages)
            duration = (time.time() - start) * 1000

            choices = response.get("choices", [])
            if choices:
                raw_text = choices[0].get("message", {}).get("content", "")
                return self._parse_response(raw_text, duration)

            error = response.get("error", {})
            return VisionResult(
                success=False,
                error=error.get("message", str(response)),
                provider=self.name, model=self._model,
                duration_ms=duration,
            )

        except asyncio.TimeoutError:
            return VisionResult(
                success=False, error="Cloud API request timed out",
                provider=self.name, model=self._model,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return VisionResult(
                success=False, error=str(e),
                provider=self.name, model=self._model,
                duration_ms=(time.time() - start) * 1000,
            )

    async def describe_screen(self, image_path: str = "") -> str:
        """Get a natural language description of the screen."""
        result = await self.analyze_image(
            image_path=image_path,
            prompt="Describe what you see on this screen in 2-3 sentences. "
                   "Include the application name, main content, and any notable UI elements.",
        )
        return result.screen_description or result.raw_response

    async def find_in_image(self, image_path: str = "", query: str = "") -> list:
        """Find specific objects in an image."""
        result = await self.analyze_image(
            image_path=image_path,
            prompt=f'Find all UI elements matching "{query}" in this screenshot. '
                   "Return a JSON array of objects with type, name, x, y, width, height, confidence. "
                   "Return ONLY the JSON array, no markdown.",
        )
        return result.objects

    async def health_check(self) -> dict:
        """Check API availability."""
        if not self._api_key:
            return {"ok": False, "error": "No API key configured"}
        return {
            "ok": True,
            "provider": self.name,
            "model": self._model,
            "base_url": self._base_url,
        }

    def _parse_response(self, raw_text: str, duration_ms: float) -> VisionResult:
        """Parse model response into VisionResult."""
        result = VisionResult(
            raw_response=raw_text,
            provider=self.name,
            model=self._model,
            duration_ms=duration_ms,
        )

        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    result.screen_description = raw_text[:500]
                    return result
            else:
                result.screen_description = raw_text[:500]
                return result

        result.application = data.get("application", "")
        result.screen_description = data.get("description", "")
        result.text_content = data.get("text", "")
        result.layout = data.get("layout", {})

        objects_raw = data.get("objects", [])
        if isinstance(objects_raw, list):
            for obj in objects_raw:
                if isinstance(obj, dict):
                    result.objects.append(DetectedObject(
                        type=obj.get("type", "unknown"),
                        name=obj.get("name", ""),
                        x=int(obj.get("x", 0)),
                        y=int(obj.get("y", 0)),
                        width=int(obj.get("width", 0)),
                        height=int(obj.get("height", 0)),
                        confidence=float(obj.get("confidence", 0.5)),
                        description=obj.get("description", ""),
                        color=obj.get("color", ""),
                        state=obj.get("state", ""),
                    ))

        return result
