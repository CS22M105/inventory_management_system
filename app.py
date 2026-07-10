from flask import Flask, Response, abort, flash, g, got_request_exception, jsonify, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from whitenoise import WhiteNoise
from werkzeug.middleware.proxy_fix import ProxyFix
from itsdangerous import URLSafeTimedSerializer
import csv
import io
import json
import logging
import os
import psycopg2
import qrcode
import sentry_sdk
import sys
from inventory.auth.passwords import (
    hash_password as password_hash_password,
    validate_password_strength as password_validate_password_strength,
    verify_password as password_verify_password,
)
from inventory.auth.tokens import (
    make_token as token_make_token,
    read_token as token_read_token,
)
from inventory.items.barcodes import (
    generate_next_item_barcode as barcode_generate_next_item_barcode,
)
from inventory.items.forms import parse_expiration_date as forms_parse_expiration_date
from inventory.services.email import send_email as email_send_email
from inventory.transactions.repository import (
    build_transaction_filter_clause as transaction_build_filter_clause,
    count_transaction_rows as transaction_count_rows,
    get_transaction_rows as transaction_get_rows,
)
from psycopg2.extras import RealDictCursor
from sentry_sdk.integrations.flask import FlaskIntegration
import click
import time
import uuid
from datetime import timedelta
from pathlib import Path

# holds the parent path to the current script we are running.
BASE_DIR = Path(__file__).resolve().parent


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


DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/inventory_management_system")
ELEVATED_ROLES = {"administrator", "faculty"}
SCHEMA = BASE_DIR / "schema.sql"
APP_ENV = os.environ.get("APP_ENV", "development").lower()
SECRET_KEY = os.environ.get("SECRET_KEY")
DEV_SECRET_KEY = "dev-secret-key-change-before-production"
MIN_PRODUCTION_SECRET_KEY_LENGTH = 64
# Public base URL used when building QR-code links. If unset, the app falls
# back to the current request host at runtime (see later QR routes).
APP_BASE_URL = os.environ.get("APP_BASE_URL")
# Prefix for auto-generated internal item codes (e.g. KATZ-NURS-000014).
BARCODE_PREFIX = os.environ.get("BARCODE_PREFIX", "KATZ-NURS")
# On-screen transaction history page size (server-side pagination). The CSV
# export is intentionally NOT paginated -- it returns the full filtered set.
TRANSACTIONS_PAGE_SIZE = max(1, int(os.environ.get("TRANSACTIONS_PAGE_SIZE", "50")))
# Minimum length enforced for account passwords (see validate_password_strength).
MIN_PASSWORD_LENGTH = 8
# Lifetimes (in seconds) for signed invite and password-reset links.
INVITE_TOKEN_MAX_AGE = 72 * 60 * 60   # 72 hours
RESET_TOKEN_MAX_AGE = 60 * 60         # 1 hour
# Transactional email provider selector. Unset (the default) means "no provider
# configured": send_email() logs the message so invite/reset flows are testable
# locally. A real provider (SES/SendGrid/SMTP/...) is wired up at deploy time.
EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "").strip().lower()
EMAIL_FROM = os.environ.get("EMAIL_FROM", "").strip()
SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}
SMTP_USE_SSL = os.environ.get("SMTP_USE_SSL", "false").lower() in {"1", "true", "yes", "on"}
# Sessions expire after this many minutes of inactivity; each request slides the
# window forward so active users are not logged out mid-task (see below).
SESSION_IDLE_MINUTES = int(os.environ.get("SESSION_IDLE_MINUTES", "30"))
# Destructive admin actions require a fresh password re-entry ("sudo mode").
# A successful login or re-auth stays valid for this many seconds.
SUDO_MODE_MAX_AGE = int(os.environ.get("SUDO_MODE_MAX_AGE", "300"))
# Simple per-process brute-force cooldown: after this many consecutive failed
# logins for an email, further attempts are refused for LOGIN_LOCKOUT_SECONDS.
# This is a lightweight safety net; Step D (Flask-Limiter) is the robust,
# shared-store defense across multiple workers/hosts.
LOGIN_MAX_ATTEMPTS = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_LOCKOUT_SECONDS = int(os.environ.get("LOGIN_LOCKOUT_SECONDS", "300"))
# Step D: Flask-Limiter rate limits, keyed by client IP. All values are
# environment-configurable. RATELIMIT_STORAGE_URI defaults to in-memory (good
# for a single process); set it to a Redis URL (e.g. redis://host:6379) so
# limits are shared across multiple Gunicorn workers or hosts in production.
RATELIMIT_ENABLED = os.environ.get("RATELIMIT_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
# Login: brute-force protection on the credential endpoint.
RATELIMIT_LOGIN = os.environ.get("RATELIMIT_LOGIN", "10 per minute")
# Password links: request-reset / set-password / reset-password.
RATELIMIT_PASSWORD = os.environ.get("RATELIMIT_PASSWORD", "5 per minute")
# Stock endpoints: abuse/scraping protection (higher, still bounded).
RATELIMIT_STOCK = os.environ.get("RATELIMIT_STOCK", "60 per minute")
# Deployment hardening for TLS-terminating proxies. In production, the app
# trusts one upstream proxy's X-Forwarded-* headers so generated URLs and
# request.is_secure reflect the public HTTPS request instead of the internal
# plain HTTP hop from proxy -> app.
PROXY_FIX_ENABLED = env_flag("PROXY_FIX_ENABLED", APP_ENV == "production")
HSTS_ENABLED = env_flag("HSTS_ENABLED", APP_ENV == "production")
HSTS_MAX_AGE = int(os.environ.get("HSTS_MAX_AGE", "31536000"))
HSTS_INCLUDE_SUBDOMAINS = env_flag("HSTS_INCLUDE_SUBDOMAINS", False)
HSTS_PRELOAD = env_flag("HSTS_PRELOAD", False)
# Optional production error monitoring. Blank by default, so local development
# and tests do not send events or make Sentry network calls.
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


def initialize_sentry():
    if not SENTRY_DSN:
        return

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FlaskIntegration()],
        environment=APP_ENV,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
    )


LOG_EXTRA_FIELDS = (
    "request_id",
    "method",
    "path",
    "status",
    "duration_ms",
    "remote_addr",
    "error_type",
)


class JsonLineFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in LOG_EXTRA_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, separators=(",", ":"))


class PlainTextFormatter(logging.Formatter):
    def format(self, record):
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        pieces = [
            timestamp,
            record.levelname,
            record.name,
            record.getMessage(),
        ]
        for field in LOG_EXTRA_FIELDS:
            if hasattr(record, field):
                pieces.append(f"{field}={getattr(record, field)}")
        if record.exc_info:
            pieces.append(self.formatException(record.exc_info))
        return " ".join(str(piece) for piece in pieces)


