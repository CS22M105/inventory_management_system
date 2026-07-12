"""Core Flask application assembly and shared route helpers."""

from datetime import timedelta
import json
import time

from flask import (
    Flask,
    g,
    got_request_exception,
    has_request_context,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFError, CSRFProtect
import psycopg2
from itsdangerous import URLSafeTimedSerializer
from werkzeug.middleware.proxy_fix import ProxyFix
from whitenoise import WhiteNoise

from inventory.auth.passwords import (
    hash_password as password_hash_password,
    validate_password_strength as password_validate_password_strength,
    verify_password as password_verify_password,
)
from inventory.auth.tokens import (
    make_token as token_make_token,
    read_token as token_read_token,
)
from inventory.cli import _alembic_config, register_cli
from inventory.config import (
    APP_BASE_URL,
    APP_ENV,
    BARCODE_PREFIX,
    BASE_DIR,
    DEV_SECRET_KEY,
    ELEVATED_ROLES,
    EMAIL_FROM,
    EMAIL_PROVIDER,
    HSTS_ENABLED,
    INVITE_TOKEN_MAX_AGE,
    LOGIN_LOCKOUT_SECONDS,
    LOGIN_MAX_ATTEMPTS,
    MIN_PASSWORD_LENGTH,
    PROXY_FIX_ENABLED,
    RATELIMIT_ENABLED,
    RATELIMIT_LOGIN,
    RATELIMIT_PASSWORD,
    RATELIMIT_STOCK,
    RATELIMIT_STORAGE_URI,
    RESET_TOKEN_MAX_AGE,
    SCHEMA,
    SECRET_KEY,
    SENTRY_DSN,
    SENTRY_TRACES_SAMPLE_RATE,
    SESSION_IDLE_MINUTES,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_USE_SSL,
    SMTP_USE_TLS,
    SUDO_MODE_MAX_AGE,
    TRANSACTIONS_PAGE_SIZE,
    add_static_headers,
    hsts_header_value,
    validate_production_config,
)
from inventory.db import close_db, get_db
from inventory.items.barcodes import (
    generate_next_item_barcode as barcode_generate_next_item_barcode,
)
from inventory.items.forms import (
    get_item_form_data as forms_get_item_form_data,
    parse_expiration_date as forms_parse_expiration_date,
)
from inventory.observability import (
    configure_logging,
    initialize_sentry,
    log_unhandled_exception,
    register_request_logging,
)
from inventory.services.email import send_email as email_send_email
from inventory.stock.service import (
    get_stock_item as stock_get_stock_item,
    process_stock_transaction as stock_process_stock_transaction,
)
from inventory.transactions.repository import (
    build_transaction_filter_clause as transaction_build_filter_clause,
    count_transaction_rows as transaction_count_rows,
    get_transaction_filter_options as transaction_filter_options,
    get_transaction_rows as transaction_get_rows,
)


validate_production_config()
initialize_sentry(SENTRY_DSN, APP_ENV, SENTRY_TRACES_SAMPLE_RATE)

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
configure_logging(app, APP_ENV)

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
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=SESSION_IDLE_MINUTES)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True

csrf = CSRFProtect(app)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri=RATELIMIT_STORAGE_URI,
    headers_enabled=True,
)
limiter.enabled = RATELIMIT_ENABLED

register_request_logging(app)
got_request_exception.connect(log_unhandled_exception, app)
app.teardown_appcontext(close_db)
register_cli(app)


@app.after_request
def add_security_headers(response):
    if HSTS_ENABLED and request.is_secure:
        response.headers.setdefault("Strict-Transport-Security", hsts_header_value())
    return response


@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    return render_template(
        "login.html",
        error="Your session expired or the form was invalid. Please try again.",
    ), 400


@app.errorhandler(429)
def handle_rate_limit(error):
    return render_template("rate_limited.html"), 429


def generate_next_item_barcode(db):
    return barcode_generate_next_item_barcode(db, BARCODE_PREFIX)


def hash_password(raw_password):
    return password_hash_password(raw_password)


def verify_password(password_hash, raw_password):
    return password_verify_password(password_hash, raw_password)


def validate_password_strength(raw_password):
    return password_validate_password_strength(raw_password, MIN_PASSWORD_LENGTH)


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
    _login_attempts.pop(email, None)
    return False


def record_failed_login(email):
    record = _login_attempts.setdefault(email, {"count": 0, "locked_until": None})
    record["count"] += 1
    if record["count"] >= LOGIN_MAX_ATTEMPTS:
        record["locked_until"] = time.time() + LOGIN_LOCKOUT_SECONDS


def clear_failed_login(email):
    _login_attempts.pop(email, None)


def remaining_login_attempts(email):
    record = _login_attempts.get(email)
    if not record:
        return LOGIN_MAX_ATTEMPTS
    return max(0, LOGIN_MAX_ATTEMPTS - record["count"])


def get_token_serializer():
    return URLSafeTimedSerializer(app.config["SECRET_KEY"])


def make_token(user_id, purpose):
    return token_make_token(get_token_serializer(), user_id, purpose)


def read_token(token, purpose, max_age):
    return token_read_token(get_token_serializer(), token, purpose, max_age)


