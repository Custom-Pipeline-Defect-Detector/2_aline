"""add user messaging rooms and messages

Revision ID: 0005_messages_chat_rooms
Revises: 0004_ai_chat_memory
Create Date: 2026-02-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_messages_chat_rooms"
down_revision = "0004_ai_chat_memory"
branch_labels = None
depends_on = None


def _has_table(insp: sa.Inspector, name: str) -> bool:
    return name in insp.get_table_names()


def _has_index(insp: sa.Inspector, table: str, index_name: str) -> bool:
    try:
        for idx in insp.get_indexes(table):
            if idx.get("name") == index_name:
                return True
    except Exception:
        return False
    return False


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 1) Rename old AI chat messages table (if it still exists)
    if _has_table(insp, "chat_messages") and not _has_table(insp, "ai_chat_messages"):
        op.rename_table("chat_messages", "ai_chat_messages")

    # refresh inspector after rename
    insp = sa.inspect(bind)

    # 2) Fix indexes on ai_chat_messages (drop old if present, create new if missing)
    if _has_table(insp, "ai_chat_messages"):
        # Old names (might or might not exist depending on how DB was created)
        if _has_index(insp, "ai_chat_messages", "ix_chat_messages_session_id"):
            op.drop_index("ix_chat_messages_session_id", table_name="ai_chat_messages")
        if _has_index(insp, "ai_chat_messages", "ix_chat_messages_user_id"):
            op.drop_index("ix_chat_messages_user_id", table_name="ai_chat_messages")

        # New names (create only if missing)
        if not _has_index(insp, "ai_chat_messages", "ix_ai_chat_messages_session_id"):
            op.create_index("ix_ai_chat_messages_session_id", "ai_chat_messages", ["session_id"])
        if not _has_index(insp, "ai_chat_messages", "ix_ai_chat_messages_user_id"):
            op.create_index("ix_ai_chat_messages_user_id", "ai_chat_messages", ["user_id"])

    # refresh again
    insp = sa.inspect(bind)

    # 3) Create new messaging tables if missing
    if not _has_table(insp, "chat_rooms"):
        op.create_table(
            "chat_rooms",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("type", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_chat_rooms_type", "chat_rooms", ["type"])

    insp = sa.inspect(bind)

    if not _has_table(insp, "chat_room_members"):
        op.create_table(
            "chat_room_members",
            sa.Column("room_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["room_id"], ["chat_rooms.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("room_id", "user_id"),
        )

    insp = sa.inspect(bind)

    if not _has_table(insp, "chat_messages"):
        op.create_table(
            "chat_messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("room_id", sa.Integer(), nullable=False),
            sa.Column("sender_user_id", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["room_id"], ["chat_rooms.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_chat_messages_room_id", "chat_messages", ["room_id"])
        op.create_index("ix_chat_messages_sender_user_id", "chat_messages", ["sender_user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Drop new messaging tables (if they exist)
    if _has_table(insp, "chat_messages"):
        if _has_index(insp, "chat_messages", "ix_chat_messages_sender_user_id"):
            op.drop_index("ix_chat_messages_sender_user_id", table_name="chat_messages")
        if _has_index(insp, "chat_messages", "ix_chat_messages_room_id"):
            op.drop_index("ix_chat_messages_room_id", table_name="chat_messages")
        op.drop_table("chat_messages")

    insp = sa.inspect(bind)

    if _has_table(insp, "chat_room_members"):
        op.drop_table("chat_room_members")

    insp = sa.inspect(bind)

    if _has_table(insp, "chat_rooms"):
        if _has_index(insp, "chat_rooms", "ix_chat_rooms_type"):
            op.drop_index("ix_chat_rooms_type", table_name="chat_rooms")
        op.drop_table("chat_rooms")

    insp = sa.inspect(bind)

    # Restore ai_chat_messages back to chat_messages (only if the target doesn't exist)
    if _has_table(insp, "ai_chat_messages") and not _has_table(insp, "chat_messages"):
        # Drop new index names if present
        if _has_index(insp, "ai_chat_messages", "ix_ai_chat_messages_user_id"):
            op.drop_index("ix_ai_chat_messages_user_id", table_name="ai_chat_messages")
        if _has_index(insp, "ai_chat_messages", "ix_ai_chat_messages_session_id"):
            op.drop_index("ix_ai_chat_messages_session_id", table_name="ai_chat_messages")

        # Recreate old names (optional, but keeps symmetry)
        if not _has_index(insp, "ai_chat_messages", "ix_chat_messages_user_id"):
            op.create_index("ix_chat_messages_user_id", "ai_chat_messages", ["user_id"])
        if not _has_index(insp, "ai_chat_messages", "ix_chat_messages_session_id"):
            op.create_index("ix_chat_messages_session_id", "ai_chat_messages", ["session_id"])

        op.rename_table("ai_chat_messages", "chat_messages")