def configure_logging(flask_app):
    formatter = JsonLineFormatter() if APP_ENV == "production" else PlainTextFormatter()

    for logger in (
        flask_app.logger,
        logging.getLogger("inventory.request"),
        logging.getLogger("inventory.error"),
    ):
        logger.handlers.clear()
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False


request_logger = logging.getLogger("inventory.request")
error_logger = logging.getLogger("inventory.error")


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


validate_production_config()
initialize_sentry()

app = Flask(__name__)
configure_logging(app)
if PROXY_FIX_ENABLED:
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=1,
        x_prefix=1,
    )
app.wsgi_app = WhiteNoise(
    app.wsgi_app,
    root=str(BASE_DIR / "static"),
    prefix="static/",
    max_age=31536000,
    add_headers_function=add_static_headers,
)

app.config["SECRET_KEY"] = SECRET_KEY or DEV_SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = APP_ENV == "production"
# Idle-timeout: signed session cookies are only accepted within this window.
# SESSION_REFRESH_EACH_REQUEST re-issues the cookie (with a fresh timestamp) on
# every response, so the window slides forward while a user is active and only
# expires after SESSION_IDLE_MINUTES of true inactivity. Sessions are marked
# permanent at login so this lifetime applies.
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=SESSION_IDLE_MINUTES)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True

# CSRF protection for every state-changing (POST/PUT/PATCH/DELETE) request.
# Each form must include the hidden csrf_token field (see templates). Tokens
# are signed with SECRET_KEY, so a strong key is required in production.
csrf = CSRFProtect(app)

# Rate limiting / brute-force protection (Step D). Keyed by client IP. No global
# default limits — each sensitive route opts in with @limiter.limit(...). Uses
# in-memory storage by default; point RATELIMIT_STORAGE_URI at Redis in prod so
# limits are shared across workers/hosts.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri=RATELIMIT_STORAGE_URI,
    headers_enabled=True,
)
limiter.enabled = RATELIMIT_ENABLED


def get_request_id():
    return getattr(g, "request_id", "-")


def get_remote_client_addr():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.remote_addr or ""


def request_log_extra(status=None, duration_ms=None, error_type=None):
    extra = {
        "request_id": get_request_id(),
        "method": request.method,
        "path": request.path,
        "remote_addr": get_remote_client_addr(),
    }
    if status is not None:
        extra["status"] = status
    if duration_ms is not None:
        extra["duration_ms"] = duration_ms
    if error_type is not None:
        extra["error_type"] = error_type
    return extra


@app.before_request
def start_request_log_context():
    g.request_id = uuid.uuid4().hex[:12]
    g.request_started_at = time.perf_counter()
    if sentry_sdk.is_initialized():
        sentry_sdk.set_tag("request_id", g.request_id)


@app.after_request
def log_request_completion(response):
    started_at = getattr(g, "request_started_at", None)
    duration_ms = None
    if started_at is not None:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)

    response.headers.setdefault("X-Request-ID", get_request_id())
    level = logging.WARNING if 400 <= response.status_code < 500 else logging.INFO
    request_logger.log(
        level,
        "request_completed",
        extra=request_log_extra(
            status=response.status_code,
            duration_ms=duration_ms,
        ),
    )
    return response


def log_unhandled_exception(sender, exception, **extra):
    error_logger.error(
        "unhandled_exception",
        exc_info=(type(exception), exception, exception.__traceback__),
        extra=request_log_extra(error_type=type(exception).__name__),
    )


got_request_exception.connect(log_unhandled_exception, app)


@app.after_request
def add_security_headers(response):
    if HSTS_ENABLED and request.is_secure:
        response.headers.setdefault("Strict-Transport-Security", hsts_header_value())

    return response


@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    # A missing/expired/invalid token lands here instead of a raw 400 page.
    return render_template(
        "login.html",
        error="Your session expired or the form was invalid. Please try again.",
    ), 400


@app.errorhandler(429)
def handle_rate_limit(error):
    # Flask-Limiter raises a 429 when a limit is exceeded. Show a clear,
    # friendly page instead of a raw error.
    return render_template("rate_limited.html"), 429


class Database:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, params=None):
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


def get_db():
    if "db" not in g: # g is for Global, it is a 
        # special object that Flask provides to store data during the 
        # request lifecycle.
        connection = psycopg2.connect(
            DATABASE_URL,
            connect_timeout=5,
            cursor_factory=RealDictCursor,
        )
        g.db = Database(connection)
        # This allows us to access columns by name.
    return g.db

# Schema is owned by Alembic migrations (see migrations/versions/). The former
# ensure_transaction_columns / ensure_barcode_sequence / ensure_auth_columns
# runtime shims — which issued ALTER TABLE / CREATE INDEX / CREATE SEQUENCE on
# ordinary requests — have been removed. All the columns, defaults, the
# item_barcode_number_seq sequence, and the users_email_key unique index they
# used to guarantee are created by the baseline migration (0001_baseline).
# Apply schema with `alembic upgrade head` (production) or `flask init-db`
# (local dev bootstrap via schema.sql).

def generate_next_item_barcode(db):
    # Draw the next unique number from the PostgreSQL sequence and format it as
    # a zero-padded internal code (e.g. KATZ-NURS-000001). The sequence
    # (item_barcode_number_seq) is created by the baseline migration.
    return barcode_generate_next_item_barcode(db, BARCODE_PREFIX)

def hash_password(raw_password):
    # Werkzeug salts and hashes the password (PBKDF2 by default). The raw
    # password is never stored.
    return password_hash_password(raw_password)

def verify_password(password_hash, raw_password):
    # A NULL/empty hash means the user was invited but has not set a password
    # yet, so they cannot authenticate.
    return password_verify_password(password_hash, raw_password)

def validate_password_strength(raw_password):
    # Returns an error message string, or None if the password is acceptable.
    return password_validate_password_strength(raw_password, MIN_PASSWORD_LENGTH)

# In-memory failed-login tracker keyed by email. Per-process only (resets on
# restart and is not shared across workers) — intentionally a lightweight
# cooldown, not the primary brute-force defense (that is Step D / Flask-Limiter).
_login_attempts = {}

def is_locked_out(email):
    record = _login_attempts.get(email)
    if not record:
        return False
    locked_until = record.get("locked_until")
    if locked_until is None:
        return False
    if time.time() < locked_until:
        return True
    # Cooldown elapsed: forget the email so it starts fresh.
    _login_attempts.pop(email, None)
    return False

def record_failed_login(email):
    record = _login_attempts.setdefault(email, {"count": 0, "locked_until": None})
    record["count"] += 1
    if record["count"] >= LOGIN_MAX_ATTEMPTS:
        record["locked_until"] = time.time() + LOGIN_LOCKOUT_SECONDS

