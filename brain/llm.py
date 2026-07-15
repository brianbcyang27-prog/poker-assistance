from openai import OpenAI
from typing import Optional
import json
import subprocess

from ..config import get_config


class LLM:
    """LLM interface supporting NVIDIA API with Ollama fallback."""
    
    def __init__(self):
        config = get_config()
        
        self.nvidia_client = OpenAI(
            base_url=config.nvidia_api_base,
            api_key=config.nvidia_api_key,
        )
        self.nvidia_model = config.nvidia_model
        
        self.ollama_client = None
        self.ollama_model = "llama3.2"
        self._init_ollama()
        
        self.use_nvidia = True
        self.conversation_history: list[dict] = []
    
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
        if self.use_nvidia:
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
    
    def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Send a message and get a response."""
        client, model = self._get_client()
        
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.extend(self.conversation_history)
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
        
        return assistant_message
    
    def chat_json(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
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
    
    def set_history(self, history: list[dict]):
        """Set the conversation history."""
        self.conversation_history = history
    
    def get_system_prompt(self) -> str:
        """Get the default JARVIS system prompt."""
        return """You are JARVIS, an advanced AI assistant inspired by Iron Man's JARVIS.

Your capabilities:
1. Understanding and planning complex tasks
2. Delegating work to specialized agents (like OpenCode for coding)
3. Managing software projects
4. Providing natural, helpful responses

Your personality:
- Professional and efficient
- Slightly witty but not overly casual
- Proactive in suggesting solutions
- Clear and concise in communication

When the user asks you to perform tasks:
1. Break down complex requests into clear, actionable steps
2. Create structured task lists
3. Identify which tasks should be delegated to workers (like OpenCode)
4. Track progress and report back

Always prioritize safety:
- Ask before deleting files
- Ask before installing software
- Ask before making destructive changes
- Ask before publishing releases

You are speaking with Brian Yang, your creator. Be helpful and efficient."""
    
    def plan_task(self, user_request: str) -> dict:
        """Use the LLM to create a structured task plan."""
        system_prompt = """You are JARVIS task planner. Convert user requests into structured task plans.

Respond with JSON only. Use this format:
{
    "tasks": [
        {
            "id": 1,
            "name": "Task name",
            "description": "What needs to be done",
            "type": "code|document|test|deploy|research",
            "priority": "high|medium|low",
            "agent": "opencode|user",
            "estimated_time": "5 minutes",
            "dependencies": []
        }
    ],
    "summary": "Brief summary of what will be done",
    "estimated_total": "Total estimated time"
}

Be specific and actionable. Consider dependencies between tasks."""
        
        response = self.chat_json(
            message=f"Create a task plan for: {user_request}",
            system_prompt=system_prompt,
        )
        
        return response