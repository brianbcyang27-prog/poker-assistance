"""First-run interactive setup experience.

If no vault exists, launch interactive setup:
- Welcome to JARVIS
- Create master password
- Enter NVIDIA API Key
- Optional providers
- Save encrypted vault
- Validate by making one successful NVIDIA request
"""

import getpass
import sys
from pathlib import Path
from typing import Optional

from .vault import EncryptedVault
from .migration import VaultMigration
from .secret_manager import SecretManager
from .audit import AuditLog


class FirstRunSetup:
    """Interactive first-run experience for JARVIS security."""

    def __init__(self, vault_dir: Optional[str] = None):
        self._dir = Path(vault_dir) if vault_dir else Path.cwd()
        self._vault = EncryptedVault(str(self._dir))
        self._migration = VaultMigration(str(self._dir))
        self._audit = AuditLog(str(self._dir))

    @property
    def needs_setup(self) -> bool:
        return not self._vault.exists

    def run(self) -> bool:
        """Run the interactive setup. Returns True if setup completed."""
        if not self.needs_setup:
            print("[JARVIS] Vault already exists. Use 'jarvis vault unlock' to access.")
            return True

        self._print_welcome()

        if self._migration.needs_migration:
            return self._run_migration()
        else:
            return self._run_fresh_setup()

    def _print_welcome(self) -> None:
        print()
        print("=" * 60)
        print("  JARVIS Security Vault — First Run Setup")
        print("=" * 60)
        print()
        print("  No encrypted vault found.")
        print("  This setup will create a secure vault to store")
        print("  all your API keys and credentials.")
        print()

    def _get_password(self, prompt: str = "Create master password: ") -> str:
        """Get password with confirmation."""
        while True:
            pw = getpass.getpass(prompt)
            if len(pw) < 8:
                print("  Password must be at least 8 characters.")
                continue
            pw2 = getpass.getpass("Confirm password: ")
            if pw != pw2:
                print("  Passwords don't match. Try again.")
                continue
            return pw

    def _run_fresh_setup(self) -> bool:
        """Fresh setup with no existing .env."""
        print("  Step 1: Create your master password")
        print("-" * 40)
        password = self._get_password()
        print()

        print("  Step 2: Enter your API keys (press Enter to skip)")
        print("-" * 40)
        secrets = {}

        nvidia_key = input("  NVIDIA API Key: ").strip()
        if nvidia_key:
            secrets["NVIDIA_API_KEY"] = nvidia_key

        openai_key = input("  OpenAI API Key: ").strip()
        if openai_key:
            secrets["OPENAI_API_KEY"] = openai_key

        anthropic_key = input("  Anthropic API Key: ").strip()
        if anthropic_key:
            secrets["ANTHROPIC_API_KEY"] = anthropic_key

        google_key = input("  Google API Key: ").strip()
        if google_key:
            secrets["GOOGLE_API_KEY"] = google_key

        github_token = input("  GitHub Token: ").strip()
        if github_token:
            secrets["GITHUB_TOKEN"] = github_token

        print()

        print("  Step 3: Creating encrypted vault")
        print("-" * 40)
        try:
            self._vault.create(password, secrets)
            print(f"  Vault created with {len(secrets)} secrets.")
            self._audit.log("setup", "vault_created", "first_run", {"secret_count": len(secrets)})
        except Exception as e:
            print(f"  ERROR: Failed to create vault: {e}")
            return False

        print()

        print("  Step 4: Validating")
        print("-" * 40)
        if secrets.get("NVIDIA_API_KEY"):
            if self._validate_nvidia_key(secrets["NVIDIA_API_KEY"]):
                print("  NVIDIA API key validated successfully!")
            else:
                print("  Warning: Could not validate NVIDIA key (network issue?)")
                print("  The key has been saved to the vault.")

        print()
        print("=" * 60)
        print("  Setup complete! Your secrets are now encrypted.")
        print("  Use 'jarvis vault' to manage your vault.")
        print("=" * 60)
        print()

        return True

    def _run_migration(self) -> bool:
        """Migrate from existing .env to vault."""
        env_secrets = self._migration.parse_env()
        print(f"  Found .env with {len(env_secrets)} secrets:")
        for key in env_secrets:
            print(f"    - {key}")
        print()

        confirm = input("  Migrate to encrypted vault? [Y/n]: ").strip().lower()
        if confirm and confirm != "y" and confirm != "yes":
            print("  Migration cancelled.")
            return False

        print()
        print("  Step 1: Create master password for the vault")
        print("-" * 40)
        password = self._get_password()
        print()

        print("  Step 2: Encrypting and migrating secrets")
        print("-" * 40)
        try:
            success, details = self._migration.migrate(password, delete_env=False)
            if success:
                print(f"  Migrated {details['count']} secrets successfully!")
            else:
                print(f"  Migration failed: {details}")
                return False
        except Exception as e:
            print(f"  Migration failed: {e}")
            return False

        print()
        print("  Step 3: Verifying migration")
        print("-" * 40)
        valid, details = self._migration.verify_migration(password)
        if valid:
            print(f"  Verified: {details['matches']} keys match .env")
        else:
            print(f"  Warning: {details.get('mismatches', [])} keys don't match")

        print()
        delete = input("  Delete old .env file? [y/N]: ").strip().lower()
        if delete == "y" or delete == "yes":
            env_path = self._dir / ".env"
            if env_path.exists():
                env_path.unlink()
                print("  .env deleted.")
                self._audit.log("migration", "env_deleted", "first_run")

        print()
        print("=" * 60)
        print("  Migration complete! Your secrets are now encrypted.")
        print("=" * 60)
        print()

        return True

    def _validate_nvidia_key(self, key: str) -> bool:
        """Validate an NVIDIA API key by making a test request."""
        try:
            import urllib.request
            import json

            req = urllib.request.Request(
                "https://integrate.api.nvidia.com/v1/models",
                headers={"Authorization": f"Bearer {key}"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False
