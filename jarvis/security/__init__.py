"""JARVIS Security Module — Enterprise Secret Vault & Security Framework.

Provides:
- Encrypted vault storage (AES-256-GCM + PBKDF2)
- Multi-provider secret resolution (Keychain → Vault → Env → .env → GitHub)
- Automatic migration from plaintext .env
- Repository secret scanning
- Git pre-commit hooks
- Log redaction
- Security dashboard
"""

from .exceptions import (
    SecurityError,
    VaultError,
    VaultLockedError,
    VaultCorruptedError,
    DecryptionError,
    ProviderError,
    MigrationError,
    ScannerError,
)
from .crypto import VaultCrypto
from .vault import EncryptedVault
from .providers import SecretProvider, KeychainProvider, VaultProvider, EnvProvider, DotEnvProvider, GitHubProvider
from .secret_manager import SecretManager
from .migration import VaultMigration
from .audit import AuditLog
from .scanner import SecretScanner
from .redactor import LogRedactor

__all__ = [
    "SecurityError", "VaultError", "VaultLockedError", "VaultCorruptedError",
    "DecryptionError", "ProviderError", "MigrationError", "ScannerError",
    "VaultCrypto", "EncryptedVault",
    "SecretProvider", "KeychainProvider", "VaultProvider", "EnvProvider",
    "DotEnvProvider", "GitHubProvider",
    "SecretManager", "VaultMigration", "AuditLog", "SecretScanner", "LogRedactor",
]

_manager = None

def get_manager() -> "SecretManager":
    global _manager
    if _manager is None:
        _manager = SecretManager()
    return _manager

def get_secret(key: str, default: str = "") -> str:
    return get_manager().get(key, default=default)