def clear_failed_login(email):
    # Called on a successful login so a legitimate user is not penalized for
    # earlier typos.
    _login_attempts.pop(email, None)

def remaining_login_attempts(email):
    # How many attempts remain for this email before the cooldown kicks in.
    record = _login_attempts.get(email)
    if not record:
        return LOGIN_MAX_ATTEMPTS
    return max(0, LOGIN_MAX_ATTEMPTS - record["count"])

def get_token_serializer():
    # Tokens are signed with SECRET_KEY. Rotating SECRET_KEY invalidates every
    # outstanding invite/reset link, which is the desired safety behavior.
    return URLSafeTimedSerializer(app.config["SECRET_KEY"])

def make_token(user_id, purpose):
    # Build a signed, self-describing token for a one-off action link. The
    # purpose ("invite" or "reset") is embedded so a token minted for one flow
    # cannot be replayed against another.
    return token_make_token(get_token_serializer(), user_id, purpose)

def read_token(token, purpose, max_age):
    # Return the user_id if the token is valid, unexpired, and was minted for
    # this exact purpose; otherwise return None. Any tampering, expiry, or
    # purpose mismatch is treated the same way (rejected).
    return token_read_token(get_token_serializer(), token, purpose, max_age)

def send_email(to, subject, body):
    # Deliver a transactional email (invite / password reset). Returns True when
    # the message was handed off.
    #
    # No provider configured (development): log the full message so the link is
    # visible in the server console and flows can be tested without external mail.
    #
    # Provider configured: send through SMTP using environment variables.
    return email_send_email(
        to,
        subject,
        body,
        provider=EMAIL_PROVIDER,
        email_from=EMAIL_FROM,
        smtp_host=SMTP_HOST,
        smtp_port=SMTP_PORT,
        smtp_username=SMTP_USERNAME,
        smtp_password=SMTP_PASSWORD,
        smtp_use_tls=SMTP_USE_TLS,
        smtp_use_ssl=SMTP_USE_SSL,
        app_env=APP_ENV,
        logger=app.logger,
    )

def send_invite(user_id, email):
    # Email a "set your password" link for a newly created or re-invited user.
    # Must be called within a request context (uses the request host as a
    # fallback base URL, mirroring the QR-code link builder).
    token = make_token(user_id, "invite")
    base_url = APP_BASE_URL or request.host_url.rstrip("/")
    link = f"{base_url}{url_for('set_password', token=token)}"
    sent = send_email(
        email,
        "Set your Katz Nursing Inventory password",
        "You have been invited to the Katz Nursing Inventory system.\n\n"
        f"Set your password using this link (valid for 72 hours):\n{link}\n",
    )
    return {"sent": sent, "link": link}

def send_reset(user_id, email):
    # Email a password-reset link. Must be called within a request context.
    token = make_token(user_id, "reset")
    base_url = APP_BASE_URL or request.host_url.rstrip("/")
    link = f"{base_url}{url_for('reset_password', token=token)}"
    sent = send_email(
        email,
        "Reset your Katz Nursing Inventory password",
        "We received a request to reset your password.\n\n"
        f"Reset it using this link (valid for 1 hour):\n{link}\n\n"
        "If you did not request this, you can ignore this email.\n",
    )
    return {"sent": sent, "link": link}

def require_login():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return None

def mark_sudo():
    # Record that the user proved their password just now (login or re-auth).
    session["sudo_at"] = int(time.time())

def has_fresh_sudo():
    sudo_at = session.get("sudo_at")
    if sudo_at is None:
        return False
    return (time.time() - sudo_at) <= SUDO_MODE_MAX_AGE

def safe_next(target, fallback_endpoint="admin_users"):
    # Only allow same-site relative paths as post-re-auth redirect targets, so
    # the ?next= parameter cannot be used for an open redirect.
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for(fallback_endpoint)

def require_sudo():
    # Gate a destructive action behind a recent password re-entry. Returns a
    # redirect (to login or the re-auth page) when the caller must stop, or None
    # when the action may proceed.
    login_redirect = require_login()
    if login_redirect is not None:
        return login_redirect

    if not has_fresh_sudo():
        return redirect(url_for("reauth", next=url_for("admin_users")))

    return None

def require_admin():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    if session.get("user_role") not in ELEVATED_ROLES:
        return redirect(url_for("dashboard"))

    return None

def require_system_admin():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    if session.get("user_role") != "administrator":
        return redirect(url_for("dashboard"))

    return None

def require_item_manager():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    if session.get("user_role") not in ELEVATED_ROLES:
        return redirect(url_for("items"))

    return None

def allowed_user_roles_to_manage():
    if session.get("user_role") == "administrator":
        return {"student", "faculty"}

    if session.get("user_role") == "faculty":
        return {"student"}

    return set()

def can_manage_user_role(role):
    return role in allowed_user_roles_to_manage()

def parse_expiration_date(value):
    """Parse a submitted expiration value into a date, or None when unset.

    The <input type="date"> field submits ISO (YYYY-MM-DD); a couple of other
    common formats are accepted defensively. Empty / unparseable -> None, which
    is stored as SQL NULL ("no expiration recorded"). The old '00/00/0000'
    sentinel is gone -- an unset date is NULL now.
    """
    return forms_parse_expiration_date(value)

def get_item_form_data(require_barcode=True):
    expiration_date = parse_expiration_date(request.form.get("expiration_date", ""))

    data = {
        "barcode": request.form.get("barcode", "").strip(),
        "name": request.form.get("name", "").strip(),
        "bin_location": request.form.get("bin_location", "").strip(),
        "room": request.form.get("room", "").strip(),
        "company": request.form.get("company", "").strip(),
        "location": request.form.get("location", "").strip(),
        "expiration_date": expiration_date,
        "notes": request.form.get("notes", "").strip(),
    }

    try:
        data["quantity"] = int(request.form.get("quantity", "0"))
        data["minimum_quantity"] = int(request.form.get("minimum_quantity", "0"))
    except ValueError:
        data["quantity"] = 0
        data["minimum_quantity"] = 0
        return data, "Quantity values must be numbers."

    # On Add Item the barcode is optional: a blank barcode is auto-generated by
    # the caller. Editing still requires an explicit barcode.
    if require_barcode and not data["barcode"]:
        return data, "Barcode, name, bin location, and room are required."

    if not data["name"] or not data["bin_location"] or not data["room"]:
        if require_barcode:
            return data, "Barcode, name, bin location, and room are required."
        return data, "Name, bin location, and room are required."

    if data["quantity"] < 0 or data["minimum_quantity"] < 0:
        return data, "Quantity values cannot be negative."

    return data, None

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()

