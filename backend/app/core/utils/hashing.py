"""
Backward-compatible hashing helpers.

IMPORTANT:
- Password hashing must use the canonical implementation in
  app.core.security.passwords.
- This module exists only as a compatibility shim for older imports.
"""

from app.core.security.passwords import hash_password, verify_password

__all__ = ["hash_password", "verify_password"]

