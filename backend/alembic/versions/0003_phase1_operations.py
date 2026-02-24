"""phase 1 operations updates

Revision ID: 0003_phase1_operations
Revises: 0002_customer_notifications_agent
Create Date: 2025-02-14
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_phase1_operations"
down_revision = "0002_customer_notif_agent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_customers_owner", "customers", "users", ["owner_id"], ["id"])

    op.add_column(
        "projects",
        sa.Column("stage", sa.String(), nullable=False, server_default="intake"),
    )
    op.add_column("projects", sa.Column("value_amount", sa.Float(), nullable=True))
    op.add_column(
        "projects",
        sa.Column("currency", sa.String(), nullable=False, server_default="CNY"),
    )

    op.add_column("ncrs", sa.Column("opened_date", sa.Date(), nullable=True))
    op.add_column("ncrs", sa.Column("closed_date", sa.Date(), nullable=True))

    op.create_table(
        "bom_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("part_no", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("qty", sa.Float(), nullable=False, server_default="1"),
        sa.Column("supplier", sa.String(), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "work_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("derived_from_doc_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["derived_from_doc_id"], ["documents.id"]),
    )

    op.create_table(
        "inspection_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("inspector_id", sa.Integer(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inspector_id"], ["users.id"]),
    )

    op.create_table(
        "inspection_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("inspection_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspection_records.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("inspection_items")
    op.drop_table("inspection_records")
    op.drop_table("work_logs")
    op.drop_table("bom_items")
    op.drop_column("ncrs", "closed_date")
    op.drop_column("ncrs", "opened_date")
    op.drop_column("projects", "currency")
    op.drop_column("projects", "value_amount")
    op.drop_column("projects", "stage")
    op.drop_constraint("fk_customers_owner", "customers", type_="foreignkey")
    op.drop_column("customers", "owner_id")