def _alembic_config():
    # Build an Alembic config pointed at the project's alembic.ini. The database
    # URL is not set here: migrations/env.py reads DATABASE_URL from the
    # environment (the same variable the app uses), so the CLI and the app always
    # target the same database. Imported lazily so the web-serving process never
    # imports Alembic.
    from alembic.config import Config as AlembicConfig

    return AlembicConfig(str(BASE_DIR / "alembic.ini"))


@app.cli.command("check-config")
def check_config_command():
    """Print production configuration status without exposing secret values."""
    checks = []

    def add(name, ok, detail):
        checks.append((name, ok, detail))

    add("APP_ENV", APP_ENV == "production", "production" if APP_ENV == "production" else "not production")
    add("SECRET_KEY", bool(SECRET_KEY), "set" if SECRET_KEY else "missing")
    add(
        "SECRET_KEY_LENGTH",
        bool(SECRET_KEY) and len(SECRET_KEY) >= MIN_PRODUCTION_SECRET_KEY_LENGTH,
        f">= {MIN_PRODUCTION_SECRET_KEY_LENGTH} chars" if SECRET_KEY and len(SECRET_KEY) >= MIN_PRODUCTION_SECRET_KEY_LENGTH else "too short or missing",
    )
    add(
        "SECRET_KEY_NOT_DEV_FALLBACK",
        SECRET_KEY != DEV_SECRET_KEY,
        "ok" if SECRET_KEY != DEV_SECRET_KEY else "uses development fallback",
    )
    add("DATABASE_URL", bool(os.environ.get("DATABASE_URL")), "set" if os.environ.get("DATABASE_URL") else "missing")
    add("APP_BASE_URL", bool(APP_BASE_URL), "set" if APP_BASE_URL else "missing")

    if EMAIL_PROVIDER == "smtp":
        add("EMAIL_PROVIDER", True, "smtp")
        add("EMAIL_FROM", bool(EMAIL_FROM), "set" if EMAIL_FROM else "missing")
        add("SMTP_HOST", bool(SMTP_HOST), "set" if SMTP_HOST else "missing")
        add("SMTP_PORT", bool(SMTP_PORT), "set" if SMTP_PORT else "missing")
        add("SMTP_USERNAME", bool(SMTP_USERNAME), "set" if SMTP_USERNAME else "missing")
        add("SMTP_PASSWORD", bool(SMTP_PASSWORD), "set" if SMTP_PASSWORD else "missing")
    else:
        add("EMAIL_PROVIDER", False, "smtp required in production")

    add("SESSION_COOKIE_SECURE", app.config["SESSION_COOKIE_SECURE"], "enabled" if app.config["SESSION_COOKIE_SECURE"] else "disabled")
    add("SESSION_COOKIE_HTTPONLY", app.config["SESSION_COOKIE_HTTPONLY"], "enabled" if app.config["SESSION_COOKIE_HTTPONLY"] else "disabled")
    add("SESSION_COOKIE_SAMESITE", bool(app.config["SESSION_COOKIE_SAMESITE"]), "set" if app.config["SESSION_COOKIE_SAMESITE"] else "missing")
    add("PROXY_FIX_ENABLED", PROXY_FIX_ENABLED, "enabled" if PROXY_FIX_ENABLED else "disabled")
    add("HSTS_ENABLED", HSTS_ENABLED, "enabled" if HSTS_ENABLED else "disabled")
    add("HSTS_MAX_AGE", HSTS_MAX_AGE > 0, str(HSTS_MAX_AGE))
    add("SENTRY_DSN", True, "set" if SENTRY_DSN else "not configured")
    add("SENTRY_TRACES_SAMPLE_RATE", 0.0 <= SENTRY_TRACES_SAMPLE_RATE <= 1.0, str(SENTRY_TRACES_SAMPLE_RATE))
    add("RATELIMIT_ENABLED", RATELIMIT_ENABLED, "enabled" if RATELIMIT_ENABLED else "disabled")
    add(
        "RATELIMIT_STORAGE_URI",
        bool(RATELIMIT_STORAGE_URI),
        "set; memory:// is single-process only" if RATELIMIT_STORAGE_URI == "memory://" else "set",
    )

    has_errors = False
    click.echo("Production configuration check")
    for name, ok, detail in checks:
        status = "OK" if ok else "MISSING/ATTENTION"
        click.echo(f"- {name}: {status} ({detail})")
        if APP_ENV == "production" and not ok:
            has_errors = True

    if APP_ENV == "production" and RATELIMIT_STORAGE_URI == "memory://":
        click.echo("- RATELIMIT_STORAGE_URI: ATTENTION (use Redis/shared storage for multi-worker or multi-host production)")

    if has_errors:
        raise click.ClickException("Production configuration is incomplete.")


@app.cli.command("init-db")
def init_db_command():
    """Bootstrap a LOCAL DEV database from schema.sql (includes demo users).

    This is a convenience for local development only. Production and any shared
    database should be managed with migrations instead:  `flask db-upgrade`
    (i.e. `alembic upgrade head`). Do not use init-db to manage a database that
    is under Alembic control -- it would recreate tables from schema.sql.
    """
    db = get_db()

    with SCHEMA.open("r") as schema_file:
        db.execute(schema_file.read())

    db.commit()

    # schema.sql builds the complete schema for local dev; production schema is
    # managed by Alembic (`flask db-upgrade` / `alembic upgrade head`).
    click.echo("Initialized the PostgreSQL inventory database (local dev bootstrap).")

@app.cli.command("db-upgrade")
@click.argument("revision", default="head")
def db_upgrade_command(revision):
    """Apply database migrations (default: upgrade to 'head').

    This is the production/shared-database schema command and the one to run in
    the deploy release phase, before the new app version serves traffic. It wraps
    `alembic upgrade <revision>` so operators have one consistent interface.
    """
    from alembic import command as alembic_command

    alembic_command.upgrade(_alembic_config(), revision)
    click.echo(f"Database upgraded to {revision}.")

@app.cli.command(
    "db-downgrade",
    context_settings={"ignore_unknown_options": True},
)
@click.argument("revision")
def db_downgrade_command(revision):
    """Roll back database migrations (e.g. `flask db-downgrade -1`).

    Wraps `alembic downgrade <revision>`. Use with care on a real database; test
    on a scratch copy first.
    """
    from alembic import command as alembic_command

    alembic_command.downgrade(_alembic_config(), revision)
    click.echo(f"Database downgraded to {revision}.")

@app.cli.command("set-password")
@click.argument("email")
@click.argument("password")
def set_password_command(email, password):
    """Set (or reset) a user's password by email. Used to bootstrap accounts."""
    db = get_db()

    error = validate_password_strength(password)
    if error:
        raise click.ClickException(error)

    cursor = db.execute(
        "UPDATE users SET password_hash = %s WHERE email = %s",
        (hash_password(password), email),
    )
    db.commit()

    if cursor.rowcount == 0:
        raise click.ClickException(f"No user found with email {email}.")

    click.echo(f"Password set for {email}.")

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/health")
def health():
    try:
        get_db().execute("SELECT 1").fetchone()
    except Exception:
        return jsonify({"status": "error", "database": "error"}), 503

    return jsonify({"status": "ok", "database": "ok"})

