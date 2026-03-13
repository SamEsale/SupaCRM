from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def validate_password_policy(password: str) -> None:
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long")
    if not any(char.islower() for char in password):
        raise ValueError("Password must include at least one lowercase letter")
    if not any(char.isupper() for char in password):
        raise ValueError("Password must include at least one uppercase letter")
    if not any(char.isdigit() for char in password):
        raise ValueError("Password must include at least one digit")
    if not any(not char.isalnum() for char in password):
        raise ValueError("Password must include at least one special character")


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False
