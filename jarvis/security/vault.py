"""Encrypted vault — the single source of truth for all credentials.

Stores secrets in .secrets.enc with AES-256-GCM encryption.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .crypto import VaultCrypto
from .exceptions import VaultError, VaultCorruptedError, VaultLockedError, DecryptionError


_VAULT_FILE = ".secrets.enc"
_VAULT_META = ".secrets.meta.json"
_DEFAULT_SECRETS = {
    "NVIDIA_API_KEY": "",
    "OPENAI_API_KEY": "",
    "ANTHROPIC_API_KEY": "",
    "GOOGLE_API_KEY": "",
    "GITHUB_TOKEN": "",
    "SMTP_PASSWORD": "",
    "DATABASE_PASSWORD": "",
}


class EncryptedVault:
    """AES-256-GCM encrypted secret vault with integrity verification."""

    def __init__(self, vault_dir: Optional[str] = None):
        self._dir = Path(vault_dir) if vault_dir else Path.cwd()
        self._vault_path = self._dir / _VAULT_FILE
        self._meta_path = self._dir / _VAULT_META
        self._crypto = VaultCrypto()
        self._password: Optional[str] = None
        self._secrets: Dict[str, str] = {}
        self._dirty = False
        self._unlocked = False

    @property
    def exists(self) -> bool:
        return self._vault_path.exists()

    @property
    def is_unlocked(self) -> bool:
        return self._unlocked

    @property
    def secret_count(self) -> int:
        return len([v for v in self._secrets.values() if v])

    def create(self, password: str, secrets: Optional[Dict[str, str]] = None) -> None:
        """Create a new vault with the given password."""
        if self.exists:
            raise VaultError("Vault already exists — delete it first or use unlock()")

        self._password = password
        self._secrets = {**_DEFAULT_SECRETS, **(secrets or {})}
        self._save_meta()
        self._persist()
        self._unlocked = True

    def unlock(self, password: str) -> bool:
        """Unlock an existing vault with the password."""
        if not self.exists:
            raise VaultError("No vault found — run create() first")

        raw = self._vault_path.read_bytes()
        try:
            self._secrets = self._crypto.decrypt_json(raw, password)
        except (ValueError, Exception) as e:
            raise DecryptionError(f"Wrong password or corrupted vault: {e}")

        self._password = password
        self._unlocked = True
        self._load_meta()
        return True

    def lock(self) -> None:
        """Lock the vault, clearing the password from memory."""
        if self._dirty:
            self._persist()
        self._password = None
        self._secrets = {}
        self._unlocked = False

    def get(self, key: str, default: str = "") -> str:
        """Get a secret value by key."""
        if not self._unlocked:
            raise VaultLockedError("Vault is locked — unlock with password first")
        return self._secrets.get(key, default)

    def set(self, key: str, value: str) -> None:
        """Set a secret value."""
        if not self._unlocked:
            raise VaultLockedError("Vault is locked")
        self._secrets[key] = value
        self._dirty = True

    def delete(self, key: str) -> bool:
        """Delete a secret."""
        if not self._unlocked:
            raise VaultLockedError("Vault is locked")
        if key in self._secrets:
            del self._secrets[key]
            self._dirty = True
            return True
        return False

    def list_secrets(self) -> Dict[str, str]:
        """Return all secrets (values masked)."""
        if not self._unlocked:
            raise VaultLockedError("Vault is locked")
        return {k: self._mask(v) for k, v in self._secrets.items() if v}

    def list_all_keys(self) -> List[str]:
        """Return all secret keys."""
        return list(self._secrets.keys())

    def to_dict(self) -> Dict[str, str]:
        """Return all secrets as a dict (use with caution)."""
        if not self._unlocked:
            raise VaultLockedError("Vault is locked")
        return dict(self._secrets)

    def update(self, secrets: Dict[str, str]) -> None:
        """Bulk update secrets."""
        if not self._unlocked:
            raise VaultLockedError("Vault is locked")
        self._secrets.update(secrets)
        self._dirty = True

    def save(self) -> None:
        """Persist current state to disk."""
        if self._unlocked:
            self._persist()
            self._dirty = False

    def change_password(self, old_password: str, new_password: str) -> None:
        """Change the vault password."""
        if not self._unlocked:
            raise VaultLockedError("Vault is locked")

        raw = self._vault_path.read_bytes()
        self._crypto.decrypt_json(raw, old_password)

        self._password = new_password
        self._persist()
        self._update_meta()

    def _persist(self) -> None:
        """Encrypt and write vault to disk."""
        if not self._password:
            raise VaultError("No password set")
        data = self._crypto.encrypt_json(self._secrets, self._password)
        self._vault_path.write_bytes(data)
        self._dirty = False

    def _mask(self, value: str) -> str:
        """Mask a secret value for display."""
        if len(value) <= 8:
            return "****"
        return value[:4] + "*" * (len(value) - 8) + value[-4:]

    def _save_meta(self) -> None:
        """Save vault metadata."""
        meta = {
            "created_at": time.time(),
            "updated_at": time.time(),
            "version": 1,
            "algorithm": "AES-256-GCM",
            "kdf": "PBKDF2-HMAC-SHA256",
            "iterations": 600_000,
            "secret_count": self.secret_count,
        }
        self._meta_path.write_text(json.dumps(meta, indent=2))

    def _load_meta(self) -> None:
        """Load vault metadata."""
        if self._meta_path.exists():
            meta = json.loads(self._meta_path.read_text())
            meta["updated_at"] = time.time()
            meta["secret_count"] = self.secret_count
            self._meta_path.write_text(json.dumps(meta, indent=2))

    def _update_meta(self) -> None:
        """Update metadata timestamp."""
        if self._meta_path.exists():
            meta = json.loads(self._meta_path.read_text())
            meta["updated_at"] = time.time()
            meta["password_changed_at"] = time.time()
            self._meta_path.write_text(json.dumps(meta, indent=2))

    def get_meta(self) -> Dict[str, Any]:
        """Get vault metadata."""
        if self._meta_path.exists():
            return json.loads(self._meta_path.read_text())
        return {}

    def delete_vault(self) -> None:
        """Permanently delete the vault."""
        if self._vault_path.exists():
            self._vault_path.unlink()
        if self._meta_path.exists():
            self._meta_path.unlink()
        self._secrets = {}
        self._password = None
        self._unlocked = False