def send_email(to, subject, body):
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
    token = make_token(user_id, "invite")
    base_url = APP_BASE_URL or request.host_url.rstrip("/")
    link = f"{base_url}{url_for('auth.set_password', token=token)}"
    sent = send_email(
        email,
        "Set your Katz Nursing Inventory password",
        "You have been invited to the Katz Nursing Inventory system.\n\n"
        f"Set your password using this link (valid for 72 hours):\n{link}\n",
    )
    return {"sent": sent, "link": link}


def send_reset(user_id, email):
    token = make_token(user_id, "reset")
    base_url = APP_BASE_URL or request.host_url.rstrip("/")
    link = f"{base_url}{url_for('auth.reset_password', token=token)}"
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
        return redirect(url_for("auth.login"))
    return None


def mark_sudo():
    session["sudo_at"] = int(time.time())


def has_fresh_sudo():
    sudo_at = session.get("sudo_at")
    if sudo_at is None:
        return False
    return (time.time() - sudo_at) <= SUDO_MODE_MAX_AGE


def safe_next(target, fallback_endpoint="admin.admin_users"):
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for(fallback_endpoint)


def require_sudo():
    login_redirect = require_login()
    if login_redirect is not None:
        return login_redirect
    if not has_fresh_sudo():
        return redirect(url_for("auth.reauth", next=url_for("admin.admin_users")))
    return None


def require_admin():
    login_redirect = require_login()
    if login_redirect is not None:
        return login_redirect
    if session.get("user_role") not in ELEVATED_ROLES:
        return redirect(url_for("dashboard.dashboard"))
    return None


def require_system_admin():
    login_redirect = require_login()
    if login_redirect is not None:
        return login_redirect
    if session.get("user_role") != "administrator":
        return redirect(url_for("dashboard.dashboard"))
    return None


def require_item_manager():
    login_redirect = require_login()
    if login_redirect is not None:
        return login_redirect
    if session.get("user_role") not in ELEVATED_ROLES:
        return redirect(url_for("items.items"))
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
    return forms_parse_expiration_date(value)


def get_item_form_data(require_barcode=True):
    return forms_get_item_form_data(request.form, require_barcode=require_barcode)


def process_stock_transaction(barcode, form):
    def audit_stock_change(db, item, transaction_type, quantity, new_quantity):
        action = "stock_added" if transaction_type == "add" else "stock_removed"
        log_audit_event(
            db,
            action,
            target_type="item",
            target_id=item["id"],
            target_label=f"{item['name']} ({barcode})",
            details={
                "barcode": barcode,
                "quantity": quantity,
                "new_quantity": new_quantity,
            },
        )

    return stock_process_stock_transaction(
        get_db(),
        session["user_id"],
        barcode,
        form,
        audit_callback=audit_stock_change,
    )


def get_stock_item(db, barcode):
    return stock_get_stock_item(db, barcode)


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
    return transaction_count_rows(db, filters)


def get_transaction_rows(db, filters, limit=None, offset=None):
    return transaction_get_rows(db, filters, limit=limit, offset=offset)


def get_transaction_filter_options(db):
    return transaction_filter_options(db)


def log_audit_event(
    db,
    action,
    target_type=None,
    target_id=None,
    target_label=None,
    details=None,
    actor_user_id=None,
    actor_email_snapshot=None,
    actor_role_snapshot=None,
):
    """Record append-only audit metadata without storing secrets or form bodies."""
    request_id = None
    remote_addr = None
    user_agent = None

    if has_request_context():
        if actor_user_id is None:
            actor_user_id = session.get("user_id")
        request_id = getattr(g, "request_id", None)
        remote_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
        if remote_addr and "," in remote_addr:
            remote_addr = remote_addr.split(",", 1)[0].strip()
        user_agent = request.headers.get("User-Agent")

    if actor_user_id and (not actor_email_snapshot or not actor_role_snapshot):
        actor = db.execute(
            "SELECT email, role FROM users WHERE id = %s",
            (actor_user_id,),
        ).fetchone()
        if actor is not None:
            actor_email_snapshot = actor_email_snapshot or actor["email"]
            actor_role_snapshot = actor_role_snapshot or actor["role"]

    serialized_details = None
    if details is not None:
        serialized_details = json.dumps(details, sort_keys=True, default=str)

    db.execute(
        """
        INSERT INTO audit_logs (
            actor_user_id,
            actor_email_snapshot,
            actor_role_snapshot,
            action,
            target_type,
            target_id,
            target_label,
            ip_address,
            request_id,
            user_agent,
            details_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            actor_user_id,
            actor_email_snapshot,
            actor_role_snapshot,
            action,
            target_type,
            str(target_id) if target_id is not None else None,
            target_label,
            remote_addr,
            request_id,
            user_agent,
            serialized_details,
        ),
    )


def register_blueprints(flask_app):
    from inventory.admin.routes import bp as admin_bp
    from inventory.auth.routes import bp as auth_bp
    from inventory.dashboard.routes import bp as dashboard_bp
    from inventory.items.routes import bp as items_bp
    from inventory.reports.routes import bp as reports_bp
    from inventory.stock.routes import bp as stock_bp
    from inventory.transactions.routes import bp as transactions_bp

    flask_app.register_blueprint(dashboard_bp)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(items_bp)
    flask_app.register_blueprint(stock_bp)
    flask_app.register_blueprint(transactions_bp)
    flask_app.register_blueprint(reports_bp)
    flask_app.register_blueprint(admin_bp)
