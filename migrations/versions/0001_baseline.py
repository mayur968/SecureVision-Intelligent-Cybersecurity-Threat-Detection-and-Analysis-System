"""0001 – Baseline: snapshot of the existing scan_history schema.

Databases created by db.create_all() (pre-Alembic) should be stamped
with this revision via:

    flask --app migrate_app db stamp 0001_baseline

This migration creates nothing new; it only records the current schema
so that revision 0002 can apply diffs on top.

Revision ID: 0001_baseline
Revises:     (none)
Create Date: 2026-10-09
"""
from alembic import op
import sqlalchemy as sa

# Alembic metadata
revision    = '0001_baseline'
down_revision = None
branch_labels = None
depends_on    = None


def upgrade() -> None:
    """
    Only create scan_history if it doesn't already exist.
    Existing databases stamped with this revision via `flask db stamp`
    will already have the table — the IF NOT EXISTS guard ensures
    upgrade() is idempotent.
    """
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS scan_history (
            id             INTEGER  NOT NULL PRIMARY KEY,
            scan_type      VARCHAR(20)  NOT NULL,
            input_value    TEXT         NOT NULL,
            prediction     VARCHAR(20)  NOT NULL,
            confidence     FLOAT        NOT NULL,
            risk_level     VARCHAR(20)  NOT NULL,
            explanation    TEXT,
            recommendation TEXT,
            created_at     DATETIME     NOT NULL
        )
        """
    )


def downgrade() -> None:
    """Downgrade is a no-op for the baseline — we do not drop the table."""
    pass
