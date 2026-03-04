"""add engineering hierarchy tables and columns

Revision ID: 0006_engineering_hierarchy
Revises: 0005_messages_chat_rooms
Create Date: 2026-03-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_engineering_hierarchy"
down_revision = "0005_messages_chat_rooms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create engineer_profiles table
    op.create_table(
        "engineer_profiles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("engineer_type", sa.String(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_engineer_profiles_engineer_type", "engineer_profiles", ["engineer_type"])
    op.create_index("ix_engineer_profiles_level", "engineer_profiles", ["level"])

    # Create project_members table
    op.create_table(
        "project_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_role", sa.String(), nullable=False),
        sa.Column("engineer_type", sa.String(), nullable=True),
        sa.Column("report_to_user_id", sa.Integer(), nullable=True),
        sa.Column("assigned_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_to_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )
    op.create_index("ix_project_members_project_role", "project_members", ["project_role"])
    op.create_index("ix_project_members_engineer_type", "project_members", ["engineer_type"])
    op.create_index("ix_project_members_report_to", "project_members", ["report_to_user_id"])

    # Add columns to tasks table
    op.add_column("tasks", sa.Column("created_by_user_id", sa.Integer(), nullable=True))
    op.add_column("tasks", sa.Column("assigned_to_user_id", sa.Integer(), nullable=True))
    op.add_column("tasks", sa.Column("assigned_by_user_id", sa.Integer(), nullable=True))
    op.add_column("tasks", sa.Column("parent_task_id", sa.Integer(), nullable=True))
    op.add_column("tasks", sa.Column("blocked_reason", sa.Text(), nullable=True))
    op.add_column("tasks", sa.Column("project_member_scope", sa.String(), nullable=True))
    op.create_foreign_key("fk_tasks_created_by", "tasks", "users", ["created_by_user_id"], ["id"])
    op.create_foreign_key("fk_tasks_assigned_to", "tasks", "users", ["assigned_to_user_id"], ["id"])
    op.create_foreign_key("fk_tasks_assigned_by", "tasks", "users", ["assigned_by_user_id"], ["id"])
    op.create_foreign_key("fk_tasks_parent", "tasks", "tasks", ["parent_task_id"], ["id"])

    # Add columns to work_logs table
    op.add_column("work_logs", sa.Column("status", sa.String(), nullable=False, server_default="draft"))
    op.add_column("work_logs", sa.Column("submitted_to_user_id", sa.Integer(), nullable=True))
    op.add_column("work_logs", sa.Column("approved_by_user_id", sa.Integer(), nullable=True))
    op.add_column("work_logs", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("work_logs", sa.Column("reject_reason", sa.Text(), nullable=True))
    op.create_foreign_key("fk_work_logs_submitted_to", "work_logs", "users", ["submitted_to_user_id"], ["id"])
    op.create_foreign_key("fk_work_logs_approved_by", "work_logs", "users", ["approved_by_user_id"], ["id"])

    # Create task_comments table
    op.create_table(
        "task_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_task_comments_task_id", "task_comments", ["task_id"])


def downgrade() -> None:
    # Drop task_comments table
    op.drop_index("ix_task_comments_task_id", table_name="task_comments")
    op.drop_table("task_comments")

    # Remove columns from work_logs table
    op.drop_constraint("fk_work_logs_approved_by", "work_logs", type_="foreignkey")
    op.drop_constraint("fk_work_logs_submitted_to", "work_logs", type_="foreignkey")
    op.drop_column("work_logs", "reject_reason")
    op.drop_column("work_logs", "approved_at")
    op.drop_column("work_logs", "approved_by_user_id")
    op.drop_column("work_logs", "submitted_to_user_id")
    op.drop_column("work_logs", "status")

    # Remove columns from tasks table
    op.drop_constraint("fk_tasks_parent", "tasks", type_="foreignkey")
    op.drop_constraint("fk_tasks_assigned_by", "tasks", type_="foreignkey")
    op.drop_constraint("fk_tasks_assigned_to", "tasks", type_="foreignkey")
    op.drop_constraint("fk_tasks_created_by", "tasks", type_="foreignkey")
    op.drop_column("tasks", "project_member_scope")
    op.drop_column("tasks", "blocked_reason")
    op.drop_column("tasks", "parent_task_id")
    op.drop_column("tasks", "assigned_by_user_id")
    op.drop_column("tasks", "assigned_to_user_id")
    op.drop_column("tasks", "created_by_user_id")

    # Drop project_members table
    op.drop_index("ix_project_members_report_to", table_name="project_members")
    op.drop_index("ix_project_members_engineer_type", table_name="project_members")
    op.drop_index("ix_project_members_project_role", table_name="project_members")
    op.drop_table("project_members")

    # Drop engineer_profiles table
    op.drop_index("ix_engineer_profiles_level", table_name="engineer_profiles")
    op.drop_index("ix_engineer_profiles_engineer_type", table_name="engineer_profiles")
    op.drop_table("engineer_profiles")