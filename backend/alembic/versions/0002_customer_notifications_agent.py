"""Add customer, notifications, and agent automation tables

Revision ID: 0002_customer_notif_agent
Revises: 0001_init
Create Date: 2025-02-14 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_customer_notif_agent"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("status", sa.String(), nullable=False, server_default="lead"))
    op.add_column("customers", sa.Column("industry", sa.String(), nullable=True))
    op.add_column("customers", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("customers", sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("customers", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))

    op.add_column("tasks", sa.Column("priority", sa.String(), nullable=False, server_default="med"))
    op.add_column("tasks", sa.Column("type", sa.String(), nullable=False, server_default="engineering"))
    op.add_column("tasks", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("documents", sa.Column("processing_status", sa.String(), nullable=False, server_default="queued"))
    op.add_column("documents", sa.Column("document_type", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("classification_confidence", sa.Float(), nullable=True))
    op.add_column("documents", sa.Column("extracted_text", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("extracted_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("documents", sa.Column("agent_summary", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("documents", sa.Column("last_processed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("processing_error", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("customer_id", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("project_id", sa.Integer(), nullable=True))
    op.create_foreign_key("documents_customer_id_fkey", "documents", "customers", ["customer_id"], ["id"])
    op.create_foreign_key("documents_project_id_fkey", "documents", "projects", ["project_id"], ["id"])

    op.create_table(
        "customer_contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("role_title", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("entity_table", sa.String(), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "milestones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="planned"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("entity_table", sa.String(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model", sa.String(), nullable=False, server_default="qwen2.5-coder:7b"),
        sa.Column("prompt_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tool_calls_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("final_result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("agent_runs")
    op.drop_table("audit_events")
    op.drop_table("milestones")
    op.drop_table("notifications")
    op.drop_table("customer_contacts")

    op.drop_constraint("documents_project_id_fkey", "documents", type_="foreignkey")
    op.drop_constraint("documents_customer_id_fkey", "documents", type_="foreignkey")
    op.drop_column("documents", "project_id")
    op.drop_column("documents", "customer_id")
    op.drop_column("documents", "processing_error")
    op.drop_column("documents", "last_processed_at")
    op.drop_column("documents", "needs_review")
    op.drop_column("documents", "agent_summary")
    op.drop_column("documents", "extracted_fields")
    op.drop_column("documents", "extracted_text")
    op.drop_column("documents", "classification_confidence")
    op.drop_column("documents", "document_type")
    op.drop_column("documents", "processing_status")

    op.drop_column("tasks", "completed_at")
    op.drop_column("tasks", "type")
    op.drop_column("tasks", "priority")

    op.drop_column("customers", "updated_at")
    op.drop_column("customers", "tags")
    op.drop_column("customers", "notes")
    op.drop_column("customers", "industry")
    op.drop_column("customers", "status")
