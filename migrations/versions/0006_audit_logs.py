"""expand audit events into admin audit logs

Revision ID: 0006_audit_logs
Revises: 0005_audit_events
Create Date: 2026-07-12

R2 introduced audit_events for CSV export metadata. R3 expands that into the
production audit_logs table used for user administration, inventory, stock,
reports, and system events. Existing audit_events rows are preserved by renaming
the table and columns, then adding actor snapshots and request context columns.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0006_audit_logs"
down_revision: Union[str, Sequence[str], None] = "0005_audit_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_audit_events_created_at")
    op.execute("DROP INDEX IF EXISTS ix_audit_events_actor_user_id")
    op.execute("DROP INDEX IF EXISTS ix_audit_events_event_type")
    op.execute("ALTER TABLE IF EXISTS audit_events RENAME TO audit_logs")
    op.execute("ALTER TABLE audit_logs RENAME COLUMN event_type TO action")
    op.execute("ALTER TABLE audit_logs RENAME COLUMN details TO details_json")
    op.execute(
        "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS actor_email_snapshot TEXT"
    )
    op.execute(
        "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS actor_role_snapshot TEXT"
    )
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS target_label TEXT")
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS user_agent TEXT")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at "
        "ON audit_logs (created_at DESC, id DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_user_id "
        "ON audit_logs (actor_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_action "
        "ON audit_logs (action)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_target_type "
        "ON audit_logs (target_type)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_target_type")
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_action")
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_actor_user_id")
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_created_at")
    op.execute("ALTER TABLE audit_logs DROP COLUMN IF EXISTS user_agent")
    op.execute("ALTER TABLE audit_logs DROP COLUMN IF EXISTS target_label")
    op.execute("ALTER TABLE audit_logs DROP COLUMN IF EXISTS actor_role_snapshot")
    op.execute("ALTER TABLE audit_logs DROP COLUMN IF EXISTS actor_email_snapshot")
    op.execute("ALTER TABLE audit_logs RENAME COLUMN details_json TO details")
    op.execute("ALTER TABLE audit_logs RENAME COLUMN action TO event_type")
    op.execute("ALTER TABLE IF EXISTS audit_logs RENAME TO audit_events")
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
