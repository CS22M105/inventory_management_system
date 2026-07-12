"""add audit events table for privacy-sensitive actions

Revision ID: 0005_audit_events
Revises: 0004_transaction_indexes
Create Date: 2026-07-12

The university readiness privacy review requires export actions to be auditable.
This revision adds a small append-only audit_events table for security/privacy
events such as CSV exports. The table records metadata about the action, not the
exported CSV contents.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0005_audit_events"
down_revision: Union[str, Sequence[str], None] = "0004_transaction_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            id SERIAL PRIMARY KEY,
            actor_user_id INTEGER,
            event_type TEXT NOT NULL,
            target_type TEXT,
            target_id TEXT,
            details TEXT,
            ip_address TEXT,
            request_id TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE SET NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_events_created_at "
        "ON audit_events (created_at DESC, id DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_events_actor_user_id "
        "ON audit_events (actor_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_events_event_type "
        "ON audit_events (event_type)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_audit_events_event_type")
    op.execute("DROP INDEX IF EXISTS ix_audit_events_actor_user_id")
    op.execute("DROP INDEX IF EXISTS ix_audit_events_created_at")
    op.execute("DROP TABLE IF EXISTS audit_events")
