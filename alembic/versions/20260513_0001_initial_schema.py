"""initial schema

Revision ID: 20260513_0001
Revises: 
Create Date: 2026-05-13 16:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260513_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index(op.f("ix_jobs_job_id"), "jobs", ["job_id"], unique=False)

    op.create_table(
        "tasks",
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("parent_job_id", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evaluation_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_log", sa.String(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["parent_job_id"], ["jobs.job_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id"),
    )
    op.create_index(op.f("ix_tasks_task_id"), "tasks", ["task_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tasks_task_id"), table_name="tasks")
    op.drop_table("tasks")
    op.drop_index(op.f("ix_jobs_job_id"), table_name="jobs")
    op.drop_table("jobs")