@app.route("/login", methods=["GET", "POST"])
@limiter.limit(RATELIMIT_LOGIN, methods=["POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Refuse further attempts once an email has failed too many times in a
        # row, until the cooldown elapses. Generic message, no enumeration.
        if is_locked_out(email):
            return render_template(
                "login.html",
                error="Too many failed attempts. Please try again later.",
            ), 429

        db = get_db()
        user = db.execute(
            """
            SELECT id, email, name, role, password_hash
            FROM users
            WHERE LOWER(email) = %s AND is_active = TRUE
            """,
            (email,),
        ).fetchone()

        # One generic message for every failure (unknown email, wrong password,
        # inactive account, or an invited user who has not set a password yet)
        # so we never reveal which emails are registered.
        if user is None or not verify_password(user["password_hash"], password):
            record_failed_login(email)
            # Warn on the final remaining try so the user is not surprised by the
            # lockout. Shown for any email (not just registered ones), so it does
            # not reveal whether the email exists.
            warning = None
            if remaining_login_attempts(email) == 1:
                warning = "This is your last attempt before your account is temporarily locked."
            return render_template(
                "login.html",
                error="Invalid email or password.",
                warning=warning,
            ), 401

        clear_failed_login(email)

        db.execute(
            "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = %s",
            (user["id"],),
        )
        db.commit()

        # Clear any existing session data before establishing the new one to
        # avoid session fixation. Privileges derive solely from the account role.
        session.clear()
        # Mark permanent so PERMANENT_SESSION_LIFETIME (idle timeout) applies.
        session.permanent = True
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_role"] = user["role"]
        session["email"] = user["email"]
        # A fresh login counts as a recent password proof for "sudo mode".
        mark_sudo()

        return redirect(url_for("dashboard"))

    return render_template("login.html")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/reauth", methods=["GET", "POST"])
def reauth():
    # Confirm the logged-in user's password before a destructive admin action
    # ("sudo mode"). This protects shared/lab computers where a session may be
    # left open.
    login_redirect = require_login()
    if login_redirect is not None:
        return login_redirect

    next_url = safe_next(request.values.get("next"))

    if request.method == "POST":
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute(
            "SELECT password_hash FROM users WHERE id = %s AND is_active = TRUE",
            (session.get("user_id"),),
        ).fetchone()

        if user is None or not verify_password(user["password_hash"], password):
            return render_template(
                "reauth.html",
                next=next_url,
                error="Incorrect password.",
            ), 401

        mark_sudo()
        return redirect(next_url)

    return render_template("reauth.html", next=next_url)

@app.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit(RATELIMIT_PASSWORD, methods=["POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        db = get_db()
        user = db.execute(
            "SELECT id, email FROM users WHERE LOWER(email) = %s AND is_active = TRUE",
            (email,),
        ).fetchone()

        if user is not None:
            try:
                reset = send_reset(user["id"], user["email"])
            except Exception as error:
                app.logger.exception("Password reset email failed for %s", user["email"])
                flash(
                    "Password reset email could not be sent. Please check email "
                    f"settings and try again. Error: {error}",
                    "error",
                )
            else:
                if reset["sent"]:
                    flash("Password reset email sent.", "success")
                else:
                    flash(
                        "Email is not configured locally, so no message was sent. "
                        f"Reset link: {reset['link']}",
                        "warning",
                    )

        # Always show the same confirmation, whether or not the email matched a
        # real account, so the form cannot be used to discover registered emails.
        return render_template("forgot_password.html", sent=True)

    return render_template("forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit(RATELIMIT_PASSWORD, methods=["POST"])
def reset_password(token):
    # No login required: the signed "reset" token is the credential.
    user_id = read_token(token, "reset", RESET_TOKEN_MAX_AGE)

    if user_id is None:
        return render_template("reset_password.html", invalid=True), 400

    db = get_db()
    user = db.execute(
        "SELECT id, email FROM users WHERE id = %s AND is_active = TRUE",
        (user_id,),
    ).fetchone()

    if user is None:
        return render_template("reset_password.html", invalid=True), 400

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        error = validate_password_strength(password)
        if not error and password != confirm_password:
            error = "Passwords do not match."

        if error:
            return render_template("reset_password.html", token=token, error=error), 400

        db.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hash_password(password), user["id"]),
        )
        db.commit()

        return redirect(url_for("login"))

    return render_template("reset_password.html", token=token)

@app.route("/dashboard")
def dashboard():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    total_items = db.execute("SELECT COUNT(*) AS total FROM items").fetchone()["total"]
    low_stock_items = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM items
        WHERE quantity <= minimum_quantity
        """
    ).fetchone()["total"]
    total_transactions = db.execute("SELECT COUNT(*) AS total FROM transactions").fetchone()["total"]
    recent_transactions = db.execute(
        """
        SELECT
            transactions.transaction_type,
            transactions.quantity,
            TO_CHAR(transactions.transaction_date, 'YYYY-MM-DD') AS transaction_date,
            TO_CHAR(transactions.transaction_time, 'HH24:MI:SS') AS transaction_time,
            transactions.lab_instructor,
            transactions.topic_of_day,
            items.name AS item_name,
            users.name AS user_name
        FROM transactions
        JOIN items ON items.id = transactions.item_id
        JOIN users ON users.id = transactions.user_id
        ORDER BY transactions.transaction_date DESC, transactions.transaction_time DESC, transactions.id DESC
        LIMIT 5
        """
    ).fetchall()

    return render_template(
        "dashboard.html",
        total_items=total_items,
        low_stock_items=low_stock_items,
        total_transactions=total_transactions,
        recent_transactions=recent_transactions,
    )

@app.route("/items")
def items():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    inventory_items = db.execute(
        """
        SELECT id, barcode, name, bin_location, room, company, quantity, minimum_quantity
        FROM items
        ORDER BY name
        """
    ).fetchall()

    return render_template("items.html", items=inventory_items)

@app.route("/items/low-stock")
def low_stock_items():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    inventory_items = db.execute(
        """
        SELECT id, barcode, name, bin_location, room, company, quantity, minimum_quantity
        FROM items
        WHERE quantity <= minimum_quantity
        ORDER BY quantity ASC, name
        """
    ).fetchall()

    return render_template("low_stock_items.html", items=inventory_items)

@app.route("/items/<barcode>")
def item_detail(barcode):
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    item = db.execute(
        """
        SELECT
            id,
            barcode,
            name,
            bin_location,
            room,
            company,
            quantity,
            minimum_quantity,
            location,
            expiration_date,
            notes
        FROM items
        WHERE barcode = %s
        """,
        (barcode,),
    ).fetchone()

    if item is None:
        abort(404, description="Not recognized")

    return render_template("item_detail.html", item=item)

@app.route("/items/<barcode>/qr.png")
def item_qr_png(barcode):
    login_redirect = require_item_manager()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    item = db.execute(
        "SELECT id FROM items WHERE barcode = %s",
        (barcode,),
    ).fetchone()

    if item is None:
        abort(404, description="Not recognized")

    # Build the URL the QR code points to: the per-item stock page. Prefer the
    # configured public base URL; fall back to the current request host in dev.
    # The path is assembled as a string (not url_for) because the stock route
    # is added in a later step, and this route must work before that exists.
    base_url = APP_BASE_URL or request.host_url.rstrip("/")
    stock_url = f"{base_url}/items/{barcode}/stock"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(stock_url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    return Response(buffer.getvalue(), mimetype="image/png")

@app.route("/items/<barcode>/label")
def item_label(barcode):
    login_redirect = require_item_manager()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    item = db.execute(
        """
        SELECT barcode, name, room, bin_location, company, expiration_date
        FROM items
        WHERE barcode = %s
        """,
        (barcode,),
    ).fetchone()

    if item is None:
        abort(404, description="Not recognized")

    return render_template("item_label.html", item=item)

@app.route("/items/new", methods=["GET", "POST"])
def item_new():
    manager_redirect = require_item_manager()

    if manager_redirect is not None:
        return manager_redirect

    if request.method == "POST":
        item_data, error = get_item_form_data(require_barcode=False)

        if error:
            return render_template("item_new.html", error=error, item=item_data), 400

        db = get_db()

        # Blank barcode means the user wants an auto-generated internal code.
        if not item_data["barcode"]:
            item_data["barcode"] = generate_next_item_barcode(db)

        try:
            db.execute(
                """
                INSERT INTO items (
                    barcode, name, bin_location, room, company,
                    quantity, minimum_quantity, location, expiration_date, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    item_data["barcode"],
                    item_data["name"],
                    item_data["bin_location"],
                    item_data["room"],
                    item_data["company"],
                    item_data["quantity"],
                    item_data["minimum_quantity"],
                    item_data["location"],
                    item_data["expiration_date"],
                    item_data["notes"],
                ),
            )
            db.commit()
        except psycopg2.IntegrityError:
            db.rollback()
            return render_template(
                "item_new.html",
                error="An item with this barcode already exists.",
                item=item_data,
            ), 400

        return redirect(url_for("items"))

    return render_template("item_new.html", item={})

@app.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
def item_edit(item_id):
    manager_redirect = require_item_manager()

    if manager_redirect is not None:
        return manager_redirect

    db = get_db()
    item = db.execute(
        """
        SELECT
            id,
            barcode,
            name,
            bin_location,
            room,
            company,
            quantity,
            minimum_quantity,
            location,
            expiration_date,
            notes
        FROM items
        WHERE id = %s
        """,
        (item_id,),
    ).fetchone()

    if item is None:
        abort(404)

    if request.method == "POST":
        item_data, error = get_item_form_data()

        if error:
            item_data["id"] = item_id
            return render_template("item_edit.html", error=error, item=item_data), 400

        try:
            db.execute(
                """
                UPDATE items
                SET
                    barcode = %s,
                    name = %s,
                    bin_location = %s,
                    room = %s,
                    company = %s,
                    quantity = %s,
                    minimum_quantity = %s,
                    location = %s,
                    expiration_date = %s,
                    notes = %s
                WHERE id = %s
                """,
                (
                    item_data["barcode"],
                    item_data["name"],
                    item_data["bin_location"],
                    item_data["room"],
                    item_data["company"],
                    item_data["quantity"],
                    item_data["minimum_quantity"],
                    item_data["location"],
                    item_data["expiration_date"],
                    item_data["notes"],
                    item_id,
                ),
            )
            db.commit()
        except psycopg2.IntegrityError:
            db.rollback()
            item_data["id"] = item_id
            return render_template(
                "item_edit.html",
                error="An item with this barcode already exists.",
                item=item_data,
            ), 400

        return redirect(url_for("items"))

    return render_template("item_edit.html", item=item)

def process_stock_transaction(barcode, form):
    """Validate and apply one add/remove stock transaction.

    Reads action/quantity/instructor/topic/notes from `form`, validates them,
    finds the item by `barcode`, updates its quantity, and records a
    transaction row for the logged-in user. Returns a
    (message, error, status_code) tuple where exactly one of message/error is
    set. Shared by /scan and the per-item QR stock page so both behave
    identically.
    """
    transaction_type = form.get("transaction_type", "").strip()
    lab_instructor = form.get("lab_instructor", "").strip()
    topic_of_day = form.get("topic_of_day", "").strip()
    notes = form.get("notes", "").strip()

    try:
        quantity = int(form.get("quantity", "1"))
    except ValueError:
        return None, "Quantity must be a number.", 400

    if not barcode:
        return None, "Barcode is required.", 400

    if transaction_type not in {"add", "remove"}:
        return None, "Choose Add Stock or Remove Stock.", 400

    if quantity <= 0:
        return None, "Quantity must be greater than zero.", 400

    # Every entry must be filled before a transaction is recorded. The form
    # marks these required, but an accidental Enter (e.g. from a barcode
    # scanner) can bypass client-side checks, so enforce it here too.
    if not lab_instructor:
        return None, "Lab Instructor is required.", 400

    if not topic_of_day:
        return None, "Topic of the Day is required.", 400

    if not notes:
        return None, "Notes are required.", 400

    db = get_db()
    item = db.execute(
        """
        SELECT id, name, quantity
        FROM items
        WHERE barcode = %s
        """,
        (barcode,),
    ).fetchone()

    if item is None:
        return None, "No item was found for that barcode.", 404

    if transaction_type == "remove" and quantity > item["quantity"]:
        return None, f"Cannot remove {quantity}. Only {item['quantity']} available.", 400

    if transaction_type == "add":
        new_quantity = item["quantity"] + quantity
    else:
        new_quantity = item["quantity"] - quantity

    db.execute(
        """
        UPDATE items
        SET quantity = %s
        WHERE id = %s
        """,
        (new_quantity, item["id"]),
    )
    db.execute(
        """
        INSERT INTO transactions (
            user_id, item_id, transaction_type, quantity,
            lab_instructor, topic_of_day, notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            session["user_id"],
            item["id"],
            transaction_type,
            quantity,
            lab_instructor,
            topic_of_day,
            notes,
        ),
    )
    db.commit()

    return f"{item['name']} updated successfully. New quantity: {new_quantity}.", None, 200

@app.route("/scan", methods=["GET", "POST"])
@limiter.limit(RATELIMIT_STOCK)
def scan():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    if request.method == "POST":
        message, error, status = process_stock_transaction(
            request.form.get("barcode", "").strip(),
            request.form,
        )

        if error:
            return render_template("scan.html", error=error), status

        return render_template("scan.html", message=message)

    return render_template("scan.html")

def get_stock_item(db, barcode):
    return db.execute(
        """
        SELECT id, barcode, name, room, bin_location, quantity
        FROM items
        WHERE barcode = %s
        """,
        (barcode,),
    ).fetchone()

@app.route("/items/<barcode>/stock", methods=["GET", "POST"])
@limiter.limit(RATELIMIT_STOCK)
def item_stock(barcode):
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    item = get_stock_item(db, barcode)

    if item is None:
        abort(404, description="Not recognized")

    if request.method == "POST":
        # The barcode is taken from the URL, not a form field, so it cannot be
        # tampered with from the browser and the route already identifies the item.
        message, error, status = process_stock_transaction(barcode, request.form)
        # Re-read so the page reflects the current quantity after the update.
        item = get_stock_item(db, barcode)

        if error:
            return render_template("item_stock.html", item=item, error=error), status

        return render_template("item_stock.html", item=item, message=message)

    return render_template("item_stock.html", item=item)

def get_transaction_filters():
    return {
        "date_from": request.args.get("date_from", "").strip(),
        "date_to": request.args.get("date_to", "").strip(),
        "item_id": request.args.get("item_id", "").strip(),
        "user_id": request.args.get("user_id", "").strip(),
        "lab_instructor": request.args.get("lab_instructor", "").strip(),
        "topic_of_day": request.args.get("topic_of_day", "").strip(),
        "transaction_type": request.args.get("transaction_type", "").strip(),
    }

def build_transaction_filter_clause(filters):
    return transaction_build_filter_clause(filters)

def count_transaction_rows(db, filters):
    # Total matching rows, used to render pagination controls. The filter clause
    # only references transactions.* columns, so no JOINs are needed here.
    return transaction_count_rows(db, filters)

def get_transaction_rows(db, filters, limit=None, offset=None):
    # limit/offset are for the on-screen paginated list. The CSV export calls
    # this WITHOUT them so it returns the full filtered result set.
    return transaction_get_rows(db, filters, limit=limit, offset=offset)

def get_transaction_filter_options(db):
    items = db.execute(
        """
        SELECT id, name, barcode
        FROM items
        ORDER BY name, barcode
        """
    ).fetchall()
    users = db.execute(
        """
        SELECT id, name, institution_id
        FROM users
        ORDER BY name, institution_id
        """
    ).fetchall()
    lab_instructors = db.execute(
        """
        SELECT DISTINCT lab_instructor
        FROM transactions
        WHERE NULLIF(BTRIM(lab_instructor), '') IS NOT NULL
        ORDER BY lab_instructor
        """
    ).fetchall()
    topics = db.execute(
        """
        SELECT DISTINCT topic_of_day
        FROM transactions
        WHERE NULLIF(BTRIM(topic_of_day), '') IS NOT NULL
        ORDER BY topic_of_day
        """
    ).fetchall()

    return items, users, lab_instructors, topics

@app.route("/transactions")
def transactions():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    db = get_db()

    filters = get_transaction_filters()
    items, users, lab_instructors, topics = get_transaction_filter_options(db)

    export_params = {key: value for key, value in filters.items() if value}

    # Server-side pagination. Total drives the controls; page is clamped so an
    # out-of-range ?page= (e.g. after tightening a filter) lands on a valid page.
    total = count_transaction_rows(db, filters)
    page_size = TRANSACTIONS_PAGE_SIZE
    total_pages = max(1, (total + page_size - 1) // page_size)

    try:
        page = int(request.args.get("page", "1"))
    except ValueError:
        page = 1
    page = max(1, min(page, total_pages))

    offset = (page - 1) * page_size
    transaction_rows = get_transaction_rows(
        db, filters, limit=page_size, offset=offset
    )

    # Page links carry the active filters (but not the old page number) so
    # navigation preserves filters; submitting the filter form omits ?page= and
    # therefore resets to page 1.
    prev_url = (
        url_for("transactions", page=page - 1, **export_params)
        if page > 1
        else None
    )
    next_url = (
        url_for("transactions", page=page + 1, **export_params)
        if page < total_pages
        else None
    )

    return render_template(
        "transactions.html",
        transactions=transaction_rows,
        filters=filters,
        items=items,
        users=users,
        lab_instructors=lab_instructors,
        topics=topics,
        export_url=url_for("export_transactions", **export_params),
        page=page,
        total_pages=total_pages,
        total=total,
        page_size=page_size,
        has_prev=page > 1,
        has_next=page < total_pages,
        prev_url=prev_url,
        next_url=next_url,
    )

@app.route("/transactions/export")
def export_transactions():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    transaction_rows = get_transaction_rows(db, get_transaction_filters())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Date",
            "Time",
            "Action",
            "Item",
            "Barcode",
            "Quantity",
            "Lab Instructor",
            "Topic",
            "User",
            "Notes",
        ]
    )

    for transaction in transaction_rows:
        writer.writerow(
            [
                transaction["transaction_date"],
                transaction["transaction_time"],
                transaction["transaction_type"],
                transaction["item_name"],
                transaction["barcode"],
                transaction["quantity"],
                transaction["lab_instructor"],
                transaction["topic_of_day"],
                transaction["user_name"],
                transaction["notes"],
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=transaction_history_export.csv"},
    )

@app.route("/reports/export")
def export_inventory():
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    db = get_db()
    inventory_items = db.execute(
        """
        SELECT
            barcode,
            name,
            bin_location,
            room,
            company,
            quantity,
            minimum_quantity,
            location,
            expiration_date,
            notes
        FROM items
        ORDER BY name
        """
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Barcode",
            "Item Name",
            "Bin Location",
            "Room",
            "Vendor",
            "Quantity",
            "Minimum Quantity",
            "General Location",
            "Expiration Date",
            "Notes",
        ]
    )

    for item in inventory_items:
        writer.writerow(
            [
                item["barcode"],
                item["name"],
                item["bin_location"],
                item["room"],
                item["company"],
                item["quantity"],
                item["minimum_quantity"],
                item["location"],
                item["expiration_date"],
                item["notes"],
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory_export.csv"},
    )

@app.route("/admin/users")
def admin_users():
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    db = get_db()
    users = db.execute(
        """
        SELECT
            id,
            institution_id,
            email,
            name,
            role,
            department,
            is_active,
            password_hash IS NULL AS invite_pending,
            (
                SELECT COUNT(*)
                FROM transactions
                WHERE transactions.user_id = users.id
            ) AS transaction_count
        FROM users
        ORDER BY name
        """
    ).fetchall()

    return render_template(
        "admin_users.html",
        users=users,
        can_manage_user_role=can_manage_user_role,
    )

@app.route("/admin/users/new", methods=["GET", "POST"])
def admin_user_new():
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    allowed_roles = allowed_user_roles_to_manage()
    role_options = [
        ("student", "Student"),
        ("faculty", "Faculty"),
    ]
    role_options = [role for role in role_options if role[0] in allowed_roles]

    if request.method == "POST":
        institution_id = request.form.get("institution_id", "").strip()
        email = request.form.get("email", "").strip().lower()
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "").strip()
        department = request.form.get("department", "").strip()

        if not email or not name or role not in allowed_roles:
            return render_template(
                "user_new.html",
                error="Name, email, and an allowed role are required.",
                role_options=role_options,
            ), 400

        db = get_db()

        try:
            # password_hash is left NULL: the account is "invited" until the
            # user sets a password via the emailed link. institution_id is
            # optional, so store NULL (not "") when blank to avoid collisions.
            new_user = db.execute(
                """
                INSERT INTO users (institution_id, email, name, role, department)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (institution_id or None, email, name, role, department),
            ).fetchone()
            db.commit()
        except psycopg2.IntegrityError:
            db.rollback()
            return render_template(
                "user_new.html",
                error="A user with this email or institution ID already exists.",
                role_options=role_options,
            ), 400

        try:
            invite = send_invite(new_user["id"], email)
        except Exception as error:
            app.logger.exception("Invite email failed for %s", email)
            flash(
                "User was created, but the invite email could not be sent. "
                f"Please check email settings and use Resend invite. Error: {error}",
                "error",
            )
        else:
            if invite["sent"]:
                flash(f"Invite email sent to {email}.", "success")
            else:
                flash(
                    "User was created. Email is not configured locally, so no "
                    f"message was sent. Invite link: {invite['link']}",
                    "warning",
                )
        return redirect(url_for("admin_users"))

    return render_template("user_new.html", role_options=role_options)

@app.route("/set-password/<token>", methods=["GET", "POST"])
@limiter.limit(RATELIMIT_PASSWORD, methods=["POST"])
def set_password(token):
    # No login required: the signed "invite" token is the credential. The
    # password-reset flow (A5) is a separate route with its own "reset" token,
    # so an invite link cannot be used as a reset link or vice versa.
    user_id = read_token(token, "invite", INVITE_TOKEN_MAX_AGE)

    if user_id is None:
        return render_template("set_password.html", invalid=True), 400

    db = get_db()
    user = db.execute(
        "SELECT id, email, name FROM users WHERE id = %s AND is_active = TRUE",
        (user_id,),
    ).fetchone()

    if user is None:
        return render_template("set_password.html", invalid=True), 400

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        error = validate_password_strength(password)
        if not error and password != confirm_password:
            error = "Passwords do not match."

        if error:
            return render_template(
                "set_password.html", user=user, token=token, error=error
            ), 400

        db.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hash_password(password), user["id"]),
        )
        db.commit()

        return redirect(url_for("login"))

    return render_template("set_password.html", user=user, token=token)

