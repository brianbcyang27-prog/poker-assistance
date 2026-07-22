"""Comprehensive tests for the JARVIS Security Module."""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from jarvis.security.crypto import VaultCrypto
from jarvis.security.vault import EncryptedVault
from jarvis.security.providers import (
    KeychainProvider, VaultProvider, EnvProvider, DotEnvProvider, GitHubProvider,
)
from jarvis.security.secret_manager import SecretManager
from jarvis.security.migration import VaultMigration
from jarvis.security.audit import AuditLog
from jarvis.security.scanner import SecretScanner
from jarvis.security.redactor import LogRedactor, redact
from jarvis.security.git_protection import GitProtection
from jarvis.security.exceptions import (
    VaultError, VaultLockedError, VaultCorruptedError,
    DecryptionError, MigrationError,
)


# ═══════════════════════════════════════════════════════════════
# CRYPTO TESTS
# ═══════════════════════════════════════════════════════════════

class TestVaultCrypto:
    def test_encrypt_decrypt_roundtrip(self):
        crypto = VaultCrypto()
        password = "test-password-123!"
        data = b"Hello, JARVIS security!"
        encrypted = crypto.encrypt(data, password)
        decrypted = crypto.decrypt(encrypted, password)
        assert decrypted == data

    def test_encrypt_decrypt_json(self):
        crypto = VaultCrypto()
        password = "test-password-123!"
        obj = {"NVIDIA_API_KEY": "nvapi-test123", "OPENAI_API_KEY": "sk-test456"}
        encrypted = crypto.encrypt_json(obj, password)
        decrypted = crypto.decrypt_json(encrypted, password)
        assert decrypted == obj

    def test_wrong_password_fails(self):
        crypto = VaultCrypto()
        data = crypto.encrypt(b"secret data", "correct-password")
        with pytest.raises(ValueError, match="Decryption failed"):
            crypto.decrypt(data, "wrong-password")

    def test_tampered_data_fails(self):
        crypto = VaultCrypto()
        data = crypto.encrypt(b"secret data", "password")
        tampered = bytearray(data)
        tampered[-1] ^= 0xFF
        with pytest.raises(ValueError):
            crypto.decrypt(bytes(tampered), "password")

    def test_different_encryptions_differ(self):
        crypto = VaultCrypto()
        e1 = crypto.encrypt(b"same data", "password")
        e2 = crypto.encrypt(b"same data", "password")
        assert e1 != e2

    def test_derive_key_deterministic(self):
        crypto = VaultCrypto()
        import os
        salt = os.urandom(32)
        k1 = crypto.derive_key("password", salt)
        k2 = crypto.derive_key("password", salt)
        assert k1 == k2
        assert len(k1) == 32

    def test_hash_verify_password(self):
        crypto = VaultCrypto()
        h, salt = crypto.hash_password("mypassword")
        assert crypto.verify_password("mypassword", h, salt)
        assert not crypto.verify_password("wrongpassword", h, salt)

    def test_generate_password(self):
        crypto = VaultCrypto()
        pw = crypto.generate_password()
        assert len(pw) > 20


# ═══════════════════════════════════════════════════════════════
# VAULT TESTS
# ═══════════════════════════════════════════════════════════════

class TestEncryptedVault:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        self.vault = EncryptedVault(self._tmpdir)

    def test_create_vault(self):
        self.vault.create("password123", {"KEY1": "value1"})
        assert self.vault.exists
        assert self.vault.is_unlocked

    def test_unlock_vault(self):
        self.vault.create("password123", {"KEY1": "value1"})
        self.vault.lock()
        assert not self.vault.is_unlocked
        self.vault.unlock("password123")
        assert self.vault.get("KEY1") == "value1"

    def test_wrong_password_unlock(self):
        self.vault.create("password123", {"KEY1": "value1"})
        self.vault.lock()
        with pytest.raises(DecryptionError):
            self.vault.unlock("wrong")

    def test_vault_not_found(self):
        with pytest.raises(VaultError, match="No vault found"):
            self.vault.unlock("password")

    def test_vault_already_exists(self):
        self.vault.create("password123")
        with pytest.raises(VaultError, match="already exists"):
            self.vault.create("another")

    def test_set_get_delete(self):
        self.vault.create("pw", {})
        self.vault.set("KEY1", "val1")
        assert self.vault.get("KEY1") == "val1"
        self.vault.delete("KEY1")
        assert self.vault.get("KEY1") == ""

    def test_list_secrets_masked(self):
        self.vault.create("pw", {"NVIDIA_API_KEY": "nvapi-superlongsecret123"})
        secrets = self.vault.list_secrets()
        assert "nvapi" not in secrets["NVIDIA_API_KEY"]
        assert "****" in secrets["NVIDIA_API_KEY"]

    def test_vault_persistence(self):
        self.vault.create("pw", {"KEY1": "val1"})
        self.vault.lock()
        vault2 = EncryptedVault(self._tmpdir)
        vault2.unlock("pw")
        assert vault2.get("KEY1") == "val1"

    def test_change_password(self):
        self.vault.create("old-pw", {"KEY1": "val1"})
        self.vault.change_password("old-pw", "new-pw")
        self.vault.lock()
        self.vault.unlock("new-pw")
        assert self.vault.get("KEY1") == "val1"

    def test_vault_corrupted(self):
        self.vault.create("pw", {"KEY1": "val1"})
        self.vault.lock()
        self.vault._vault_path.write_bytes(b"corrupted data")
        with pytest.raises(DecryptionError):
            self.vault.unlock("pw")

    def test_get_meta(self):
        self.vault.create("pw")
        meta = self.vault.get_meta()
        assert meta["version"] == 1
        assert meta["algorithm"] == "AES-256-GCM"


