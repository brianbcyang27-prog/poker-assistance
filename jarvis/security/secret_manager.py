"""SecretManager — the single interface for all secret access.

No module should directly call os.getenv() or read .env files.
Every credential MUST go through SecretManager.get().
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from .providers import (
    SecretProvider, KeychainProvider, VaultProvider,
    EnvProvider, DotEnvProvider, GitHubProvider,
)
from .vault import EncryptedVault
from .audit import AuditLog
from .exceptions import VaultError


_DEFAULT_SECRETS = {
    "NVIDIA_API_KEY": "",
    "OPENAI_API_KEY": "",
    "ANTHROPIC_API_KEY": "",
    "GOOGLE_API_KEY": "",
    "GITHUB_TOKEN": "",
    "SMTP_PASSWORD": "",
    "DATABASE_PASSWORD": "",
}


class SecretManager:
    """Unified secret resolution with provider priority chain.

    Usage:
        from jarvis.security import get_secret
        api_key = get_secret("NVIDIA_API_KEY")
    """

    def __init__(self, vault_dir: Optional[str] = None):
        self._dir = Path(vault_dir) if vault_dir else Path.cwd()
        self._audit = AuditLog(str(self._dir))

        self._vault = EncryptedVault(str(self._dir))
        self._providers: List[SecretProvider] = [
            KeychainProvider(),
            VaultProvider(self._vault),
            EnvProvider(),
            DotEnvProvider(str(self._dir / ".env")),
            GitHubProvider(),
        ]
        self._providers.sort(key=lambda p: p.priority)

        self._cache: Dict[str, str] = {}
        self._overrides: Dict[str, str] = {}

    @property
    def vault(self) -> EncryptedVault:
        return self._vault

    @property
    def is_vault_ready(self) -> bool:
        return self._vault.exists

    @property
    def providers(self) -> List[SecretProvider]:
        return list(self._providers)

    def get(self, key: str, default: str = "", use_cache: bool = True) -> str:
        """Resolve a secret by key, checking providers in priority order."""
        if key in self._overrides:
            return self._overrides[key]

        if use_cache and key in self._cache:
            return self._cache[key]

        for provider in self._providers:
            try:
                value = provider.get(key)
                if value:
                    self._cache[key] = value
                    self._audit.log("resolve", key, provider.name)
                    return value
            except Exception:
                continue

        self._audit.log("miss", key, "none")
        return default

    def set(self, key: str, value: str, persist: bool = True) -> None:
        """Set a secret in the vault."""
        if persist and self._vault.exists and self._vault.is_unlocked:
            self._vault.set(key, value)
            self._vault.save()
            self._audit.log("set", key, "vault")
        self._cache[key] = value
        os.environ[key] = value

    def delete(self, key: str) -> bool:
        """Delete a secret from the vault."""
        if self._vault.exists and self._vault.is_unlocked:
            self._vault.delete(key)
            self._vault.save()
            self._audit.log("delete", key, "vault")
        self._cache.pop(key, None)
        os.environ.pop(key, None)
        return True

    def override(self, key: str, value: str) -> None:
        """Override a secret (for testing)."""
        self._overrides[key] = value

    def clear_overrides(self) -> None:
        self._overrides.clear()

    def list_all(self) -> Dict[str, str]:
        """List all known secrets with masked values."""
        result = {}
        for key in _DEFAULT_SECRETS:
            value = self.get(key, use_cache=False)
            if value:
                result[key] = self._mask(value)
            else:
                result[key] = "(not set)"
        for key, value in self._cache.items():
            if key not in result:
                result[key] = self._mask(value) if value else "(not set)"
        return result

    def list_keys(self) -> List[str]:
        """List all known secret keys."""
        return list(set(list(_DEFAULT_SECRETS.keys()) + list(self._cache.keys())))

    def _mask(self, value: str) -> str:
        if len(value) <= 8:
            return "****"
        return value[:4] + "*" * (len(value) - 8) + value[-4:]

    def get_provider_for(self, key: str) -> Optional[str]:
        """Find which provider resolves a given key."""
        for provider in self._providers:
            try:
                value = provider.get(key)
                if value:
                    return provider.name
            except Exception:
                continue
        return None

    def health_check(self) -> Dict[str, dict]:
        """Check health of all providers."""
        results = {}
        for provider in self._providers:
            try:
                test_key = "NVIDIA_API_KEY"
                value = provider.get(test_key)
                results[provider.name] = {
                    "available": True,
                    "has_nvidia_key": bool(value),
                    "priority": provider.priority,
                }
            except Exception as e:
                results[provider.name] = {
                    "available": False,
                    "error": str(e),
                    "priority": provider.priority,
                }
        return results
