"""Migration tests / CI check (Substep F5).

These tests guard the Alembic migration chain the app relies on for schema
management (F1-F4). They run against a DEDICATED throwaway database that is
separate from the auth suite's ``inventory_test`` DB, because a migration test
needs full control over Alembic's version table (it must start from an empty,
never-stamped database).

What is covered:
- ``alembic upgrade head`` from zero builds the expected tables/columns/indexes.
- ``upgrade head -> downgrade base -> upgrade head`` round-trips without error
  (guards reversibility of the latest chain).
- The migration graph has a single head (no divergent/branched heads).

Alembic reads ``DATABASE_URL`` from the environment (see ``migrations/env.py``),
so each test points that variable at the throwaway DB for the duration of the
Alembic run and restores it afterwards.
"""

import os

import psycopg2
import pytest
from alembic import command as alembic_command
from alembic.script import ScriptDirectory

import app as app_module

# A database dedicated to migration tests, distinct from the auth suite DB so the
# two never fight over Alembic's version table. Overridable for CI.
MIG_DATABASE_URL = os.environ.get(
    "MIG_DATABASE_URL", "postgresql://localhost/inventory_mig_test"
)

EXPECTED_TABLES = {"users", "items", "transactions"}

# A representative subset of columns per table -- enough to prove the baseline
# ran and folded in everything the old ensure_*_columns() shims guaranteed.
EXPECTED_COLUMNS = {
    "users": {
        "id",
        "institution_id",
        "email",
        "password_hash",
        "name",
        "role",
        "is_active",
        "created_at",
        "last_login_at",
    },
    "items": {
        "id",
        "barcode",
        "name",
        "bin_location",
        "room",
        "quantity",
        "minimum_quantity",
        "expiration_date",
    },
    "transactions": {
        "id",
        "user_id",
        "item_id",
        "transaction_type",
        "quantity",
        "created_at",
        "transaction_date",
        "transaction_time",
        "lab_instructor",
        "topic_of_day",
    },
}

EXPECTED_SEQUENCE = "item_barcode_number_seq"


def _maintenance_url():
    return MIG_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"


def _db_name():
    return MIG_DATABASE_URL.rsplit("/", 1)[1]


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


@pytest.fixture()
def migration_db(monkeypatch):
    """Create a fresh, empty (never-stamped) database and point Alembic at it.

    Yields the migration DB URL. The database is dropped afterwards and the
    original DATABASE_URL (the auth suite DB) is restored.
    """
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

    # migrations/env.py reads DATABASE_URL at run time, so this is what makes the
    # Alembic commands target the throwaway DB.
    monkeypatch.setenv("DATABASE_URL", MIG_DATABASE_URL)

    try:
        yield MIG_DATABASE_URL
    finally:
        _run_admin_sql(
            [
                (terminate, (name,)),
                (f'DROP DATABASE IF EXISTS "{name}"', None),
            ]
        )


def _connect():
    return psycopg2.connect(MIG_DATABASE_URL)


def _table_names(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
    )
    return {row[0] for row in cur.fetchall()}


def _column_names(conn, table):
    cur = conn.cursor()
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s",
        (table,),
    )
    return {row[0] for row in cur.fetchall()}


def _sequence_exists(conn, name):
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM information_schema.sequences "
        "WHERE sequence_schema = 'public' AND sequence_name = %s",
        (name,),
    )
    return cur.fetchone() is not None


def _index_defs(conn, table):
    cur = conn.cursor()
    cur.execute(
        "SELECT indexname, indexdef FROM pg_indexes "
        "WHERE schemaname = 'public' AND tablename = %s",
        (table,),
    )
    return {row[0]: row[1] for row in cur.fetchall()}


def test_upgrade_head_creates_expected_schema(migration_db):
    alembic_command.upgrade(app_module._alembic_config(), "head")

    conn = _connect()
    try:
        tables = _table_names(conn)
        assert EXPECTED_TABLES <= tables, (
            f"missing tables: {EXPECTED_TABLES - tables}"
        )

        for table, expected in EXPECTED_COLUMNS.items():
            actual = _column_names(conn, table)
            assert expected <= actual, (
                f"{table} missing columns: {expected - actual}"
            )

        assert _sequence_exists(conn, EXPECTED_SEQUENCE), (
            f"missing sequence {EXPECTED_SEQUENCE}"
        )

        # The UNIQUE constraints in the baseline are backed by unique indexes;
        # assert the important ones exist (primary keys + natural keys).
        users_idx = " ".join(_index_defs(conn, "users").values())
        assert "UNIQUE" in users_idx and "email" in users_idx, (
            "expected a unique index on users(email)"
        )

        items_idx = " ".join(_index_defs(conn, "items").values())
        assert "UNIQUE" in items_idx and "barcode" in items_idx, (
            "expected a unique index on items(barcode)"
        )

        # Every table should have a primary-key index.
        for table in EXPECTED_TABLES:
            assert any(
                name.endswith("_pkey") for name in _index_defs(conn, table)
            ), f"{table} is missing its primary-key index"

        # Performance indexes added in 0004 must be present at head.
        tx_indexes = set(_index_defs(conn, "transactions"))
        for expected in (
            "ix_transactions_item_id",
            "ix_transactions_user_id",
            "ix_transactions_transaction_date",
            "ix_transactions_date_time_id",
        ):
            assert expected in tx_indexes, f"missing index {expected}"
        assert "ix_items_name" in _index_defs(conn, "items"), (
            "missing index ix_items_name"
        )
    finally:
        conn.close()


def test_upgrade_downgrade_upgrade_roundtrip(migration_db):
    cfg = app_module._alembic_config()

    # Full forward, full back, full forward again -- must not raise.
    alembic_command.upgrade(cfg, "head")

    conn = _connect()
    try:
        assert EXPECTED_TABLES <= _table_names(conn)
    finally:
        conn.close()

    alembic_command.downgrade(cfg, "base")

    conn = _connect()
    try:
        remaining = _table_names(conn)
        assert not (EXPECTED_TABLES & remaining), (
            f"downgrade left tables behind: {EXPECTED_TABLES & remaining}"
        )
        assert not _sequence_exists(conn, EXPECTED_SEQUENCE), (
            "downgrade left the barcode sequence behind"
        )
    finally:
        conn.close()

    alembic_command.upgrade(cfg, "head")

    conn = _connect()
    try:
        assert EXPECTED_TABLES <= _table_names(conn)
    finally:
        conn.close()


def test_single_migration_head():
    # No live database needed: this inspects the migration scripts on disk.
    script = ScriptDirectory.from_config(app_module._alembic_config())
    heads = script.get_heads()
    assert len(heads) == 1, f"expected a single migration head, found {heads}"
