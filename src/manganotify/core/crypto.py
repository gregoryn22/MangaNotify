# src/manganotify/core/crypto.py
"""
Cryptographic utilities for secure credential storage.
"""

from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Derive a cryptographic key from a password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_credential(credential: str, master_key: str) -> str:
    """Encrypt a credential using the master key."""
    if not credential:
        return ""

    # Validate master key
    if not master_key or len(master_key) < 32:
        raise ValueError("Master key must be at least 32 characters long")

    # Validate credential length
    if len(credential) > 1000:  # Reasonable limit
        raise ValueError("Credential too long")

    # Generate a random salt for this encryption
    salt = os.urandom(16)

    # Derive key from master key + salt
    key = derive_key_from_password(master_key, salt)

    # Encrypt the credential
    fernet = Fernet(key)
    encrypted = fernet.encrypt(credential.encode())

    # Return salt + encrypted data as base64
    combined = salt + encrypted
    return base64.urlsafe_b64encode(combined).decode()


def decrypt_credential(encrypted_credential: str, master_key: str) -> str:
    """Decrypt a credential using the master key."""
    if not encrypted_credential:
        return ""

    # Validate master key
    if not master_key or len(master_key) < 32:
        raise ValueError("Master key must be at least 32 characters long")

    try:
        # Decode base64
        combined = base64.urlsafe_b64decode(encrypted_credential.encode())

        # Validate minimum length (salt + some encrypted data)
        if len(combined) < 17:  # 16 bytes salt + at least 1 byte encrypted data
            raise ValueError("Encrypted credential too short")

        # Extract salt (first 16 bytes) and encrypted data
        salt = combined[:16]
        encrypted = combined[16:]

        # Derive key from master key + salt
        key = derive_key_from_password(master_key, salt)

        # Decrypt the credential
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted)

        return decrypted.decode()
    except Exception as e:
        # Log the error for debugging but don't expose it
        import logging

        logger = logging.getLogger(__name__)
        logger.warning("Credential decryption failed: %s", type(e).__name__)
        return ""


def generate_master_key() -> str:
    """Generate a secure random master key."""
    return base64.urlsafe_b64encode(os.urandom(32)).decode()