# ═══════════════════════════════════════════════════════════════
# PROVIDER TESTS
# ═══════════════════════════════════════════════════════════════

class TestProviders:
    def test_env_provider(self):
        os.environ["TEST_SECRET_KEY"] = "test-value-123"
        provider = EnvProvider()
        assert provider.get("TEST_SECRET_KEY") == "test-value-123"
        assert provider.get("NONEXISTENT") is None
        del os.environ["TEST_SECRET_KEY"]

    def test_dotenv_provider(self):
        tmpdir = tempfile.mkdtemp()
        env_file = Path(tmpdir) / ".env"
        env_file.write_text("TEST_KEY=test_value\nOTHER_KEY=other_value\n")
        provider = DotEnvProvider(str(env_file))
        assert provider.get("TEST_KEY") == "test_value"
        assert provider.get("OTHER_KEY") == "other_value"
        assert provider.get("MISSING") is None

    def test_vault_provider(self):
        tmpdir = tempfile.mkdtemp()
        vault = EncryptedVault(tmpdir)
        vault.create("pw", {"KEY1": "val1"})
        provider = VaultProvider(vault)
        assert provider.get("KEY1") == "val1"
        assert provider.get("MISSING") is None

    def test_provider_priority(self):
        assert KeychainProvider().priority < VaultProvider().priority
        assert VaultProvider().priority < EnvProvider().priority
        assert EnvProvider().priority < DotEnvProvider().priority
        assert DotEnvProvider().priority < GitHubProvider().priority


# ═══════════════════════════════════════════════════════════════
# SECRET MANAGER TESTS
# ═══════════════════════════════════════════════════════════════

class TestSecretManager:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()

    def test_get_from_env(self):
        os.environ["TEST_SM_KEY"] = "from-env"
        mgr = SecretManager(self._tmpdir)
        assert mgr.get("TEST_SM_KEY") == "from-env"
        del os.environ["TEST_SM_KEY"]

    def test_override(self):
        mgr = SecretManager(self._tmpdir)
        mgr.override("KEY", "override-value")
        assert mgr.get("KEY") == "override-value"
        mgr.clear_overrides()
        assert mgr.get("KEY") == ""

    def test_set_to_vault(self):
        mgr = SecretManager(self._tmpdir)
        mgr.vault.create("pw")
        mgr.set("KEY1", "val1")
        assert mgr.get("KEY1") == "val1"

    def test_list_all(self):
        os.environ["TEST_LIST_KEY"] = "test"
        mgr = SecretManager(self._tmpdir)
        result = mgr.list_all()
        assert "NVIDIA_API_KEY" in result
        del os.environ["TEST_LIST_KEY"]

    def test_health_check(self):
        mgr = SecretManager(self._tmpdir)
        health = mgr.health_check()
        assert "Environment Variables" in health


# ═══════════════════════════════════════════════════════════════
# MIGRATION TESTS
# ═══════════════════════════════════════════════════════════════

