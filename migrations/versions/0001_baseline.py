"""baseline schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-08 17:35:20.362963

Baseline revision: represents the CURRENT production schema after all Phase 1
changes (users / items / transactions tables, the item_barcode_number_seq
sequence, and every column/constraint the ensure_*_columns() runtime shims
currently guarantee). It is written as explicit SQL (raw-SQL migration mode; no
SQLAlchemy models) and mirrors schema.sql exactly, minus the DROP statements and
the demo seed rows.

Adoption:
- Brand-new empty database:   `alembic upgrade head`   builds the whole schema.
- Existing populated database (already created by schema.sql): mark it as already
  at this baseline WITHOUT recreating tables:
      `alembic stamp 0001_baseline`
  A subsequent `alembic upgrade head` then only applies later revisions.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the baseline schema on an empty database."""
    op.execute(
        """
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            institution_id TEXT UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE items (
            id SERIAL PRIMARY KEY,
            barcode TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            bin_location TEXT NOT NULL,
            room TEXT NOT NULL,
            company TEXT,
            quantity INTEGER NOT NULL DEFAULT 0,
            minimum_quantity INTEGER NOT NULL DEFAULT 0,
            location TEXT,
            expiration_date TEXT DEFAULT '00/00/0000',
            notes TEXT
        )
        """
    )
    op.execute("CREATE SEQUENCE item_barcode_number_seq START WITH 1")
    op.execute(
        """
        CREATE TABLE transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
            transaction_time TIME(0) NOT NULL DEFAULT LOCALTIME(0),
            lab_instructor TEXT,
            topic_of_day TEXT,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT,
            FOREIGN KEY (item_id) REFERENCES items (id) ON DELETE RESTRICT
        )
        """
    )


def downgrade() -> None:
    """Drop everything the baseline created (reverse dependency order)."""
    op.execute("DROP TABLE IF EXISTS transactions")
    op.execute("DROP TABLE IF EXISTS items")
    op.execute("DROP SEQUENCE IF EXISTS item_barcode_number_seq")
    op.execute("DROP TABLE IF EXISTS users")
