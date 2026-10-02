"""
AuraTrade Password Security Engine (txcore.auth.security)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Implements OWASP-recommended PBKDF2-HMAC-SHA256 password hashing,
cryptographic salt generation, and constant-time verification.
"""

import hashlib
import secrets
import hmac
from typing import Tuple

ITERATIONS = 600_000
HASH_NAME = "sha256"


def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using PBKDF2-HMAC-SHA256 with 600,000 iterations
    and a cryptographically random 16-byte salt.
    Format: pbkdf2:sha256:600000$<salt_hex>$<hash_hex>
    """
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac(HASH_NAME, password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2:{HASH_NAME}:{ITERATIONS}${salt.hex()}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """
    Verifies a plaintext password against a stored PBKDF2 hash using constant-time comparison.
    """
    try:
        parts = hashed.split("$")
        if len(parts) != 3:
            return False
        meta, salt_hex, key_hex = parts
        _, hash_name, iterations_str = meta.split(":")
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)

        computed_key = hashlib.pbkdf2_hmac(hash_name, password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(computed_key, expected_key)
    except Exception:
        return False
