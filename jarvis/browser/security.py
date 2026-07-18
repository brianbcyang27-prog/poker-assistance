"""Browser security — permission rules for web actions.

Extends the computer PermissionSystem with browser-specific rules.

Risk levels for browser actions:
  SAFE      — search, reading pages, taking screenshots
  LOW       — clicking links, navigating within known sites
  MEDIUM    — downloading files, filling non-sensitive forms
  HIGH      — login, sending messages, submitting forms with personal data
  DANGEROUS — financial transactions, deleting accounts, sharing credentials
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass

log = logging.getLogger("jarvis.browser.security")


# ── Risk classification for browser actions ───────────────

BROWSER_ACTION_RISKS = {
    # Safe
    "search": "safe",
    "extract": "safe",
    "screenshot": "safe",
    "get_content": "safe",
    "get_links": "safe",
    "get_text": "safe",
    "list_tabs": "safe",

    # Low
    "navigate": "low",
    "click": "low",
    "scroll": "low",
    "hover": "low",
    "back": "low",
    "forward": "low",
    "reload": "low",
    "new_tab": "low",
    "close_tab": "low",
    "switch_tab": "low",

    # Medium
    "type": "medium",
    "fill_form": "medium",
    "select_option": "medium",
    "download": "medium",
    "upload": "medium",

    # High
    "login": "high",
    "submit_form": "high",
    "send_message": "high",
    "post_comment": "high",
    "share": "high",

    # Dangerous
    "payment": "dangerous",
    "purchase": "dangerous",
    "delete_account": "dangerous",
    "transfer_money": "dangerous",
    "change_password": "dangerous",
}

# ── URL pattern safety rules ──────────────────────────────

# Domains that are always safe to browse
SAFE_DOMAINS = [
    "google.com", "github.com", "stackoverflow.com",
    "wikipedia.org", "docs.python.org", "developer.mozilla.org",
    "npmjs.com", "pypi.org", "arxiv.org",
]

# Domains that require extra caution
SENSITIVE_DOMAINS = [
    "bank", "paypal", "venmo", "cashapp",
    "amazon.com", "ebay.com",  # purchases
    "facebook.com", "twitter.com", "instagram.com",  # social (posting)
    "gmail.com", "outlook.com",  # email (sending)
]

# Domains that should never be accessed automatically
BLOCKED_DOMAINS = [
    "malware.com", "phishing.com",  # placeholder examples
]


class BrowserSecurity:
    """Enforces security rules for browser actions.

    Usage:
        security = BrowserSecurity()
        decision = security.check_action("navigate", url="https://github.com")
        if decision.allowed:
            # proceed
    """

    def __init__(self, mode: str = "normal"):
        self.mode = mode  # "normal" | "permissive" | "strict"
        self._approval_cache: dict[str, bool] = {}

    def check_action(
        self,
        action: str,
        url: str = "",
        agent: str = "",
        context: Optional[dict] = None,
    ) -> "BrowserDecision":
        """Check if a browser action is allowed.

        Args:
            action: Browser action name (navigate, click, type, etc.)
            url: Target URL (if applicable)
            agent: Which agent is requesting
            context: Additional context

        Returns:
            BrowserDecision with allowed, risk_level, reason
        """
        # Step 1: Classify action risk
        risk = self.classify_action_risk(action)

        # Step 2: Check URL safety
        if url:
            url_risk = self.classify_url_risk(url)
            risk = self._higher_risk(risk, url_risk)

        # Step 3: Check cache
        cache_key = f"{action}:{url}:{agent}"
        if cache_key in self._approval_cache:
            return BrowserDecision(
                allowed=True, risk_level=risk,
                reason="Previously approved", approved_by="cache",
            )

        # Step 4: Apply policy
        return self._apply_policy(risk, action, url)

    def classify_action_risk(self, action: str) -> str:
        """Classify the risk level of a browser action."""
        return BROWSER_ACTION_RISKS.get(action, "medium")

    def classify_url_risk(self, url: str) -> str:
        """Classify the risk level based on URL."""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
        except Exception:
            return "medium"

        # Check blocked
        for blocked in BLOCKED_DOMAINS:
            if blocked in domain:
                return "dangerous"

        # Check sensitive
        for sensitive in SENSITIVE_DOMAINS:
            if sensitive in domain:
                return "high"

        # Check safe
        for safe in SAFE_DOMAINS:
            if safe in domain:
                return "safe"

        # Unknown domain: medium risk
        return "medium"

    def _higher_risk(self, a: str, b: str) -> str:
        order = ["safe", "low", "medium", "high", "dangerous"]
        ai = order.index(a) if a in order else 0
        bi = order.index(b) if b in order else 0
        return order[max(ai, bi)]

    def _apply_policy(self, risk: str, action: str, url: str) -> "BrowserDecision":
        if self.mode == "permissive":
            if risk in ("safe", "low", "medium"):
                return BrowserDecision(allowed=True, risk_level=risk, reason="Permissive mode")
            if risk == "high":
                return BrowserDecision(
                    allowed=True, risk_level=risk,
                    reason="Permissive mode (high risk)", requires_confirmation=True,
                )
            return BrowserDecision(
                allowed=False, risk_level=risk,
                reason="Permissive mode blocks dangerous", requires_approval=True,
            )

        if self.mode == "strict":
            if risk == "safe":
                return BrowserDecision(allowed=True, risk_level=risk, reason="Strict: safe only")
            return BrowserDecision(
                allowed=False, risk_level=risk,
                reason="Strict mode: requires approval", requires_approval=True,
            )

        # Normal mode
        if risk in ("safe", "low"):
            return BrowserDecision(
                allowed=True, risk_level=risk,
                reason=f"Auto-approved: {risk}", approved_by="auto",
            )
        if risk == "medium":
            return BrowserDecision(
                allowed=True, risk_level=risk,
                reason="Medium risk: allowed with notification",
                requires_confirmation=True, approved_by="notification",
            )
        if risk == "high":
            return BrowserDecision(
                allowed=False, risk_level=risk,
                reason="High risk: requires confirmation",
                requires_confirmation=True, requires_approval=True,
            )
        return BrowserDecision(
            allowed=False, risk_level=risk,
            reason="Dangerous: blocked", requires_approval=True,
        )

    def approve(self, action: str, url: str = "", agent: str = ""):
        """Cache an approval."""
        cache_key = f"{action}:{url}:{agent}"
        self._approval_cache[cache_key] = True

    def revoke(self, action: str, url: str = "", agent: str = ""):
        """Remove a cached approval."""
        cache_key = f"{action}:{url}:{agent}"
        self._approval_cache.pop(cache_key, None)

    def get_stats(self) -> dict:
        return {
            "mode": self.mode,
            "cached_approvals": len(self._approval_cache),
            "action_risks": len(BROWSER_ACTION_RISKS),
            "safe_domains": len(SAFE_DOMAINS),
            "sensitive_domains": len(SENSITIVE_DOMAINS),
        }


@dataclass
class BrowserDecision:
    """Result of a browser security check."""
    allowed: bool
    risk_level: str
    reason: str
    requires_confirmation: bool = False
    requires_approval: bool = False
    approved_by: str = ""


# Module-level singleton
browser_security = BrowserSecurity()
