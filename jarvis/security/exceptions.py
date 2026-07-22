"""Security module exceptions."""


class SecurityError(Exception):
    """Base exception for all security errors."""


class VaultError(SecurityError):
    """Vault operation failed."""


class VaultLockedError(VaultError):
    """Vault is locked — unlock with master password first."""


class VaultCorruptedError(VaultError):
    """Vault file is corrupted or tampered with."""


class DecryptionError(VaultError):
    """Decryption failed — wrong password or corrupted data."""


class ProviderError(SecurityError):
    """Secret provider failed to resolve a key."""


class MigrationError(SecurityError):
    """Migration from .env to vault failed."""


class ScannerError(SecurityError):
    """Repository scan failed."""
