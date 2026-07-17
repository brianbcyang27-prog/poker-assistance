"""PII/Privacy scrubbing for JARVIS.

Detects and redacts sensitive information before data is sent to external APIs.
Regex-based detection inspired by OpenAdapt's Presidio approach, but with zero
external dependencies.

Usage:
    from jarvis.brain.privacy import scrubber
    clean = scrubber.scrub("my email is bob@example.com")
    # clean == "my email is [EMAIL]"
"""

import re
from typing import Dict, List, Optional, Pattern, Tuple


class PrivacyScrubber:
    """Detect and redact PII from text using regex patterns.
    
    Supports emails, phone numbers, SSNs, credit cards, IPs, API keys,
    AWS keys, names, and file paths with usernames.
    """

    def __init__(self, allowlist: Optional[list[str]] = None):
        """Initialize scrubber.
        
        Args:
            allowlist: Patterns that should NOT be redacted (e.g. ["localhost",
                       "127.0.0.1"]). Matches are checked against the full
                       matched string.
        """
        self._allowlist: set[str] = set(allowlist or [])
        self._patterns: list[Tuple[str, Pattern, str]] = []
        self._build_patterns()

    def _build_patterns(self) -> None:
        """Compile all PII detection regex patterns.
        
        Order matters - more specific patterns should come first so they
        match before broader ones.
        """
        # API keys first (most specific)
        self._patterns.append((
            "API_KEY",
            re.compile(
                r"(?:nvapi-[A-Za-z0-9_-]{20,}|"
                r"sk-[A-Za-z0-9]{20,}|"
                r"key-[A-Za-z0-9]{20,}|"
                r"token-[A-Za-z0-9]{20,})"
            ),
            "[API_KEY]",
        ))
        self._patterns.append((
            "AWS_KEY",
            re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
            "[AWS_KEY]",
        ))

        # Financial / identity
        self._patterns.append((
            "SSN",
            re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            "[SSN]",
        ))
        self._patterns.append((
            "CARD",
            re.compile(
                r"\b(?:\d[ -]*?){13,19}\b"
            ),
            "[CARD]",
        ))

        # Network identifiers
        self._patterns.append((
            "EMAIL",
            re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
            "[EMAIL]",
        ))
        self._patterns.append((
            "PHONE",
            re.compile(
                r"(?<!\d)"
                r"(?:\+?1[-.\s]?)?"
                r"(?:\(?\d{3}\)?[-.\s]?)"
                r"\d{3}[-.\s]?"
                r"\d{4}"
                r"(?!\d)"
            ),
            "[PHONE]",
        ))
        self._patterns.append((
            "IP",
            re.compile(
                r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
                r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
            ),
            "[IP]",
        ))

        # File paths with usernames
        self._patterns.append((
            "FILE_PATH",
            re.compile(
                r"(/(?:Users|home)/)[^/\s]+"
            ),
            r"\1[USER]",
        ))

        # Names after common intros (most general / lowest priority)
        self._patterns.append((
            "NAME",
            re.compile(
                r"(?i)(?:my name is|i'm|i am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
            ),
            None,  # handled specially in _apply_name
        ))

    def scrub(self, text: str) -> str:
        """Detect and redact PII from text.
        
        Scans for all supported PII types and replaces them with tags.
        Items in the allowlist are preserved.
        
        Args:
            text: Input text that may contain PII.
            
        Returns:
            Text with PII replaced by redaction tags.
        """
        result = text

        for pii_type, pattern, replacement in self._patterns:
            if pii_type == "NAME":
                result = self._apply_name(result)
                continue

            result = pattern.sub(
                lambda m: self._check_allowlist(m, replacement),
                result,
            )

        return result

    def scrub_for_log(self, text: str) -> str:
        """Aggressively scrub text for log output.
        
        Applies standard scrubbing plus additional redactions for
        file paths, port numbers, and any token-like strings.
        
        Args:
            text: Input text to scrub.
            
        Returns:
            Heavily redacted text safe for logging.
        """
        result = self.scrub(text)

        # Redact anything that looks like a bearer token
        result = re.sub(
            r"(?i)(bearer\s+)[^\s]+",
            r"\1[REDACTED]",
            result,
        )

        # Redact port numbers from host:port patterns
        result = re.sub(
            r"(\w+(?:\.\w+)*:)\d+",
            r"\1[PORT]",
            result,
        )

        # Redact any remaining long hex strings (session tokens, etc.)
        result = re.sub(
            r"\b[A-Fa-f0-9]{32,}\b",
            "[HEX]",
            result,
        )

        return result

    def contains_pii(self, text: str) -> bool:
        """Quick check if text contains any detectable PII.
        
        Short-circuits on the first match for performance.
        
        Args:
            text: Input text to check.
            
        Returns:
            True if any PII pattern is found.
        """
        for pii_type, pattern, _ in self._patterns:
            if pii_type == "NAME":
                if re.search(
                    r"(?i)(?:my name is|i'm|i am)\s+[A-Z][a-z]+",
                    text,
                ):
                    return True
                continue

            if pattern.search(text):
                return True

        return False

    def get_redacted_count(self, text: str) -> Dict[str, int]:
        """Count how many instances of each PII type are found.
        
        Args:
            text: Input text to analyze.
            
        Returns:
            Dict mapping PII type names to their occurrence counts.
            Only types with count > 0 are included.
        """
        counts: Dict[str, int] = {}

        for pii_type, pattern, _ in self._patterns:
            if pii_type == "NAME":
                name_matches = re.findall(
                    r"(?i)(?:my name is|i'm|i am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                    text,
                )
                if name_matches:
                    counts[pii_type] = len(name_matches)
                continue

            matches = pattern.findall(text)
            if matches:
                counts[pii_type] = len(matches)

        return counts

    def _apply_name(self, text: str) -> str:
        """Replace name introductions with redacted tags.
        
        Handles patterns like "my name is Alice", "I'm Bob Smith",
        "I am Charlie" by preserving the intro and replacing only
        the name portion.
        """
        return re.sub(
            r"(?i)((?:my name is|i'm|i am)\s+)[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*",
            r"\1[NAME]",
            text,
        )

    def _check_allowlist(self, match: re.Match, replacement: str) -> str:
        """Return original text if matched value is in the allowlist."""
        matched_text = match.group(0)
        if matched_text in self._allowlist:
            return matched_text
        return match.expand(replacement)


# Module-level singleton with sensible defaults.
scrubber = PrivacyScrubber(allowlist=[
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
])
