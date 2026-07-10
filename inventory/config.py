"""Environment-backed application configuration."""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/inventory_management_system")
ELEVATED_ROLES = {"administrator", "faculty"}
SCHEMA = BASE_DIR / "schema.sql"


def env_flag(name, default=False):
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.lower() in {"1", "true", "yes", "on"}


def env_float(name, default):
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return default


APP_ENV = os.environ.get("APP_ENV", "development").lower()
SECRET_KEY = os.environ.get("SECRET_KEY")
DEV_SECRET_KEY = "dev-secret-key-change-before-production"
MIN_PRODUCTION_SECRET_KEY_LENGTH = 64
APP_BASE_URL = os.environ.get("APP_BASE_URL")
BARCODE_PREFIX = os.environ.get("BARCODE_PREFIX", "KATZ-NURS")
TRANSACTIONS_PAGE_SIZE = max(1, int(os.environ.get("TRANSACTIONS_PAGE_SIZE", "50")))
MIN_PASSWORD_LENGTH = 8
INVITE_TOKEN_MAX_AGE = 72 * 60 * 60
RESET_TOKEN_MAX_AGE = 60 * 60

EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "").strip().lower()
EMAIL_FROM = os.environ.get("EMAIL_FROM", "").strip()
SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}
SMTP_USE_SSL = os.environ.get("SMTP_USE_SSL", "false").lower() in {"1", "true", "yes", "on"}

SESSION_IDLE_MINUTES = int(os.environ.get("SESSION_IDLE_MINUTES", "30"))
SUDO_MODE_MAX_AGE = int(os.environ.get("SUDO_MODE_MAX_AGE", "300"))
LOGIN_MAX_ATTEMPTS = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_LOCKOUT_SECONDS = int(os.environ.get("LOGIN_LOCKOUT_SECONDS", "300"))

RATELIMIT_ENABLED = os.environ.get("RATELIMIT_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
RATELIMIT_LOGIN = os.environ.get("RATELIMIT_LOGIN", "10 per minute")
RATELIMIT_PASSWORD = os.environ.get("RATELIMIT_PASSWORD", "5 per minute")
RATELIMIT_STOCK = os.environ.get("RATELIMIT_STOCK", "60 per minute")

PROXY_FIX_ENABLED = env_flag("PROXY_FIX_ENABLED", APP_ENV == "production")
HSTS_ENABLED = env_flag("HSTS_ENABLED", APP_ENV == "production")
HSTS_MAX_AGE = int(os.environ.get("HSTS_MAX_AGE", "31536000"))
HSTS_INCLUDE_SUBDOMAINS = env_flag("HSTS_INCLUDE_SUBDOMAINS", False)
HSTS_PRELOAD = env_flag("HSTS_PRELOAD", False)

SENTRY_DSN = os.environ.get("SENTRY_DSN", "").strip()
SENTRY_TRACES_SAMPLE_RATE = max(
    0.0,
    min(
        1.0,
        env_float(
            "SENTRY_TRACES_SAMPLE_RATE",
            0.1 if APP_ENV == "production" else 0.0,
        ),
    ),
)


def validate_production_config():
    if APP_ENV != "production":
        return

    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY environment variable must be set in production.")

    if SECRET_KEY == DEV_SECRET_KEY:
        raise RuntimeError("SECRET_KEY must not use the development fallback in production.")

    if len(SECRET_KEY) < MIN_PRODUCTION_SECRET_KEY_LENGTH:
        raise RuntimeError(
            "SECRET_KEY must be at least "
            f"{MIN_PRODUCTION_SECRET_KEY_LENGTH} characters in production."
        )


def hsts_header_value():
    hsts_value = f"max-age={HSTS_MAX_AGE}"
    if HSTS_INCLUDE_SUBDOMAINS:
        hsts_value += "; includeSubDomains"
    if HSTS_PRELOAD:
        hsts_value += "; preload"
    return hsts_value


def add_static_headers(headers, path, url):
    if HSTS_ENABLED:
        headers.setdefault("Strict-Transport-Security", hsts_header_value())
