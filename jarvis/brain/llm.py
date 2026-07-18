"""Unified LLM interface for JARVIS.

Uses httpx directly instead of the openai library to avoid dependency issues.
NVIDIA API is OpenAI-compatible, so we hit /chat/completions directly.
"""

import json
import subprocess
import httpx
from typing import Optional, Dict, Any, List

from ..core.config import get_config


class LLM:
    """LLM interface supporting NVIDIA API with Ollama fallback.
    
    Each agent can override model/api_base for different LLMs per subagent.
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        config = get_config()
        
        self.api_key = api_key or config.nvidia_api_key
        self.api_base = (api_base or config.nvidia_api_base).rstrip("/")
        self.nvidia_model = model or config.nvidia_model
        
        self.ollama_base = "http://localhost:11434/v1"
        self.ollama_model = "llama3.2"
        self._ollama_available = False
        self._init_ollama()
        
        self.use_nvidia = bool(self.api_key)
        self.conversation_history: list[dict] = []
        self._current_session_id: Optional[str] = None
        
        self._http = httpx.Client(timeout=60.0)
    
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
    
    def is_available(self) -> bool:
        """Check if an LLM backend is available."""
        return bool(self.api_key) or self._ollama_available
    
    def _get_endpoint(self) -> tuple[str, str, str]:
        """Returns (base_url, api_key, model)."""
        if self.use_nvidia:
            return self.api_base, self.api_key, self.nvidia_model
        elif self._ollama_available:
            return self.ollama_base, "ollama", self.ollama_model
        else:
            raise RuntimeError("No LLM backend available. Set NVIDIA_API_KEY or install Ollama.")
    
    def _chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        base_url: str,
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Call /chat/completions endpoint via httpx."""
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
        
        response = self._http.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    def switch_to_ollama(self):
        """Switch to Ollama backend."""
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
                self.conversation_history = context
                self._current_session_id = session_id
        except Exception:
            pass
    
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
        system_prompt: Optional[str] = None,
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
        system_prompt: Optional[str] = None,
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
        
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {"raw_response": response, "parse_error": True}
    
    def _build_messages(
        self,
        message: str,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(self.conversation_history[-10:])
        messages.append({"role": "user", "content": message})
        return messages

    def _chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
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
        messages: List[Dict[str, str]],
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

        async with httpx.AsyncClient(timeout=60.0) as client:
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
        system_prompt: Optional[str] = None,
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

        full_response: List[str] = []
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
        system_prompt: Optional[str] = None,
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

        full_response: List[str] = []
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
