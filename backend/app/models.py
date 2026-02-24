from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    roles = relationship("Role", secondary="user_roles", back_populates="users")


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    users = relationship("User", secondary="user_roles", back_populates="roles")


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    aliases = Column(JSONB, nullable=False, default=list)
    status = Column(String, nullable=False, default="lead")
    industry = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    tags = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    projects = relationship("Project", back_populates="customer")
    contacts = relationship("CustomerContact", back_populates="customer", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="customer")


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    project_code = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status = Column(String, nullable=False, default="new")
    stage = Column(String, nullable=False, default="intake")
    value_amount = Column(Float, nullable=True)
    currency = Column(String, nullable=False, default="CNY")
    start_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="projects")
    tasks = relationship("Task", back_populates="project")
    issues = relationship("Issue", back_populates="project")
    ncrs = relationship("NCR", back_populates="project")
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="project")
    bom_items = relationship("BOMItem", back_populates="project", cascade="all, delete-orphan")
    work_logs = relationship("WorkLog", back_populates="project", cascade="all, delete-orphan")
    inspection_records = relationship("InspectionRecord", back_populates="project", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    mime = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    folder_path_hint = Column(String, nullable=True)
    file_hash = Column(String, nullable=False)
    processing_status = Column(String, nullable=False, default="queued")
    document_type = Column(String, nullable=True)
    classification_confidence = Column(Float, nullable=True)
    extracted_text = Column(Text, nullable=True)
    extracted_fields = Column(JSONB, nullable=True)
    agent_summary = Column(Text, nullable=True)
    needs_review = Column(Boolean, nullable=False, default=False)
    last_processed_at = Column(DateTime(timezone=True), nullable=True)
    processing_error = Column(Text, nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    versions = relationship("DocumentVersion", back_populates="document")
    customer = relationship("Customer", back_populates="documents")
    project = relationship("Project", back_populates="documents")
    agent_runs = relationship("AgentRun", back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id = Column(Integer, primary_key=True)
    doc_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    extracted_text_path = Column(String, nullable=True)
    router_json = Column(JSONB, nullable=True)
    extractor_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="versions")
    proposals = relationship("Proposal", back_populates="document_version")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(String, nullable=False, default="open")
    priority = Column(String, nullable=False, default="med")
    type = Column(String, nullable=False, default="engineering")
    completed_at = Column(DateTime(timezone=True), nullable=True)
    source_doc_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="tasks")


class Issue(Base):
    __tablename__ = "issues"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    severity = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, nullable=False, default="open")
    source_doc_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="issues")


class NCR(Base):
    __tablename__ = "ncrs"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    description = Column(Text, nullable=False)
    root_cause = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="open")
    source_doc_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    opened_date = Column(Date, nullable=True)
    closed_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="ncrs")


class Proposal(Base):
    __tablename__ = "proposals"
    id = Column(Integer, primary_key=True)
    doc_version_id = Column(Integer, ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False)
    proposed_action = Column(String, nullable=False)
    target_module = Column(String, nullable=False)
    target_table = Column(String, nullable=False)
    target_entity_id = Column(Integer, nullable=True)
    proposed_fields = Column(JSONB, nullable=False)
    field_confidence = Column(JSONB, nullable=False)
    evidence = Column(JSONB, nullable=False)
    questions = Column(JSONB, nullable=False)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    document_version = relationship("DocumentVersion", back_populates="proposals")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    entity_table = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    before = Column(JSONB, nullable=True)
    after = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CustomerContact(Base):
    __tablename__ = "customer_contacts"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    role_title = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="contacts")


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    role = Column(String, nullable=True)
    type = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    entity_table = Column(String, nullable=True)
    entity_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Milestone(Base):
    __tablename__ = "milestones"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    due_date = Column(Date, nullable=True)
    status = Column(String, nullable=False, default="planned")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="milestones")


class BOMItem(Base):
    __tablename__ = "bom_items"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    part_no = Column(String, nullable=False)
    name = Column(String, nullable=False)
    qty = Column(Float, nullable=False, default=1)
    supplier = Column(String, nullable=True)
    lead_time_days = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="bom_items")


class WorkLog(Base):
    __tablename__ = "work_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    summary = Column(Text, nullable=False)
    derived_from_doc_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="work_logs")


class InspectionRecord(Base):
    __tablename__ = "inspection_records"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    inspector_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    date = Column(Date, nullable=False)
    status = Column(String, nullable=False, default="open")
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="inspection_records")
    items = relationship("InspectionItem", back_populates="inspection", cascade="all, delete-orphan")


class InspectionItem(Base):
    __tablename__ = "inspection_items"
    id = Column(Integer, primary_key=True)
    inspection_id = Column(Integer, ForeignKey("inspection_records.id", ondelete="CASCADE"), nullable=False)
    label = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    inspection = relationship("InspectionRecord", back_populates="items")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    entity_table = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    payload_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    model = Column(String, nullable=False, default="qwen2.5:7b-instruct")
    prompt_version = Column(String, nullable=False, default="v1")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    tool_calls_json = Column(JSONB, nullable=True)
    final_result_json = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)

    document = relationship("Document", back_populates="agent_runs")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChatMessage(Base):
    __tablename__ = "ai_chat_messages"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserMemory(Base):
    __tablename__ = "user_memories"
    __table_args__ = (UniqueConstraint("user_id", "content", name="uq_user_memories_user_content"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String, nullable=False, default="general")
    key = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    relevance = Column(Float, nullable=False, default=0.5)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MessageRoom(Base):
    __tablename__ = "chat_rooms"
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatRoomMember(Base):
    __tablename__ = "chat_room_members"
    room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)


class Message(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sender = relationship("User")
