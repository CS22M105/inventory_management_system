"""indexes for the transactions list/filters and the items name sort

Revision ID: 0004_transaction_indexes
Revises: 0003_expiration_date_to_date
Create Date: 2026-07-08

The transaction history page (/transactions) sorts by
``(transaction_date DESC, transaction_time DESC, id DESC)`` and filters by item,
user, and date range. On a growing table those queries degrade to a full
sequential scan plus an in-memory/disk sort. This migration adds the supporting
indexes:

- transactions(item_id)                          -> item filter + user page counts
- transactions(user_id)                          -> user filter + per-user counts
- transactions(transaction_date)                 -> date-range filter
- transactions(transaction_date DESC,
               transaction_time DESC, id DESC)    -> matches the list ORDER BY so
                                                     the sort is index-supported
                                                     (esp. with LIMIT/OFFSET
                                                     pagination in H2)
- items(name)                                     -> items list sort + filter
                                                     dropdown ordering

Note on transactions(transaction_date): it is partly redundant with the composite
index (whose leading column is transaction_date), so a date-range predicate can
already use the composite. It is kept because it is smaller/cheaper for the
planner on pure date-range scans and this table's write volume is low; drop it
later if index bloat ever matters.

CONCURRENTLY caveat
-------------------
These use plain ``CREATE INDEX``, which takes a brief ACCESS EXCLUSIVE lock while
building. The transactions table is small today, so that is fine. On a large,
busy production table, build them without locking writes using
``CREATE INDEX CONCURRENTLY`` instead -- but CONCURRENTLY **cannot run inside a
transaction block**, and Alembic wraps each migration in one. So do NOT put
CONCURRENTLY here. Instead run it manually during a maintenance window, e.g.:

    CREATE INDEX CONCURRENTLY ix_transactions_date_time_id
        ON transactions (transaction_date DESC, transaction_time DESC, id DESC);

then ``alembic stamp 0004_transaction_indexes`` to mark this revision applied.
The ``IF NOT EXISTS`` guards below make that path safe (the migration becomes a
no-op for any index already built concurrently).
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0004_transaction_indexes"
down_revision: Union[str, Sequence[str], None] = "0003_expiration_date_to_date"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_transactions_item_id "
        "ON transactions (item_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_transactions_user_id "
        "ON transactions (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_transactions_transaction_date "
        "ON transactions (transaction_date)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_transactions_date_time_id "
        "ON transactions (transaction_date DESC, transaction_time DESC, id DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_items_name ON items (name)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_items_name")
    op.execute("DROP INDEX IF EXISTS ix_transactions_date_time_id")
    op.execute("DROP INDEX IF EXISTS ix_transactions_transaction_date")
    op.execute("DROP INDEX IF EXISTS ix_transactions_user_id")
    op.execute("DROP INDEX IF EXISTS ix_transactions_item_id")
