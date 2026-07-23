"""Memory Validation — Health check for JARVIS memory system.

Ensures memory stores useful information but never secrets.
"""

import re
import logging
from typing import Optional

log = logging.getLogger("jarvis.memory_validation")


class MemoryValidator:
    """Validates memory content and health."""
    
    # Patterns that should never be stored
    SECRET_PATTERNS = [
        r"nvapi-[a-zA-Z0-9]{20,}",
        r"sk-[a-zA-Z0-9]{20,}",
        r"password\s*[:=]\s*\S+",
        r"api[_-]?key\s*[:=]\s*\S+",
        r"secret\s*[:=]\s*\S+",
        r"token\s*[:=]\s*\S+",
        r"Bearer\s+[a-zA-Z0-9\-._~+/]+=*",
    ]
    
    def __init__(self):
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.SECRET_PATTERNS]
    
    def contains_secrets(self, text: str) -> tuple[bool, list[str]]:
        """Check if text contains potential secrets.
        
        Returns (has_secrets, list_of_patterns_matched).
        """
        matches = []
        for pattern in self._compiled_patterns:
            if pattern.search(text):
                matches.append(pattern.pattern)
        return len(matches) > 0, matches
    
    def sanitize_for_storage(self, text: str) -> str:
        """Remove potential secrets from text before storage."""
        sanitized = text
        for pattern in self._compiled_patterns:
            sanitized = pattern.sub("[REDACTED]", sanitized)
        return sanitized
    
    async def validate_memory_health(self) -> dict:
        """Run memory health checks."""
        results = {
            "episodic": await self._check_episodic(),
            "personal": await self._check_personal(),
            "journal": await self._check_journal(),
            "working": await self._check_working(),
        }
        
        all_healthy = all(r.get("healthy", False) for r in results.values())
        return {
            "healthy": all_healthy,
            "systems": results,
        }
    
    async def _check_episodic(self) -> dict:
        """Check episodic memory health."""
        try:
            from jarvis.brain.memory.episodic import get_episodic_memory
            em = get_episodic_memory()
            episodes = await em.get_recent(limit=10)
            
            # Check for secrets in recent episodes
            secret_count = 0
            for ep in episodes:
                content = getattr(ep, "content", "") or ""
                has_secrets, _ = self.contains_secrets(content)
                if has_secrets:
                    secret_count += 1
            
            return {
                "healthy": True,
                "count": len(episodes),
                "secrets_found": secret_count,
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    async def _check_personal(self) -> dict:
        """Check personal memory health."""
        try:
            from jarvis.brain.memory.personal import get_personal_memory
            pm = get_personal_memory()
            # Just check if it's accessible
            return {"healthy": True}
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    async def _check_journal(self) -> dict:
        """Check journal memory health."""
        try:
            from jarvis.brain.memory.journal import get_journal
            journal = get_journal()
            return {"healthy": True}
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    async def _check_working(self) -> dict:
        """Check working memory health."""
        try:
            from jarvis.brain.memory.working import get_working_memory
            wm = get_working_memory()
            return {"healthy": True}
        except Exception as e:
            return {"healthy": False, "error": str(e)}


# Module-level singleton
memory_validator = MemoryValidator()