class TestVaultMigration:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()

    def test_needs_migration(self):
        env_path = Path(self._tmpdir) / ".env"
        env_path.write_text("NVIDIA_API_KEY=nvapi-test\n")
        migration = VaultMigration(self._tmpdir)
        assert migration.needs_migration

    def test_no_migration_needed(self):
        migration = VaultMigration(self._tmpdir)
        assert not migration.needs_migration

    def test_parse_env(self):
        env_path = Path(self._tmpdir) / ".env"
        env_path.write_text("NVIDIA_API_KEY=nvapi-test\nOPENAI_API_KEY=sk-test\n# comment\n")
        migration = VaultMigration(self._tmpdir)
        secrets = migration.parse_env()
        assert secrets["NVIDIA_API_KEY"] == "nvapi-test"
        assert secrets["OPENAI_API_KEY"] == "sk-test"

    def test_migrate(self):
        env_path = Path(self._tmpdir) / ".env"
        env_path.write_text("NVIDIA_API_KEY=nvapi-test\n")
        migration = VaultMigration(self._tmpdir)
        success, details = migration.migrate("password123")
        assert success
        assert details["count"] == 1
        assert env_path.exists()

    def test_migrate_delete_env(self):
        env_path = Path(self._tmpdir) / ".env"
        env_path.write_text("NVIDIA_API_KEY=nvapi-test\n")
        migration = VaultMigration(self._tmpdir)
        migration.migrate("password123", delete_env=True)
        assert not env_path.exists()

    def test_verify_migration(self):
        env_path = Path(self._tmpdir) / ".env"
        env_path.write_text("NVIDIA_API_KEY=nvapi-test\n")
        migration = VaultMigration(self._tmpdir)
        migration.migrate("password123")
        valid, details = migration.verify_migration("password123")
        assert valid
        assert "NVIDIA_API_KEY" in details["matches"]


# ═══════════════════════════════════════════════════════════════
# AUDIT TESTS
# ═══════════════════════════════════════════════════════════════

class TestAuditLog:
    def test_log_and_read(self):
        tmpdir = tempfile.mkdtemp()
        audit = AuditLog(tmpdir)
        audit.log("test_action", "test_key", "test_provider")
        entries = audit.get_entries()
        assert len(entries) == 1
        assert entries[0]["action"] == "test_action"

    def test_stats(self):
        tmpdir = tempfile.mkdtemp()
        audit = AuditLog(tmpdir)
        audit.log("resolve", "KEY1", "provider1")
        audit.log("resolve", "KEY2", "provider1")
        audit.log("set", "KEY1", "vault")
        stats = audit.get_stats()
        assert stats["total"] == 3
        assert stats["actions"]["resolve"] == 2

    def test_clear(self):
        tmpdir = tempfile.mkdtemp()
        audit = AuditLog(tmpdir)
        audit.log("test", "key", "provider")
        audit.clear()
        assert len(audit.get_entries()) == 0


# ═══════════════════════════════════════════════════════════════
# SCANNER TESTS
# ═══════════════════════════════════════════════════════════════

class TestSecretScanner:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()

    def test_scan_finds_nvidia_key(self):
        src = Path(self._tmpdir) / "test.py"
        src.write_text('api_key = "nvapi-supersecretkey12345678"\n')
        scanner = SecretScanner(self._tmpdir)
        findings = scanner.scan()
        assert any(f["type"] == "NVIDIA API Key" for f in findings)

    def test_scan_finds_openai_key(self):
        src = Path(self._tmpdir) / "config.py"
        src.write_text('key = "sk-supersecretopenaikey12345678"\n')
        scanner = SecretScanner(self._tmpdir)
        findings = scanner.scan()
        assert any(f["type"] == "OpenAI API Key" for f in findings)

    def test_scan_ignores_comments(self):
        src = Path(self._tmpdir) / "test.py"
        src.write_text('# api_key = "nvapi-shouldnotmatch"\n')
        scanner = SecretScanner(self._tmpdir)
        findings = scanner.scan()
        assert not any(f["type"] == "NVIDIA API Key" for f in findings)

    def test_scan_finds_private_key(self):
        src = Path(self._tmpdir) / "server_key.pem"
        src.write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----\n")
        scanner = SecretScanner(self._tmpdir)
        findings = scanner.scan()
        assert any(f["type"] == "Private Key" for f in findings)

    def test_generate_report(self):
        scanner = SecretScanner(self._tmpdir)
        report = scanner.generate_report([])
        assert "CLEAN" in report

    def test_scan_and_save(self):
        scanner = SecretScanner(self._tmpdir)
        path = scanner.scan_and_save(str(Path(self._tmpdir) / "report.md"))
        assert Path(path).exists()


# ═══════════════════════════════════════════════════════════════
# REDACTOR TESTS
# ═══════════════════════════════════════════════════════════════

