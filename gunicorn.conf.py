import os
from multiprocessing import cpu_count


def _int_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _worker_count():
    default_workers = (2 * cpu_count()) + 1
    # WEB_CONCURRENCY is the common PaaS convention. Keep GUNICORN_WORKERS as a
    # compatibility alias for the earlier project config.
    if os.environ.get("WEB_CONCURRENCY"):
        return _int_env("WEB_CONCURRENCY", default_workers)
    return _int_env("GUNICORN_WORKERS", default_workers)


bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = _worker_count()
threads = _int_env("GUNICORN_THREADS", 2)
timeout = _int_env("GUNICORN_TIMEOUT", 30)
graceful_timeout = _int_env("GUNICORN_GRACEFUL_TIMEOUT", 30)
keepalive = _int_env("GUNICORN_KEEPALIVE", 5)
max_requests = _int_env("GUNICORN_MAX_REQUESTS", 1000)
max_requests_jitter = _int_env("GUNICORN_MAX_REQUESTS_JITTER", 100)
accesslog = os.environ.get("GUNICORN_ACCESSLOG", "-")
errorlog = os.environ.get("GUNICORN_ERRORLOG", "-")
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")
