"""Multi-provider secret resolution.

Priority order:
1. macOS Keychain
2. .secrets.enc (encrypted vault)
3. Environment Variables
4. .env (legacy)
5. GitHub Actions Secrets

The application should not know where secrets come from.
Only SecretManager.get() is used.
"""

import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class SecretProvider(ABC):
    """Base class for all secret providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""

    @property
    @abstractmethod
    def priority(self) -> int:
        """Lower number = higher priority."""

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Resolve a secret. Returns None if not found."""

    def has(self, key: str) -> bool:
        return self.get(key) is not None


class KeychainProvider(SecretProvider):
    """macOS Keychain provider."""

    @property
    def name(self) -> str:
        return "macOS Keychain"

    @property
    def priority(self) -> int:
        return 10

    def get(self, key: str) -> Optional[str]:
        try:
            result = subprocess.run(
                ["security", "find-generic-password", "-s", f"jarvis-{key}", "-w"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None

    def set(self, key: str, value: str) -> bool:
        try:
            subprocess.run(
                ["security", "add-generic-password",
                 "-s", f"jarvis-{key}", "-a", "jarvis", "-w", value, "-U"],
                capture_output=True, timeout=5
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def delete(self, key: str) -> bool:
        try:
            subprocess.run(
                ["security", "delete-generic-password", "-s", f"jarvis-{key}"],
                capture_output=True, timeout=5
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False


class VaultProvider(SecretProvider):
    """Encrypted vault provider (.secrets.enc)."""

    def __init__(self, vault=None):
        self._vault = vault

    @property
    def name(self) -> str:
        return "Encrypted Vault"

    @property
    def priority(self) -> int:
        return 20

    def set_vault(self, vault) -> None:
        self._vault = vault

    def get(self, key: str) -> Optional[str]:
        if self._vault and self._vault.is_unlocked:
            value = self._vault.get(key)
            if value:
                return value
        return None


class EnvProvider(SecretProvider):
    """Environment variable provider."""

    @property
    def name(self) -> str:
        return "Environment Variables"

    @property
    def priority(self) -> int:
        return 30

    def get(self, key: str) -> Optional[str]:
        return os.environ.get(key) or None


class DotEnvProvider(SecretProvider):
    """Legacy .env file provider."""

    def __init__(self, env_path: Optional[str] = None):
        self._env_path = Path(env_path) if env_path else Path.cwd() / ".env"
        self._cache: Optional[dict] = None

    @property
    def name(self) -> str:
        return ".env File"

    @property
    def priority(self) -> int:
        return 40

    def get(self, key: str) -> Optional[str]:
        if self._cache is None:
            self._cache = self._parse()
        return self._cache.get(key)

    def _parse(self) -> dict:
        if not self._env_path.exists():
            return {}
        result = {}
        for line in self._env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if v:
                    result[k] = v
        return result

    def list_secrets(self) -> dict:
        if self._cache is None:
            self._cache = self._parse()
        return dict(self._cache)


class GitHubProvider(SecretProvider):
    """GitHub Actions Secrets provider."""

    @property
    def name(self) -> str:
        return "GitHub Actions"

    @property
    def priority(self) -> int:
        return 50

    def get(self, key: str) -> Optional[str]:
        if os.environ.get("GITHUB_ACTIONS") != "true":
            return None
        return os.environ.get(key)
