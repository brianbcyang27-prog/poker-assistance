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

from .audit import AuditLog
from .crypto import VaultCrypto
from .exceptions import (
    DecryptionError,
    MigrationError,
    ProviderError,
    ScannerError,
    SecurityError,
    VaultCorruptedError,
    VaultError,
    VaultLockedError,
)
from .migration import VaultMigration
from .providers import (
    DotEnvProvider,
    EnvProvider,
    GitHubProvider,
    KeychainProvider,
    SecretProvider,
    VaultProvider,
)
from .redactor import LogRedactor
from .scanner import SecretScanner
from .secret_manager import SecretManager
from .vault import EncryptedVault

__all__ = [
    "SecurityError",
    "VaultError",
    "VaultLockedError",
    "VaultCorruptedError",
    "DecryptionError",
    "ProviderError",
    "MigrationError",
    "ScannerError",
    "VaultCrypto",
    "EncryptedVault",
    "SecretProvider",
    "KeychainProvider",
    "VaultProvider",
    "EnvProvider",
    "DotEnvProvider",
    "GitHubProvider",
    "SecretManager",
    "VaultMigration",
    "AuditLog",
    "SecretScanner",
    "LogRedactor",
]

_manager = None


def get_manager() -> "SecretManager":
    global _manager
    if _manager is None:
        _manager = SecretManager()
    return _manager


def get_secret(key: str, default: str = "") -> str:
    return get_manager().get(key, default=default)
