"""Sentry and request logging setup."""

import json
import logging
import sys
import time
import uuid

from flask import g, request
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration


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
        pieces = [timestamp, record.levelname, record.name, record.getMessage()]
        for field in LOG_EXTRA_FIELDS:
            if hasattr(record, field):
                pieces.append(f"{field}={getattr(record, field)}")
        if record.exc_info:
            pieces.append(self.formatException(record.exc_info))
        return " ".join(str(piece) for piece in pieces)


request_logger = logging.getLogger("inventory.request")
error_logger = logging.getLogger("inventory.error")


def initialize_sentry(dsn, app_env, traces_sample_rate):
    if not dsn:
        return

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        environment=app_env,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
    )


def configure_logging(flask_app, app_env):
    formatter = JsonLineFormatter() if app_env == "production" else PlainTextFormatter()

    for logger in (flask_app.logger, request_logger, error_logger):
        logger.handlers.clear()
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False


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


def register_request_logging(flask_app):
    @flask_app.before_request
    def start_request_log_context():
        g.request_id = uuid.uuid4().hex[:12]
        g.request_started_at = time.perf_counter()
        if sentry_sdk.is_initialized():
            sentry_sdk.set_tag("request_id", g.request_id)

    @flask_app.after_request
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
