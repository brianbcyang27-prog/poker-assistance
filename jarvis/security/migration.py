"""Automatic migration from .env to encrypted vault."""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .vault import EncryptedVault
from .audit import AuditLog
from .exceptions import MigrationError


class VaultMigration:
    """Migrate plaintext .env secrets to encrypted vault."""

    def __init__(self, vault_dir: Optional[str] = None):
        self._dir = Path(vault_dir) if vault_dir else Path.cwd()
        self._vault = EncryptedVault(str(self._dir))
        self._audit = AuditLog(str(self._dir))

    @property
    def needs_migration(self) -> bool:
        """Check if .env exists and vault doesn't."""
        env_path = self._dir / ".env"
        return env_path.exists() and not self._vault.exists

    @property
    def migration_status(self) -> Dict[str, any]:
        """Get current migration status."""
        env_path = self._dir / ".env"
        return {
            "env_exists": env_path.exists(),
            "vault_exists": self._vault.exists,
            "needs_migration": self.needs_migration,
            "env_secrets": len(self._parse_env()) if env_path.exists() else 0,
        }

    def parse_env(self) -> Dict[str, str]:
        """Parse .env file into a dict."""
        return self._parse_env()

    def _parse_env(self) -> Dict[str, str]:
        env_path = self._dir / ".env"
        if not env_path.exists():
            return {}

        result = {}
        for line in env_path.read_text().splitlines():
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

    def migrate(self, password: str, delete_env: bool = False) -> Tuple[bool, Dict[str, any]]:
        """Migrate .env secrets to encrypted vault.

        Returns (success, details).
        """
        if self._vault.exists:
            raise MigrationError("Vault already exists — cannot migrate")

        secrets = self._parse_env()
        if not secrets:
            raise MigrationError("No secrets found in .env")

        try:
            self._vault.create(password, secrets)
        except Exception as e:
            raise MigrationError(f"Failed to create vault: {e}")

        migrated_keys = list(secrets.keys())
        self._audit.log("migration", "complete", "migration", {
            "keys_migrated": migrated_keys,
            "count": len(migrated_keys),
        })

        if delete_env:
            env_path = self._dir / ".env"
            if env_path.exists():
                env_path.unlink()
                self._audit.log("migration", "env_deleted", "migration")

        return True, {
            "migrated_keys": migrated_keys,
            "count": len(migrated_keys),
            "env_deleted": delete_env,
        }

    def verify_migration(self, password: str) -> Tuple[bool, Dict[str, any]]:
        """Verify that vault matches .env after migration."""
        env_secrets = self._parse_env()

        if not self._vault.exists:
            return False, {"error": "Vault does not exist"}

        try:
            self._vault.unlock(password)
        except Exception as e:
            return False, {"error": f"Cannot unlock vault: {e}"}

        vault_secrets = self._vault.to_dict()
        self._vault.lock()

        matches = {}
        mismatches = []
        missing = []

        for key, env_value in env_secrets.items():
            vault_value = vault_secrets.get(key, "")
            if vault_value == env_value:
                matches[key] = True
            else:
                mismatches.append(key)

        for key in vault_secrets:
            if key not in env_secrets and vault_secrets[key]:
                missing.append(key)

        success = len(mismatches) == 0
        return success, {
            "matches": list(matches.keys()),
            "mismatches": mismatches,
            "vault_only": missing,
            "env_count": len(env_secrets),
            "vault_count": len([v for v in vault_secrets.values() if v]),
        }
