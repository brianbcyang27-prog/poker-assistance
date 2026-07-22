"""Log redaction — automatically redact secrets from all outputs.

Before writing logs, events, memory, mission replay, reasoning,
tool history — redact API keys, passwords, tokens, connection strings.
"""

import re
from typing import Optional


_REDACT_PATTERNS = [
    (r"nvapi-[A-Za-z0-9\-_]{20,}", "[REDACTED_NVIDIA_KEY]"),
    (r"sk-[A-Za-z0-9]{20,}", "[REDACTED_OPENAI_KEY]"),
    (r"sk-ant-[A-Za-z0-9\-_]{20,}", "[REDACTED_ANTHROPIC_KEY]"),
    (r"ghp_[A-Za-z0-9]{36}", "[REDACTED_GITHUB_TOKEN]"),
    (r"github_pat_[A-Za-z0-9\-_]{20,}", "[REDACTED_GITHUB_PAT]"),
    (r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]"),
    (r"AIza[0-9A-Za-z\-_]{35}", "[REDACTED_GOOGLE_KEY]"),
    (r"xox[baprs]-[A-Za-z0-9\-]{10,}", "[REDACTED_SLACK_TOKEN]"),
    (r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_.+/=]+", "[REDACTED_JWT]"),
    (r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"]?([^\s'\"]{8,})['\"]?", r"\1=[REDACTED_PASSWORD]"),
    (r"(?i)bearer\s+([A-Za-z0-9\-_\.]{20,})", "Bearer [REDACTED_TOKEN]"),
    (r"(?i)authorization:\s*bearer\s+[^\s\"']+", "Authorization: Bearer [REDACTED_TOKEN]"),
    (r"(?i)api[_-]?key\s*[=:]\s*['\"]?([A-Za-z0-9\-_]{20,})['\"]?", "api_key=[REDACTED_KEY]"),
    (r"(mysql|postgres|mongodb|redis)://[^:]+:[^@]+@[^\s\"']+", r"\1://[REDACTED_USER]:[REDACTED_PASS]@"),
    (r"-----BEGIN (RSA |EC )?PRIVATE KEY-----[\s\S]*?-----END (RSA |EC )?PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]"),
]


class LogRedactor:
    """Redact secrets from strings before logging/writing."""

    def __init__(self):
        self._compiled = [(re.compile(pattern), replacement) for pattern, replacement in _REDACT_PATTERNS]

    def redact(self, text: str) -> str:
        """Redact all secrets from the given text."""
        if not text:
            return text

        result = text
        for pattern, replacement in self._compiled:
            result = pattern.sub(replacement, result)

        return result

    def redact_dict(self, data: dict) -> dict:
        """Redact secrets in all string values of a dict."""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.redact(value)
            elif isinstance(value, dict):
                result[key] = self.redact_dict(value)
            elif isinstance(value, list):
                result[key] = [self.redact(item) if isinstance(item, str) else item for item in value]
            else:
                result[key] = value
        return result

    def redact_list(self, items: list) -> list:
        """Redact secrets in a list of strings."""
        return [self.redact(item) if isinstance(item, str) else item for item in items]

    def is_safe(self, text: str) -> bool:
        """Check if text contains any detectable secrets."""
        for pattern, _ in self._compiled:
            if pattern.search(text):
                return False
        return True


_redactor: Optional[LogRedactor] = None


def get_redactor() -> LogRedactor:
    global _redactor
    if _redactor is None:
        _redactor = LogRedactor()
    return _redactor


def redact(text: str) -> str:
    """Convenience function to redact secrets from text."""
    return get_redactor().redact(text)
