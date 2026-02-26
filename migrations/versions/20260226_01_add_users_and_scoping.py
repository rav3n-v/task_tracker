"""Add users/auth and scope tasks/settings per user.

Revision ID: 20260226_01
Revises:
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa
from werkzeug.security import generate_password_hash


revision = "20260226_01"
down_revision = "20260226_00"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    with op.batch_alter_table("task", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_task_user_id", ["user_id"], unique=False)

    with op.batch_alter_table("setting", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_setting_user_id", ["user_id"], unique=True)

    conn = op.get_bind()
    legacy_password = generate_password_hash("change-me")
    conn.execute(
        sa.text(
            "INSERT INTO user (username, password_hash, created_at) VALUES (:username, :password_hash, CURRENT_TIMESTAMP)"
        ),
        {"username": "legacy", "password_hash": legacy_password},
    )
    legacy_id = conn.execute(
        sa.text("SELECT id FROM user WHERE username='legacy'")
    ).scalar_one()

    conn.execute(
        sa.text("UPDATE task SET user_id = :legacy_id WHERE user_id IS NULL"),
        {"legacy_id": legacy_id},
    )
    conn.execute(
        sa.text("UPDATE setting SET user_id = :legacy_id WHERE user_id IS NULL"),
        {"legacy_id": legacy_id},
    )

    with op.batch_alter_table("task", schema=None) as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key("fk_task_user_id_user", "user", ["user_id"], ["id"])

    with op.batch_alter_table("setting", schema=None) as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            "fk_setting_user_id_user", "user", ["user_id"], ["id"]
        )


def downgrade():
    with op.batch_alter_table("setting", schema=None) as batch_op:
        batch_op.drop_constraint("fk_setting_user_id_user", type_="foreignkey")
        batch_op.drop_index("ix_setting_user_id")
        batch_op.drop_column("user_id")

    with op.batch_alter_table("task", schema=None) as batch_op:
        batch_op.drop_constraint("fk_task_user_id_user", type_="foreignkey")
        batch_op.drop_index("ix_task_user_id")
        batch_op.drop_column("user_id")

    op.drop_table("user")
