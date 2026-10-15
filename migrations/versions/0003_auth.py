"""0003 – Auth: users table + scan_history ownership columns.

Changes:
  users          – new table (google_sub, email, name, picture, created_at, last_login)
  scan_history   – add user_id (FK → users.id, NULL) and anon_session_id (VARCHAR 64, NULL)

Revision ID: 0003_auth
Revises:     0002_phase1_unified_schema
Create Date: 2026-10-09
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision      = '0003_auth'
down_revision = '0002_phase1_unified_schema'
branch_labels = None
depends_on    = None


def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
        {'t': table_name}
    ).first()
    return result is not None


def _column_exists(conn, table_name: str, col_name: str) -> bool:
    rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return any(r[1] == col_name for r in rows)


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Create users table (idempotent) ────────────────────────────────────
    if not _table_exists(conn, 'users'):
        op.create_table(
            'users',
            sa.Column('id',          sa.Integer,      nullable=False, autoincrement=True),
            sa.Column('google_sub',  sa.String(255),  nullable=False),
            sa.Column('email',       sa.String(255),  nullable=True),
            sa.Column('name',        sa.String(255),  nullable=True),
            sa.Column('picture',     sa.String(500),  nullable=True),
            sa.Column('created_at',  sa.DateTime,     nullable=False,
                      server_default=sa.func.now()),
            sa.Column('last_login',  sa.DateTime,     nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('google_sub', name='uq_users_google_sub'),
        )

    # 2. Add user_id and anon_session_id to scan_history (batch for SQLite) ─
    # Note: In SQLite batch mode, ForeignKey constraints on new columns are
    # expressed via add_column only (no separate add_constraint needed).
    need_user_id = not _column_exists(conn, 'scan_history', 'user_id')
    need_anon_id = not _column_exists(conn, 'scan_history', 'anon_session_id')

    if need_user_id or need_anon_id:
        with op.batch_alter_table('scan_history', schema=None) as batch_op:
            if need_user_id:
                batch_op.add_column(sa.Column('user_id', sa.Integer, nullable=True))
            if need_anon_id:
                batch_op.add_column(sa.Column('anon_session_id', sa.String(64), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()

    # Remove user_id and anon_session_id from scan_history (idempotent) ─────
    has_user_id = _column_exists(conn, 'scan_history', 'user_id')
    has_anon_id = _column_exists(conn, 'scan_history', 'anon_session_id')

    if has_user_id or has_anon_id:
        with op.batch_alter_table('scan_history', schema=None) as batch_op:
            if has_anon_id:
                batch_op.drop_column('anon_session_id')
            if has_user_id:
                batch_op.drop_column('user_id')

    # Drop users table (idempotent) ─────────────────────────────────────────
    if _table_exists(conn, 'users'):
        op.drop_table('users')
