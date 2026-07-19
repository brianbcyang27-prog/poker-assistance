"""Local vision provider — Ollama.

Supports vision models via Ollama's API:
  - qwen2.5-vl (recommended)
  - llava
  - llava-llama3
  - minicpm-v

Requires Ollama running locally (default: http://localhost:11434).
"""

import asyncio
import json
import logging
import time

from jarvis.core.reliability import config as reliability_config
from typing import Optional, List

from .base import VisionProvider, VisionResult, DetectedObject

log = logging.getLogger("jarvis.vision.providers.local")


class OllamaVisionProvider(VisionProvider):
    """Ollama local vision provider.

    Uses Ollama's /api/generate endpoint with vision models.
    No external API keys needed — runs entirely on local hardware.

    Configuration:
      OLLAMA_HOST=http://localhost:11434
      VISION_MODEL=qwen2.5-vl
    """

    def __init__(self, host: str = ""):
        import os
        self._host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self._model = os.environ.get("VISION_MODEL", "qwen2.5-vl")
        self._initialized = False

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    def _check_ollama_sync(self) -> bool:
        """Quick synchronous check if Ollama is reachable."""
        import urllib.request
        try:
            req = urllib.request.Request(f"{self._host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def initialize(self) -> dict:
        """Verify Ollama is running and model is available."""
        if self._initialized:
            return {"ok": True, "provider": self.name, "model": self._model}

        try:
            proc = await asyncio.create_subprocess_exec(
                "curl", "-s", f"{self._host}/api/tags",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=reliability_config.ws_timeout)
            data = json.loads(stdout.decode())

            models = [m.get("name", "") for m in data.get("models", [])]
            model_available = any(self._model in m for m in models)

            if not model_available:
                log.warning(
                    "Model '%s' not found in Ollama. Available: %s. "
                    "Run: ollama pull %s",
                    self._model, models, self._model,
                )

            self._initialized = True
            return {
                "ok": True,
                "provider": self.name,
                "model": self._model,
                "models_available": models,
                "model_found": model_available,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def analyze_image(
        self,
        image_path: str = "",
        image_base64: str = "",
        prompt: str = "",
    ) -> VisionResult:
        """Analyze an image using Ollama vision model."""
        start = time.time()

        if not image_base64 and image_path:
            import base64
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

        payload = {
            "model": self._model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 2048,
            },
        }

        try:
            payload_json = json.dumps(payload)
            proc = await asyncio.create_subprocess_exec(
                "curl", "-s", "-X", "POST",
                f"{self._host}/api/generate",
                "-H", "Content-Type: application/json",
                "-d", payload_json,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=reliability_config.llm_timeout)
            response = json.loads(stdout.decode())
            raw_text = response.get("response", "")

            duration = (time.time() - start) * 1000
            return self._parse_response(raw_text, duration)

        except asyncio.TimeoutError:
            return VisionResult(
                success=False, error="Ollama request timed out",
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
        """Check Ollama health."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "curl", "-s", f"{self._host}/api/tags",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=reliability_config.health_check_timeout)
            data = json.loads(stdout.decode())
            models = [m.get("name", "") for m in data.get("models", [])]
            return {
                "ok": True,
                "provider": self.name,
                "model": self._model,
                "models": models,
                "host": self._host,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _parse_response(self, raw_text: str, duration_ms: float) -> VisionResult:
        """Parse the model's response into a VisionResult."""
        result = VisionResult(
            raw_response=raw_text,
            provider=self.name,
            model=self._model,
            duration_ms=duration_ms,
        )

        # Try to extract JSON from the response
        text = raw_text.strip()
        # Remove markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON in the response
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

        # Parse detected objects
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