@app.route("/admin/users/<int:user_id>/resend-invite", methods=["POST"])
def admin_user_resend_invite(user_id):
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    db = get_db()
    user = db.execute(
        "SELECT id, email, role, password_hash FROM users WHERE id = %s",
        (user_id,),
    ).fetchone()

    # Only re-invite a manageable account that is still pending (no password set
    # yet). Activated accounts should use the password-reset flow instead.
    if user is None or not can_manage_user_role(user["role"]) or user["password_hash"] is not None:
        return redirect(url_for("admin_users"))

    try:
        invite = send_invite(user["id"], user["email"])
    except Exception as error:
        app.logger.exception("Invite email failed for %s", user["email"])
        flash(
            "Invite email could not be sent. Please check email settings and "
            f"try again. Error: {error}",
            "error",
        )
    else:
        if invite["sent"]:
            flash(f"Invite email sent to {user['email']}.", "success")
        else:
            flash(
                "Email is not configured locally, so no message was sent. "
                f"Invite link: {invite['link']}",
                "warning",
            )

    return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/deactivate", methods=["POST"])
def admin_user_deactivate(user_id):
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    sudo_redirect = require_sudo()
    if sudo_redirect is not None:
        return sudo_redirect

    if user_id == session.get("user_id"):
        return redirect(url_for("admin_users"))

    db = get_db()
    user = db.execute(
        """
        SELECT id, role
        FROM users
        WHERE id = %s
        """,
        (user_id,),
    ).fetchone()

    if user is None or not can_manage_user_role(user["role"]):
        return redirect(url_for("admin_users"))

    db.execute(
        """
        UPDATE users
        SET is_active = FALSE
        WHERE id = %s
        """,
        (user_id,),
    )
    db.commit()

    return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/activate", methods=["POST"])
