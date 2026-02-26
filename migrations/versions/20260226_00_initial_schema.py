"""Initial task tracker schema.

Revision ID: 20260226_00
Revises:
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa

revision = "20260226_00"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "task",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("unit", sa.String(length=120), nullable=False),
        sa.Column("topic", sa.String(length=180), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "setting",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exam_date", sa.Date(), nullable=True),
        sa.Column("daily_goal", sa.Integer(), nullable=True),
        sa.Column("theme", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("setting")
    op.drop_table("task")
