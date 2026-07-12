"""Shared pytest fixtures for the authentication test suite (Substep A6).

These tests run against a real, throwaway PostgreSQL database (they never touch
the development/production database). The database name defaults to
``inventory_test`` and can be overridden with ``TEST_DATABASE_URL``.

The database is created fresh once per test session, the schema is applied, and
each test starts from a known set of seeded users (see the ``users`` fixture).
"""

import os
import sys

# Make the application package importable regardless of pytest's rootdir, and
# point the app at a dedicated test database BEFORE it is imported (DATABASE_URL
# is read at import time in app.py).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://localhost/inventory_test"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-auth-tests")

import psycopg2  # noqa: E402
import pytest  # noqa: E402

import app as app_module  # noqa: E402
import inventory.core as core_module  # noqa: E402

# Shared password for every seeded user that has one.
SEED_PASSWORD = "Password123"


def _maintenance_url():
    # Connect to the default "postgres" database on the same server so we can
    # create/drop the test database itself.
    return TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"


def _db_name():
    return TEST_DATABASE_URL.rsplit("/", 1)[1]


def _run_admin_sql(statements):
    conn = psycopg2.connect(_maintenance_url())
    conn.autocommit = True
    try:
        cursor = conn.cursor()
        for sql, params in statements:
            cursor.execute(sql, params)
        cursor.close()
    finally:
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def _create_test_database():
    name = _db_name()
    terminate = (
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        "WHERE datname = %s AND pid <> pg_backend_pid()"
    )

    _run_admin_sql(
        [
            (terminate, (name,)),
            (f'DROP DATABASE IF EXISTS "{name}"', None),
            (f'CREATE DATABASE "{name}"', None),
        ]
    )

    with app_module.app.app_context():
        db = app_module.get_db()
        # schema.sql builds the complete schema (the ensure_*_columns runtime
        # shims were removed in F3; the schema is owned by migrations/schema.sql).
        with app_module.SCHEMA.open("r") as schema_file:
            db.execute(schema_file.read())
        db.commit()

    yield

    _run_admin_sql(
        [
            (terminate, (name,)),
            (f'DROP DATABASE IF EXISTS "{name}"', None),
        ]
    )


@pytest.fixture(autouse=True)
def _configure_app():
    # CSRF is exercised separately (Step B); disabling it here lets the tests
    # focus on the authentication logic without minting tokens for every POST.
    app_module.app.config["TESTING"] = True
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    # Rate limiting (Step D) is off by default so the many requests other tests
    # make are not throttled; the rate-limit tests enable it explicitly.
    app_module.limiter.enabled = False
    try:
        app_module.limiter._storage.reset()
    except Exception:
        pass
    yield
    app_module.limiter.enabled = False


@pytest.fixture(autouse=True)
def _clear_login_attempts():
    # The failed-login lockout store is a module-level dict; reset it around each
    # test so per-process state does not leak between tests.
    app_module._login_attempts.clear()
    yield
    app_module._login_attempts.clear()


@pytest.fixture()
def users(_create_test_database):
    """Reset the database to a known set of users before each test.

    Returns a dict keyed by role/label; each value has id, email, role and the
    plaintext password (or None for the still-invited account).
    """
    seed = {
        "admin": ("admin@test.edu", "administrator", True, SEED_PASSWORD),
        "faculty": ("faculty@test.edu", "faculty", True, SEED_PASSWORD),
        "student": ("student@test.edu", "student", True, SEED_PASSWORD),
        "inactive": ("inactive@test.edu", "student", False, SEED_PASSWORD),
        "invited": ("invited@test.edu", "student", True, None),
    }

    result = {}
    with app_module.app.app_context():
        db = app_module.get_db()
        db.execute(
            "TRUNCATE audit_logs, transactions, items, users "
            "RESTART IDENTITY CASCADE"
        )
        for key, (email, role, active, password) in seed.items():
            password_hash = app_module.hash_password(password) if password else None
            row = db.execute(
                """
                INSERT INTO users (email, name, role, is_active, password_hash)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (email, key.title(), role, active, password_hash),
            ).fetchone()
            result[key] = {
                "id": row["id"],
                "email": email,
                "role": role,
                "password": password,
            }
        db.commit()

    return result


@pytest.fixture()
def client():
    return app_module.app.test_client()


@pytest.fixture()
def captured_emails(monkeypatch):
    """Capture outgoing invite/reset emails instead of logging/sending them."""
    sent = []

    def fake_send_email(to, subject, body):
        sent.append({"to": to, "subject": subject, "body": body})
        return True

    monkeypatch.setattr(app_module, "send_email", fake_send_email)
    monkeypatch.setattr(core_module, "send_email", fake_send_email)
    return sent


@pytest.fixture()
def login(client):
    def _login(email, password):
        return client.post(
            "/login", data={"email": email, "password": password}
        )

    return _login
