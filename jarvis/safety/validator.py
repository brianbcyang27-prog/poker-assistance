"""Safety validator for JARVIS operations."""

import re
from typing import Optional

from ..core.config import get_config


class SafetyValidator:
    """Validates operations for safety concerns."""
    
    def __init__(self):
        self._config = get_config()
    
    def is_dangerous(self, command: str) -> bool:
        """Check if a command is potentially dangerous."""
        command_lower = command.lower().strip()
        
        for dangerous in self._config.dangerous_commands:
            if dangerous.lower() in command_lower:
                return True
        
        return False
    
    def requires_confirmation(self, command: str) -> bool:
        """Check if a command requires user confirmation."""
        if not self._config.require_confirmation:
            return False
        
        return self.is_dangerous(command)
    
    def validate_command(self, command: str) -> tuple[bool, Optional[str]]:
        """Validate a command. Returns (is_safe, reason)."""
        if self.is_dangerous(command):
            return False, f"Potentially dangerous command detected: {command}"
        
        # Check for common injection patterns
        injection_patterns = [
            r';\s*rm\s',
            r'\|\s*rm\s',
            r'&&\s*rm\s',
            r'>\s*/etc/',
            r'>>\s*/etc/',
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Suspicious command pattern detected"
        
        return True, None
    
    def get_safety_level(self, command: str) -> str:
        """Get safety level: safe, caution, dangerous."""
        if self.is_dangerous(command):
            return "dangerous"
        
        # Commands that need attention
        caution_patterns = [
            r'install',
            r'update',
            r'upgrade',
            r'remove',
            r'delete',
            r'kill',
        ]
        
        for pattern in caution_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return "caution"
        
        return "safe"
