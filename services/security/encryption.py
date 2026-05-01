"""Encryption Module — Field-level encryption for sensitive data.

Blueprint §8: Secures PII/NPI data (SSN, PAN, account numbers) at rest.
Uses AES-GCM for authenticated encryption.
"""

from typing import Any
import base64
import json
import os

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class EncryptionService:
    """Provides field-level encryption and decryption.

    In production, the master key should be fetched from Azure Key Vault,
    HashiCorp Vault, or AWS KMS.
    """

    def __init__(self, master_key_b64: str | None = None) -> None:
        if not HAS_CRYPTO:
            print("WARNING: cryptography package not found. Encryption will be a no-op stub.")

        if master_key_b64:
            self._key = base64.b64decode(master_key_b64)
        else:
            # Generate a key for development if none provided
            self._key = AESGCM.generate_key(bit_length=256) if HAS_CRYPTO else b"stub_key"

        self._aesgcm = AESGCM(self._key) if HAS_CRYPTO else None

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string using AES-GCM."""
        if not plaintext:
            return plaintext
        if not self._aesgcm:
            return f"ENC[{plaintext}]"

        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        return base64.b64encode(nonce + ciphertext).decode('utf-8')

    def decrypt(self, encrypted_b64: str) -> str:
        """Decrypt an AES-GCM encrypted string."""
        if not encrypted_b64:
            return encrypted_b64
        if not self._aesgcm:
            if encrypted_b64.startswith("ENC[") and encrypted_b64.endswith("]"):
                return encrypted_b64[4:-1]
            return encrypted_b64

        try:
            data = base64.b64decode(encrypted_b64)
            nonce = data[:12]
            ciphertext = data[12:]
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

    def encrypt_dict(self, data: dict[str, Any], sensitive_fields: list[str]) -> dict[str, Any]:
        """Encrypt specific fields in a dictionary."""
        result = data.copy()
        for field in sensitive_fields:
            if field in result and isinstance(result[field], str):
                result[field] = self.encrypt(result[field])
        return result

    def decrypt_dict(self, data: dict[str, Any], sensitive_fields: list[str]) -> dict[str, Any]:
        """Decrypt specific fields in a dictionary."""
        result = data.copy()
        for field in sensitive_fields:
            if field in result and isinstance(result[field], str):
                try:
                    result[field] = self.decrypt(result[field])
                except ValueError:
                    pass  # Keep original if decryption fails (e.g. wasn't encrypted)
        return result
