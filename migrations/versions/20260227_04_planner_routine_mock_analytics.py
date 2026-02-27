"""Add routine template/completion, daily planner, and mock test tables.

Revision ID: 20260227_04
Revises: 20260226_03
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260227_04"
down_revision = "20260226_03"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "routine_template",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("time_label", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("title", name="uq_routine_template_title"),
    )

    op.create_table(
        "routine_completion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("routine_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["routine_id"], ["routine_template.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "routine_id", "date", name="uq_routine_completion_user_routine_date"),
    )
    op.create_index("ix_routine_completion_user_id", "routine_completion", ["user_id"], unique=False)
    op.create_index("ix_routine_completion_routine_id", "routine_completion", ["routine_id"], unique=False)
    op.create_index("ix_routine_completion_date", "routine_completion", ["date"], unique=False)

    op.create_table(
        "daily_task",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_daily_task_user_id", "daily_task", ["user_id"], unique=False)
    op.create_index("ix_daily_task_date", "daily_task", ["date"], unique=False)

    op.create_table(
        "mock_test",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("test_number", sa.Integer(), nullable=False),
        sa.Column("attempted", sa.Boolean(), nullable=False),
        sa.Column("attempt_date", sa.Date(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "test_number", name="uq_mock_test_user_test_number"),
    )
    op.create_index("ix_mock_test_user_id", "mock_test", ["user_id"], unique=False)


def downgrade():
    op.drop_index("ix_mock_test_user_id", table_name="mock_test")
    op.drop_table("mock_test")

    op.drop_index("ix_daily_task_date", table_name="daily_task")
    op.drop_index("ix_daily_task_user_id", table_name="daily_task")
    op.drop_table("daily_task")

    op.drop_index("ix_routine_completion_date", table_name="routine_completion")
    op.drop_index("ix_routine_completion_routine_id", table_name="routine_completion")
    op.drop_index("ix_routine_completion_user_id", table_name="routine_completion")
    op.drop_table("routine_completion")

    op.drop_table("routine_template")
