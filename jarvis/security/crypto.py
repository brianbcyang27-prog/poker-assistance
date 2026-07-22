"""AES-256-GCM encryption with PBKDF2-HMAC-SHA256 key derivation.

Provides authenticated encryption for the secret vault.
"""

import hashlib
import hmac
import json
import os
import secrets
import struct
from typing import Tuple

_ALGO_VERSION = 1
_SALT_BYTES = 32
_IV_BYTES = 12
_TAG_BYTES = 16
_PBKDF2_ITERATIONS = 600_000
_KEY_BYTES = 32


class VaultCrypto:
    """AES-256-GCM encryption/decryption using pure Python fallback.

    Uses cryptography lib when available, falls back to
    PBKDF2 + XOR-stream cipher for environments without it.
    """

    def __init__(self):
        self._has_crypto = False
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives import hashes
            self._AESGCM = AESGCM
            self._PBKDF2HMAC = PBKDF2HMAC
            self._hashes = hashes
            self._has_crypto = True
        except ImportError:
            pass

    def derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive AES-256 key from password using PBKDF2-HMAC-SHA256."""
        if self._has_crypto:
            kdf = self._PBKDF2HMAC(
                algorithm=self._hashes.SHA256(),
                length=_KEY_BYTES,
                salt=salt,
                iterations=_PBKDF2_ITERATIONS,
            )
            return kdf.derive(password.encode("utf-8"))
        else:
            return hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS, dklen=_KEY_BYTES
            )

    def encrypt(self, plaintext: bytes, password: str) -> bytes:
        """Encrypt data. Returns: version(1) + salt(32) + iv(12) + tag(16) + ciphertext."""
        salt = os.urandom(_SALT_BYTES)
        iv = os.urandom(_IV_BYTES)
        key = self.derive_key(password, salt)

        if self._has_crypto:
            aesgcm = self._AESGCM(key)
            ciphertext_with_tag = aesgcm.encrypt(iv, plaintext, None)
            tag = ciphertext_with_tag[-_TAG_BYTES:]
            ciphertext = ciphertext_with_tag[:-_TAG_BYTES]
        else:
            ciphertext, tag = self._xor_encrypt(key, iv, plaintext)

        header = struct.pack(">B", _ALGO_VERSION) + salt + iv + tag
        return header + ciphertext

    def decrypt(self, data: bytes, password: str) -> bytes:
        """Decrypt data. Verifies integrity via auth tag."""
        if len(data) < 1 + _SALT_BYTES + _IV_BYTES + _TAG_BYTES + 1:
            raise ValueError("Data too short to be a valid vault")

        version = data[0]
        if version != _ALGO_VERSION:
            raise ValueError(f"Unsupported vault version: {version}")

        salt = data[1:1 + _SALT_BYTES]
        iv = data[1 + _SALT_BYTES:1 + _SALT_BYTES + _IV_BYTES]
        tag = data[1 + _SALT_BYTES + _IV_BYTES:1 + _SALT_BYTES + _IV_BYTES + _TAG_BYTES]
        ciphertext = data[1 + _SALT_BYTES + _IV_BYTES + _TAG_BYTES:]

        key = self.derive_key(password, salt)

        if self._has_crypto:
            aesgcm = self._AESGCM(key)
            try:
                return aesgcm.decrypt(iv, ciphertext + tag, None)
            except Exception:
                raise ValueError("Decryption failed — wrong password or corrupted data")
        else:
            return self._xor_decrypt(key, iv, ciphertext, tag)

    def _xor_encrypt(self, key: bytes, iv: bytes, plaintext: bytes) -> Tuple[bytes, bytes]:
        """Fallback: XOR stream cipher with HMAC-SHA256 tag."""
        stream = self._generate_stream(key, iv, len(plaintext))
        ciphertext = bytes(a ^ b for a, b in zip(plaintext, stream))
        tag = hmac.new(key, iv + ciphertext, hashlib.sha256).digest()[:_TAG_BYTES]
        return ciphertext, tag

    def _xor_decrypt(self, key: bytes, iv: bytes, ciphertext: bytes, tag: bytes) -> bytes:
        """Fallback: verify HMAC then XOR-decrypt."""
        expected_tag = hmac.new(key, iv + ciphertext, hashlib.sha256).digest()[:_TAG_BYTES]
        if not hmac.compare_digest(tag, expected_tag):
            raise ValueError("Decryption failed — wrong password or corrupted data")
        stream = self._generate_stream(key, iv, len(ciphertext))
        return bytes(a ^ b for a, b in zip(ciphertext, stream))

    def _generate_stream(self, key: bytes, iv: bytes, length: int) -> bytes:
        """Generate keystream using counter mode."""
        stream = b""
        counter = 0
        while len(stream) < length:
            block_input = iv + counter.to_bytes(4, "big")
            stream += hashlib.sha256(key + block_input).digest()
            counter += 1
        return stream[:length]

    def encrypt_json(self, obj: dict, password: str) -> bytes:
        """Encrypt a JSON-serializable dict."""
        plaintext = json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return self.encrypt(plaintext, password)

    def decrypt_json(self, data: bytes, password: str) -> dict:
        """Decrypt to a dict."""
        plaintext = self.decrypt(data, password)
        return json.loads(plaintext.decode("utf-8"))

    def generate_password(self, length: int = 32) -> str:
        """Generate a cryptographically secure random password."""
        return secrets.token_urlsafe(length)

    def hash_password(self, password: str) -> Tuple[bytes, bytes]:
        """Hash password for verification. Returns (hash, salt)."""
        salt = os.urandom(_SALT_BYTES)
        h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
        return h, salt

    def verify_password(self, password: str, stored_hash: bytes, salt: bytes) -> bool:
        """Verify password against stored hash."""
        h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
        return hmac.compare_digest(h, stored_hash)
