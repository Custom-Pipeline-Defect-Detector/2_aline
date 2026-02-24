"""init

Revision ID: 0001_init
Revises: 
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("password_hash", sa.String, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String, nullable=False, unique=True),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String, nullable=False, unique=True),
        sa.Column("aliases", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_code", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("customer_id", sa.Integer, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("status", sa.String, nullable=False, server_default="new"),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_projects_project_code", "projects", ["project_code"])
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("filename", sa.String, nullable=False),
        sa.Column("mime", sa.String, nullable=False),
        sa.Column("storage_path", sa.String, nullable=False),
        sa.Column("uploader_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("folder_path_hint", sa.String, nullable=True),
        sa.Column("file_hash", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_documents_file_hash", "documents", ["file_hash"])
    op.create_table(
        "document_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("doc_id", sa.Integer, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("extracted_text_path", sa.String, nullable=True),
        sa.Column("router_json", postgresql.JSONB, nullable=True),
        sa.Column("extractor_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("status", sa.String, nullable=False, server_default="open"),
        sa.Column("source_doc_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "issues",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("severity", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String, nullable=False, server_default="open"),
        sa.Column("source_doc_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "ncrs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("root_cause", sa.Text, nullable=True),
        sa.Column("corrective_action", sa.Text, nullable=True),
        sa.Column("status", sa.String, nullable=False, server_default="open"),
        sa.Column("source_doc_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "proposals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("doc_version_id", sa.Integer, sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("proposed_action", sa.String, nullable=False),
        sa.Column("target_module", sa.String, nullable=False),
        sa.Column("target_table", sa.String, nullable=False),
        sa.Column("target_entity_id", sa.Integer, nullable=True),
        sa.Column("proposed_fields", postgresql.JSONB, nullable=False),
        sa.Column("field_confidence", postgresql.JSONB, nullable=False),
        sa.Column("evidence", postgresql.JSONB, nullable=False),
        sa.Column("questions", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.String, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_proposals_status", "proposals", ["status"])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("actor_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("entity_table", sa.String, nullable=False),
        sa.Column("entity_id", sa.Integer, nullable=False),
        sa.Column("before", postgresql.JSONB, nullable=True),
        sa.Column("after", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_index("ix_proposals_status", table_name="proposals")
    op.drop_table("proposals")
    op.drop_table("ncrs")
    op.drop_table("issues")
    op.drop_table("tasks")
    op.drop_table("document_versions")
    op.drop_index("ix_documents_file_hash", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_projects_project_code", table_name="projects")
    op.drop_table("projects")
    op.drop_table("customers")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")
