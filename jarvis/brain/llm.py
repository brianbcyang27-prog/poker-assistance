"""Unified LLM interface for JARVIS (v6.1.0).

Uses httpx directly instead of the openai library to avoid dependency issues.
NVIDIA API is OpenAI-compatible, so we hit /chat/completions directly.
Timeouts and retries are configurable via jarvis.core.reliability.
"""

import asyncio
import json
import logging
import subprocess
import threading

import httpx

from ..core.config import get_config

logger = logging.getLogger(__name__)


class LLM:
    """LLM interface supporting NVIDIA API with Ollama fallback.

    Each agent can override model/api_base for different LLMs per subagent.
    """

    def __init__(
        self,
        model: str | None = None,
        api_base: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
    ):
        config = get_config()

        try:
            from ..core.reliability import config as reliability

            self._timeout = timeout or reliability.llm_timeout
            self._max_retries = reliability.max_retries
            self._retry_base_delay = reliability.retry_base_delay
            self._retry_max_delay = reliability.retry_max_delay
            self._retry_backoff = reliability.retry_backoff_factor
        except ImportError:
            self._timeout = timeout or 60.0
            self._max_retries = 3
            self._retry_base_delay = 1.0
            self._retry_max_delay = 30.0
            self._retry_backoff = 2.0

        self.api_key = api_key or config.nvidia_api_key
        self.api_base = (api_base or config.nvidia_api_base).rstrip("/")
        self.nvidia_model = model or config.nvidia_model

        self.ollama_base = "http://localhost:11434/v1"
        self.ollama_model = "llama3.2"
        self._ollama_available = False
        self._initialized = False
        self._init_lock = threading.Lock()

        self.use_nvidia = bool(self.api_key)
        self.conversation_history: list[dict] = []
        self._history_lock = asyncio.Lock()
        self._current_session_id: str | None = None

        self._http = httpx.Client(timeout=self._timeout)
        self._async_http: httpx.AsyncClient | None = None

    async def _get_async_http(self) -> httpx.AsyncClient:
        """Get or create async httpx client."""
        if self._async_http is None or self._async_http.is_closed:
            self._async_http = httpx.AsyncClient(timeout=self._timeout)
        return self._async_http

    def _init_ollama(self):
        """Initialize Ollama client if available."""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            self._ollama_available = result.returncode == 0
        except Exception:
            self._ollama_available = False

    def _ensure_initialized(self):
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._init_ollama()
            self._initialized = True

    def is_available(self) -> bool:
        """Check if an LLM backend is available."""
        self._ensure_initialized()
        return bool(self.api_key) or self._ollama_available

    def close(self) -> None:
        """Close the httpx clients to release connections."""
        if self._http:
            try:
                self._http.close()
            except Exception:
                pass
        # Note: async client should be closed with aclose() from async context
        # The __del__ fallback is best-effort only

    def __del__(self):
        self.close()

    def _get_endpoint(self) -> tuple[str, str, str]:
        """Returns (base_url, api_key, model)."""
        self._ensure_initialized()
        if not hasattr(self, "_timed_first_ai"):
            self._timed_first_ai = True
            try:
                from jarvis.core.startup_timer import startup_timer

                startup_timer.mark("first_ai")
            except Exception:
                pass
        if self.use_nvidia:
            return self.api_base, self.api_key, self.nvidia_model
        elif self._ollama_available:
            return self.ollama_base, "ollama", self.ollama_model
        else:
            raise RuntimeError("No LLM backend available. Set NVIDIA_API_KEY or install Ollama.")

    def _chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        base_url: str,
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Call /chat/completions endpoint with retry logic."""
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._http.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code >= 500 and attempt < self._max_retries:
                    delay = min(
                        self._retry_base_delay * (self._retry_backoff**attempt),
                        self._retry_max_delay,
                    )
                    logger.warning(
                        f"LLM HTTP {e.response.status_code}, retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{self._max_retries})"
                    )
                    import time as _time

                    _time.sleep(delay)
                    continue
                raise
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                last_error = e
                if attempt < self._max_retries:
                    delay = min(
                        self._retry_base_delay * (self._retry_backoff**attempt),
                        self._retry_max_delay,
                    )
                    logger.warning(
                        f"LLM connection error: {e}, retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{self._max_retries})"
                    )
                    import time as _time

                    _time.sleep(delay)
                    continue
                raise

        raise last_error or RuntimeError("LLM request failed after retries")

    async def _achat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        base_url: str,
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Async call /chat/completions endpoint with retry logic."""
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        client = await self._get_async_http()
        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code >= 500 and attempt < self._max_retries:
                    delay = min(
                        self._retry_base_delay * (self._retry_backoff**attempt),
                        self._retry_max_delay,
                    )
                    logger.warning(
                        f"LLM HTTP {e.response.status_code}, retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{self._max_retries})"
                    )
                    await asyncio.sleep(delay)
                    continue
                raise
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                last_error = e
                if attempt < self._max_retries:
                    delay = min(
                        self._retry_base_delay * (self._retry_backoff**attempt),
                        self._retry_max_delay,
                    )
                    logger.warning(
                        f"LLM connection error: {e}, retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{self._max_retries})"
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

        raise last_error or RuntimeError("LLM request failed after retries")

    async def achat(
        self,
        message: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Async send a message and get a response."""
        try:
            from .privacy import scrubber

            message = scrubber.scrub(message)
        except Exception:
            pass

        base_url, api_key, model = self._get_endpoint()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(self.conversation_history[-10:])
        messages.append({"role": "user", "content": message})

        assistant_message = await self._achat_completion(
            messages=messages,
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        async with self._history_lock:
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": assistant_message})

            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

        # Compact context if history is getting long
        await self._compact_context()

        return assistant_message

    async def _compact_context(self) -> None:
        """Compact conversation context by summarizing old messages.

        When history exceeds 15 messages, summarize the older messages
        into a single system message to preserve context while freeing space.
        """
        async with self._history_lock:
            if len(self.conversation_history) <= 15:
                return

            # Keep last 6 messages intact, summarize the rest
            to_summarize = self.conversation_history[:-6]
            keep = self.conversation_history[-6:]

            # Build a summary prompt
            summary_messages = [
                {
                    "role": "system",
                    "content": (
                        "Summarize this conversation into 2-3 sentences capturing key decisions, "
                        "facts, and context. Be concise."
                    ),
                },
                {"role": "user", "content": json.dumps(to_summarize, default=str)[:4000]},
            ]

            try:
                base_url, api_key, model = self._get_endpoint()
                summary = await self._achat_completion(
                    messages=summary_messages,
                    model=model,
                    base_url=base_url,
                    api_key=api_key,
                    temperature=0.3,
                    max_tokens=200,
                )
                # Replace old messages with summary
                self.conversation_history = [
                    {"role": "system", "content": f"[Conversation Summary] {summary}"}
                ] + keep
                logger.info(
                    "Compacted context: %d messages → summary + %d messages",
                    len(to_summarize),
                    len(keep),
                )
            except Exception as e:
                # If compaction fails, just truncate
                self.conversation_history = keep
                logger.warning("Context compaction failed, truncated instead: %s", e)

    def switch_to_ollama(self):
        """Switch to Ollama backend."""
        self._ensure_initialized()
        if self._ollama_available:
            self.use_nvidia = False
        else:
            raise RuntimeError("Ollama not available")

    def switch_to_nvidia(self):
        """Switch to NVIDIA backend."""
        self.use_nvidia = True

    async def load_session_context(self, session_id: str):
        """Load conversation context from database for a session."""
        if self._current_session_id == session_id:
            return

        try:
            from ..core.database import get_db

            db = await get_db()
            context = await db.get_llm_context(session_id)
            if context:
                async with self._history_lock:
                    self.conversation_history = context
                    self._current_session_id = session_id
        except Exception as e:
            logger.warning("Failed to load session context for %s: %s", session_id, e)

    async def save_session_context(self, session_id: str):
        """Save conversation context to database."""
        try:
            from ..core.database import get_db

            db = await get_db()
            await db.save_llm_context(session_id, self.conversation_history)
            self._current_session_id = session_id
        except Exception:
            pass

    def chat(
        self,
        message: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Send a message and get a response."""
        # Scrub PII before sending to external API
        try:
            from .privacy import scrubber

            message = scrubber.scrub(message)
        except Exception:
            pass

        base_url, api_key, model = self._get_endpoint()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(self.conversation_history[-10:])
        messages.append({"role": "user", "content": message})

        assistant_message = self._chat_completion(
            messages=messages,
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        self.conversation_history.append({"role": "user", "content": message})
        self.conversation_history.append({"role": "assistant", "content": assistant_message})

        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        return assistant_message

    def chat_json(
        self,
        message: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict:
        """Send a message and parse the response as JSON."""
        response = self.chat(
            message=message,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Try markdown code blocks first
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
        except (json.JSONDecodeError, IndexError):
            pass

        # Try to find JSON object in the response using regex
        try:
            # Find the outermost { ... } block
            depth = 0
            start = -1
            for i, ch in enumerate(response):
                if ch == "{":
                    if depth == 0:
                        start = i
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0 and start >= 0:
                        candidate = response[start : i + 1]
                        return json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            pass

        # Try to find JSON array
        try:
            depth = 0
            start = -1
            for i, ch in enumerate(response):
                if ch == "[":
                    if depth == 0:
                        start = i
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0 and start >= 0:
                        candidate = response[start : i + 1]
                        return json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            pass

        # Last resort: strip everything before first { and after last }
        try:
            first_brace = response.find("{")
            last_brace = response.rfind("}")
            if first_brace >= 0 and last_brace > first_brace:
                return json.loads(response[first_brace : last_brace + 1])
        except (json.JSONDecodeError, ValueError):
            pass

        return {"raw_response": response, "parse_error": True}

    def _build_messages(
        self,
        message: str,
        system_prompt: str | None = None,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(self.conversation_history[-10:])
        messages.append({"role": "user", "content": message})
        return messages

    def _chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        model: str,
        base_url: str,
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """Yield SSE tokens from /chat/completions via httpx streaming."""
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        with self._http.stream("POST", url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                # SSE lines are prefixed with "data: "
                if line.startswith("data: "):
                    line = line[6:]
                if line.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(line)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

    async def _achat_completion_stream(
        self,
        messages: list[dict[str, str]],
        model: str,
        base_url: str,
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """Async yield SSE tokens from /chat/completions via httpx streaming."""
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    if line.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(line)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    def chat_stream(
        self,
        message: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """Yield response tokens one by one as they arrive from the LLM."""
        try:
            from .privacy import scrubber

            message = scrubber.scrub(message)
        except Exception:
            pass

        base_url, api_key, model = self._get_endpoint()
        messages = self._build_messages(message, system_prompt)

        full_response: list[str] = []
        for token in self._chat_completion_stream(
            messages=messages,
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            full_response.append(token)
            yield token

        # Persist to conversation history after stream completes
        self.conversation_history.append({"role": "user", "content": message})
        self.conversation_history.append({"role": "assistant", "content": "".join(full_response)})
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

    async def achat_stream(
        self,
        message: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """Async yield response tokens one by one as they arrive from the LLM."""
        try:
            from .privacy import scrubber

            message = scrubber.scrub(message)
        except Exception:
            pass

        base_url, api_key, model = self._get_endpoint()
        messages = self._build_messages(message, system_prompt)

        full_response: list[str] = []
        async for token in self._achat_completion_stream(
            messages=messages,
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            full_response.append(token)
            yield token

        self.conversation_history.append({"role": "user", "content": message})
        self.conversation_history.append({"role": "assistant", "content": "".join(full_response)})
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
        self._current_session_id = None

    def set_history(self, history: list[dict]):
        """Set the conversation history."""
        self.conversation_history = history
