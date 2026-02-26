"""Add study session, daily routine, and syllabus progress tables.

Revision ID: 20260226_02
Revises: 20260226_01
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260226_02"
down_revision = "20260226_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "study_session",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_study_session_user_id", "study_session", ["user_id"], unique=False)
    op.create_index("ix_study_session_date", "study_session", ["date"], unique=False)

    op.create_table(
        "daily_routine_task",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "task_name", "date", name="uq_daily_routine_user_task_date"),
    )
    op.create_index("ix_daily_routine_task_user_id", "daily_routine_task", ["user_id"], unique=False)
    op.create_index("ix_daily_routine_task_date", "daily_routine_task", ["date"], unique=False)

    op.create_table(
        "syllabus_topic",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=120), nullable=False),
        sa.Column("topic_name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_syllabus_topic_subject", "syllabus_topic", ["subject"], unique=False)

    op.create_table(
        "user_syllabus_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("theory_completed", sa.Boolean(), nullable=False),
        sa.Column("pyq_30_done", sa.Boolean(), nullable=False),
        sa.Column("revision_1_done", sa.Boolean(), nullable=False),
        sa.Column("revision_2_done", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["syllabus_topic.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "topic_id", name="uq_user_syllabus_topic"),
    )
    op.create_index("ix_user_syllabus_progress_user_id", "user_syllabus_progress", ["user_id"], unique=False)
    op.create_index("ix_user_syllabus_progress_topic_id", "user_syllabus_progress", ["topic_id"], unique=False)


def downgrade():
    op.drop_index("ix_user_syllabus_progress_topic_id", table_name="user_syllabus_progress")
    op.drop_index("ix_user_syllabus_progress_user_id", table_name="user_syllabus_progress")
    op.drop_table("user_syllabus_progress")

    op.drop_index("ix_syllabus_topic_subject", table_name="syllabus_topic")
    op.drop_table("syllabus_topic")

    op.drop_index("ix_daily_routine_task_date", table_name="daily_routine_task")
    op.drop_index("ix_daily_routine_task_user_id", table_name="daily_routine_task")
    op.drop_table("daily_routine_task")

    op.drop_index("ix_study_session_date", table_name="study_session")
    op.drop_index("ix_study_session_user_id", table_name="study_session")
    op.drop_table("study_session")
