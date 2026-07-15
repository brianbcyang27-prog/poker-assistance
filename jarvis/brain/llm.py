"""Unified LLM interface for JARVIS."""

from openai import OpenAI
from typing import Optional
import json
import subprocess

from ..core.config import get_config


class LLM:
    """LLM interface supporting NVIDIA API with Ollama fallback."""
    
    def __init__(self):
        config = get_config()
        
        self.nvidia_client = None
        if config.nvidia_api_key:
            self.nvidia_client = OpenAI(
                base_url=config.nvidia_api_base,
                api_key=config.nvidia_api_key,
            )
        self.nvidia_model = config.nvidia_model
        
        self.ollama_client = None
        self.ollama_model = "llama3.2"
        self._init_ollama()
        
        self.use_nvidia = bool(config.nvidia_api_key)
        self.conversation_history: list[dict] = []
        self._current_session_id: Optional[str] = None
    
    def _init_ollama(self):
        """Initialize Ollama client if available."""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                self.ollama_client = OpenAI(
                    base_url="http://localhost:11434/v1",
                    api_key="ollama",
                )
        except Exception:
            self.ollama_client = None
    
    def _get_client(self):
        """Get the appropriate client."""
        if self.use_nvidia and self.nvidia_client:
            return self.nvidia_client, self.nvidia_model
        elif self.ollama_client:
            return self.ollama_client, self.ollama_model
        else:
            raise RuntimeError("No LLM backend available. Set NVIDIA_API_KEY or install Ollama.")
    
    def switch_to_ollama(self):
        """Switch to Ollama backend."""
        if self.ollama_client:
            self.use_nvidia = False
        else:
            raise RuntimeError("Ollama not available")
    
    def switch_to_nvidia(self):
        """Switch to NVIDIA backend."""
        self.use_nvidia = True
    
    async def load_session_context(self, session_id: str):
        """Load conversation context from database for a session."""
        if self._current_session_id == session_id:
            return  # Already loaded
        
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
        client, model = self._get_client()
        
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.extend(self.conversation_history[-10:])  # Keep last 10 messages
        messages.append({"role": "user", "content": message})
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        assistant_message = response.choices[0].message.content
        
        self.conversation_history.append({"role": "user", "content": message})
        self.conversation_history.append({"role": "assistant", "content": assistant_message})
        
        # Keep history manageable
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
    
    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
        self._current_session_id = None
    
    def set_history(self, history: list[dict]):
        """Set the conversation history."""
        self.conversation_history = history