class TestLogRedactor:
    def test_redact_nvidia_key(self):
        r = LogRedactor()
        text = "Using key nvapi-abc123def456ghi789jkl012mno345"
        result = r.redact(text)
        assert "nvapi-abc123" not in result
        assert "REDACTED" in result

    def test_redact_openai_key(self):
        r = LogRedactor()
        text = "OpenAI key: sk-supersecretkey12345678abcdefghij"
        result = r.redact(text)
        assert "sk-supersecret" not in result

    def test_redact_bearer_token(self):
        r = LogRedactor()
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.test.signature"
        result = r.redact(text)
        assert "eyJ" not in result

    def test_redact_private_key(self):
        r = LogRedactor()
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAK...\n-----END RSA PRIVATE KEY-----"
        result = r.redact(text)
        assert "MIIEowIBAAK" not in result
        assert "REDACTED_PRIVATE_KEY" in result

    def test_redact_dict(self):
        r = LogRedactor()
        data = {"api_key": "nvapi-supersecretkey12345678", "name": "jarvis"}
        result = r.redact_dict(data)
        assert "nvapi" not in result["api_key"]
        assert result["name"] == "jarvis"

    def test_is_safe(self):
        r = LogRedactor()
        assert r.is_safe("Hello world")
        assert not r.is_safe("nvapi-supersecretkey12345678")

    def test_clean_text_unchanged(self):
        r = LogRedactor()
        text = "This is clean text with no secrets"
        assert r.redact(text) == text


# ═══════════════════════════════════════════════════════════════
# GIT PROTECTION TESTS
# ═══════════════════════════════════════════════════════════════

class TestGitProtection:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        (Path(self._tmpdir) / ".git").mkdir()

    def test_setup_gitignore(self):
        gp = GitProtection(self._tmpdir)
        gp.setup_gitignore()
        gitignore = (Path(self._tmpdir) / ".gitignore").read_text()
        assert ".secrets.enc" in gitignore
        assert "*.pem" in gitignore

    def test_install_hook(self):
        gp = GitProtection(self._tmpdir)
        assert gp.install_pre_commit_hook()
        hook = Path(self._tmpdir) / ".git" / "hooks" / "pre-commit"
        assert hook.exists()
        assert "JARVIS" in hook.read_text()

    def test_hook_installed_check(self):
        gp = GitProtection(self._tmpdir)
        assert not gp.is_hook_installed()
        gp.install_pre_commit_hook()
        assert gp.is_hook_installed()

    def test_uninstall_hook(self):
        gp = GitProtection(self._tmpdir)
        gp.install_pre_commit_hook()
        assert gp.uninstall_pre_commit_hook()
        assert not gp.is_hook_installed()

    def test_not_git_repo(self):
        gp = GitProtection(tempfile.mkdtemp())
        assert not gp.is_git_repo
        assert not gp.install_pre_commit_hook()

    def test_status(self):
        gp = GitProtection(self._tmpdir)
        status = gp.get_status()
        assert status["is_git_repo"]
        assert not status["hook_installed"]


# ═══════════════════════════════════════════════════════════════
# EDGE CASE / RECOVERY TESTS
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_vault(self):
        tmpdir = tempfile.mkdtemp()
        vault = EncryptedVault(tmpdir)
        vault.create("pw")
        assert vault.secret_count == 0

    def test_large_secret(self):
        tmpdir = tempfile.mkdtemp()
        vault = EncryptedVault(tmpdir)
        big_value = "x" * 10000
        vault.create("pw", {"BIG": big_value})
        assert vault.get("BIG") == big_value

    def test_special_characters_in_secret(self):
        tmpdir = tempfile.mkdtemp()
        vault = EncryptedVault(tmpdir)
        special = "key with spaces & special chars!@#$%^&*()"
        vault.create("pw", {"SPECIAL": special})
        assert vault.get("SPECIAL") == special

    def test_unicode_in_secret(self):
        tmpdir = tempfile.mkdtemp()
        vault = EncryptedVault(tmpdir)
        vault.create("pw", {"UNICODE": "日本語テスト"})
        assert vault.get("UNICODE") == "日本語テスト"

    def test_concurrent_access(self):
        tmpdir = tempfile.mkdtemp()
        vault = EncryptedVault(tmpdir)
        vault.create("pw", {"KEY": "val"})
        vault.set("KEY2", "val2")
        vault.save()
        vault2 = EncryptedVault(tmpdir)
        vault2.unlock("pw")
        assert vault2.get("KEY") == "val"
        assert vault2.get("KEY2") == "val2"

    def test_redact_empty_string(self):
        r = LogRedactor()
        assert r.redact("") == ""

    def test_redact_none_safe(self):
        r = LogRedactor()
        assert r.redact(None) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