def admin_user_activate(user_id):
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    db = get_db()
    user = db.execute(
        """
        SELECT id, role
        FROM users
        WHERE id = %s
        """,
        (user_id,),
    ).fetchone()

    if user is None or not can_manage_user_role(user["role"]):
        return redirect(url_for("admin_users"))

    db.execute(
        """
        UPDATE users
        SET is_active = TRUE
        WHERE id = %s
        """,
        (user_id,),
    )
    db.commit()

    return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def admin_user_delete(user_id):
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    sudo_redirect = require_sudo()
    if sudo_redirect is not None:
        return sudo_redirect

    if user_id == session.get("user_id"):
        return redirect(url_for("admin_users"))

    db = get_db()
    user = db.execute(
        """
        SELECT id, role, is_active
        FROM users
        WHERE id = %s
        """,
        (user_id,),
    ).fetchone()

    if user is None or user["is_active"] or not can_manage_user_role(user["role"]):
        return redirect(url_for("admin_users"))

    transaction_count = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM transactions
        WHERE user_id = %s
        """,
        (user_id,),
    ).fetchone()["total"]

    if transaction_count > 0:
        return redirect(url_for("admin_users"))

    db.execute(
        """
        DELETE FROM users
        WHERE id = %s
        """,
        (user_id,),
    )
    db.commit()

    return redirect(url_for("admin_users"))

@app.route("/db-status")
def db_status():
    admin_redirect = require_system_admin()

    if admin_redirect is not None:
        return admin_redirect

    db = get_db()
    user_count = db.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"]
    item_count = db.execute("SELECT COUNT(*) AS total FROM items").fetchone()["total"]
    transaction_count = db.execute("SELECT COUNT(*) AS total FROM transactions").fetchone()["total"]

    return render_template(
        "db_status.html",
        user_count=user_count,
        item_count=item_count,
        transaction_count=transaction_count,
    )
# to run : invent/bin/python -m flask --app app init-db
