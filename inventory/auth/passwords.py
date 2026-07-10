"""Password hashing and validation helpers."""

from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(raw_password):
    return generate_password_hash(raw_password)


def verify_password(password_hash, raw_password):
    if not password_hash:
        return False
    return check_password_hash(password_hash, raw_password)


def validate_password_strength(raw_password, min_length):
    if not raw_password or len(raw_password) < min_length:
        return f"Password must be at least {min_length} characters."
    return None
