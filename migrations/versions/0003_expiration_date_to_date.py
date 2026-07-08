"""convert items.expiration_date from TEXT to a real DATE

Revision ID: 0003_expiration_date_to_date
Revises: 0001_baseline
Create Date: 2026-07-08

Historically ``items.expiration_date`` is free-text (``TEXT DEFAULT '00/00/0000'``)
because the add/edit forms use a plain text input that defaults to the sentinel
``00/00/0000``. That makes range queries ("expiring soon"), sorting, and
validation impossible and lets malformed values in.

This migration converts the column to a real ``DATE``.

Input format
------------
The UI's placeholder and default are ``00/00/0000`` (month/day/year), so the
canonical input format is treated as **MM/DD/YYYY**. A few other common formats
are accepted defensively. Anything that is empty, the ``00/00/0000`` sentinel, or
otherwise unparseable becomes ``NULL`` (i.e. "no expiration date recorded").

Strategy (safe, reversible)
---------------------------
upgrade:  add a nullable ``expiration_date_new DATE`` -> backfill it in Python by
          parsing the old text -> drop the old TEXT column -> rename new -> old.
downgrade: add ``expiration_date TEXT DEFAULT '00/00/0000'`` -> format each DATE
          back to ``MM/DD/YYYY`` (NULL -> ``00/00/0000``) -> drop the DATE column
          -> rename back.

The backfill runs in Python (via op.get_bind()) rather than SQL ``to_date`` on
purpose: PostgreSQL's ``to_date`` does NOT raise on junk like ``00/00/0000`` --
it silently produces a bogus date -- so parsing defensively in Python and mapping
failures to NULL is the correct, lossless behaviour.

NOTE FOR APP CODE (follow-up G2): after this runs, the column is a DATE. The
add/edit/import write paths still send the string ``'00/00/0000'`` and must be
updated to send a real date or NULL, otherwise inserts/updates will fail. This
migration only changes the schema + existing data.
"""
from datetime import date, datetime
from typing import Optional, Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0003_expiration_date_to_date"
down_revision: Union[str, Sequence[str], None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Sentinels that mean "no date recorded".
_EMPTY_VALUES = {"", "00/00/0000"}

# Accepted input formats, most likely first. MM/DD/YYYY is the documented format;
# the others are accepted defensively so we do not needlessly discard real dates.
_INPUT_FORMATS = ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%m/%d/%y")


def _parse_text_to_date(value: Optional[str]) -> Optional[date]:
    """Parse a legacy free-text expiration value into a date, or None."""
    if value is None:
        return None
    text = value.strip()
    if text in _EMPTY_VALUES:
        return None
    for fmt in _INPUT_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # Unparseable / malformed -> treat as "no date" rather than losing the row.
    return None


def _format_date_to_text(value: Optional[date]) -> str:
    """Reverse mapping used by downgrade: date -> MM/DD/YYYY, None -> sentinel."""
    if value is None:
        return "00/00/0000"
    return value.strftime("%m/%d/%Y")


def upgrade() -> None:
    bind = op.get_bind()

    op.execute("ALTER TABLE items ADD COLUMN expiration_date_new DATE")

    rows = bind.execute(
        sa.text("SELECT id, expiration_date FROM items")
    ).fetchall()

    update = sa.text(
        "UPDATE items SET expiration_date_new = :d WHERE id = :id"
    )
    for row in rows:
        parsed = _parse_text_to_date(row[1])
        if parsed is not None:
            bind.execute(update, {"d": parsed, "id": row[0]})

    op.execute("ALTER TABLE items DROP COLUMN expiration_date")
    op.execute(
        "ALTER TABLE items RENAME COLUMN expiration_date_new TO expiration_date"
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Restore the original TEXT column, including its historical default.
    op.execute(
        "ALTER TABLE items ADD COLUMN expiration_date_old TEXT DEFAULT '00/00/0000'"
    )

    rows = bind.execute(
        sa.text("SELECT id, expiration_date FROM items")
    ).fetchall()

    update = sa.text(
        "UPDATE items SET expiration_date_old = :t WHERE id = :id"
    )
    for row in rows:
        bind.execute(
            update, {"t": _format_date_to_text(row[1]), "id": row[0]}
        )

    op.execute("ALTER TABLE items DROP COLUMN expiration_date")
    op.execute(
        "ALTER TABLE items RENAME COLUMN expiration_date_old TO expiration_date"
    )
