"""Signed invite/reset token helpers."""

from itsdangerous import BadData


def make_token(serializer, user_id, purpose):
    return serializer.dumps({"user_id": user_id, "purpose": purpose})


def read_token(serializer, token, purpose, max_age):
    try:
        data = serializer.loads(token, max_age=max_age)
    except BadData:
        return None

    if not isinstance(data, dict) or data.get("purpose") != purpose:
        return None

    return data.get("user_id")
