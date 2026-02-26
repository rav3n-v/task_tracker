"""Add weighted subject metadata to syllabus topics.

Revision ID: 20260226_03
Revises: 20260226_02
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260226_03"
down_revision = "20260226_02"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("syllabus_topic", sa.Column("subject_name", sa.String(length=120), nullable=True))
    op.add_column("syllabus_topic", sa.Column("unit_name", sa.String(length=120), nullable=True))
    op.add_column("syllabus_topic", sa.Column("weight", sa.Float(), nullable=True, server_default="0"))

    op.execute("UPDATE syllabus_topic SET subject_name = subject")
    op.execute("UPDATE syllabus_topic SET unit_name = 'Unit 1'")

    op.alter_column("syllabus_topic", "subject_name", nullable=False)
    op.alter_column("syllabus_topic", "unit_name", nullable=False)
    op.alter_column("syllabus_topic", "weight", nullable=False, server_default=None)

    op.create_index("ix_syllabus_topic_subject_name", "syllabus_topic", ["subject_name"], unique=False)
    op.create_index("ix_syllabus_topic_unit_name", "syllabus_topic", ["unit_name"], unique=False)

    op.drop_index("ix_syllabus_topic_subject", table_name="syllabus_topic")
    op.drop_column("syllabus_topic", "subject")


def downgrade():
    op.add_column("syllabus_topic", sa.Column("subject", sa.String(length=120), nullable=True))
    op.execute("UPDATE syllabus_topic SET subject = subject_name")
    op.alter_column("syllabus_topic", "subject", nullable=False)
    op.create_index("ix_syllabus_topic_subject", "syllabus_topic", ["subject"], unique=False)

    op.drop_index("ix_syllabus_topic_unit_name", table_name="syllabus_topic")
    op.drop_index("ix_syllabus_topic_subject_name", table_name="syllabus_topic")
    op.drop_column("syllabus_topic", "weight")
    op.drop_column("syllabus_topic", "unit_name")
    op.drop_column("syllabus_topic", "subject_name")
