import re
from typing import Optional
from ..config import get_config


class SafetyValidator:
    """Validates operations and requests user confirmation for dangerous actions."""
    
    def __init__(self):
        config = get_config()
        self.require_confirmation = config.require_confirmation
        self.dangerous_commands = config.dangerous_commands
    
    def requires_confirmation(self, action: str) -> tuple[bool, str]:
        """Check if an action requires user confirmation."""
        if not self.require_confirmation:
            return False, ""
        
        action_lower = action.lower()
        
        for pattern in self.dangerous_commands:
            if pattern.lower() in action_lower:
                return True, f"Contains dangerous pattern: {pattern}"
        
        if self._is_file_deletion(action):
            return True, "File deletion detected"
        
        if self._is_install_command(action):
            return True, "Software installation detected"
        
        if self._is_publish_command(action):
            return True, "Publishing/release detected"
        
        if self._is_system_command(action):
            return True, "System-level command detected"
        
        return False, ""
    
    def _is_file_deletion(self, action: str) -> bool:
        """Check if action involves file deletion."""
        patterns = [
            r'\brm\b',
            r'\brmdir\b',
            r'\bdelete\b.*\bfile',
            r'\bremove\b.*\bfile',
            r'\btrash\b',
        ]
        return any(re.search(p, action.lower()) for p in patterns)
    
    def _is_install_command(self, action: str) -> bool:
        """Check if action involves software installation."""
        patterns = [
            r'\bpip\s+install\b',
            r'\bnpm\s+install\b',
            r'\byarn\s+add\b',
            r'\bbrew\s+install\b',
            r'\bapt\s+install\b',
            r'\byum\s+install\b',
            r'\binstall\b.*\bpackage',
        ]
        return any(re.search(p, action.lower()) for p in patterns)
    
    def _is_publish_command(self, action: str) -> bool:
        """Check if action involves publishing."""
        patterns = [
            r'\bgit\s+push\b',
            r'\bnpm\s+publish\b',
            r'\bpip\s+upload\b',
            r'\brelease\b',
            r'\bdeploy\b',
            r'\bpublish\b',
        ]
        return any(re.search(p, action.lower()) for p in patterns)
    
    def _is_system_command(self, action: str) -> bool:
        """Check if action is a system-level command."""
        patterns = [
            r'\bsudo\b',
            r'\bchmod\b',
            r'\bchown\b',
            r'\bsystemctl\b',
            r'\bservice\b',
            r'\breboot\b',
            r'\bshutdown\b',
        ]
        return any(re.search(p, action.lower()) for p in patterns)
    
    def validate_task(self, task_description: str) -> tuple[bool, str]:
        """Validate a task before execution."""
        return self.requires_confirmation(task_description)
    
    def get_confirmation(self, action: str, reason: str) -> bool:
        """Get user confirmation for an action."""
        print("\n" + "=" * 60)
        print("⚠️  SAFETY CHECK REQUIRED")
        print("=" * 60)
        print(f"\nAction: {action}")
        print(f"Reason: {reason}")
        print("\nDo you want to proceed?")
        print("  [y] Yes - Proceed with the action")
        print("  [n] No - Cancel this action")
        print("  [s] Skip - Skip this task")
        print()
        
        while True:
            response = input("Your choice (y/n/s): ").strip().lower()
            
            if response in ('y', 'yes'):
                return True
            elif response in ('n', 'no'):
                return False
            elif response in ('s', 'skip'):
                return False
            else:
                print("Please enter 'y' for yes, 'n' for no, or 's' to skip")
    
    def validate_and_confirm(self, action: str) -> bool:
        """Validate an action and get confirmation if needed."""
        needs_confirmation, reason = self.requires_confirmation(action)
        
        if not needs_confirmation:
            return True
        
        return self.get_confirmation(action, reason)