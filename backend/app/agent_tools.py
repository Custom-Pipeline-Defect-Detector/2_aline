from typing import Any, Dict, Optional
from datetime import date
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session
from app import models
from app.database import SessionLocal
from app.services.customers import find_similar_customer


class ToolResult(BaseModel):
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)


class DocumentContextArgs(BaseModel):
    document_id: int


class DocumentClassificationArgs(BaseModel):
    document_id: int
    document_type: str
    confidence: Optional[float] = None
    extracted_fields_json: Optional[Dict[str, Any]] = None
    agent_summary: Optional[str] = None


class SearchArgs(BaseModel):
    query: str


class UpsertCustomerArgs(BaseModel):
    name: str
    aliases: Optional[list[str]] = None
    industry: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None


class SearchProjectArgs(BaseModel):
    query: str
    customer_id: Optional[int] = None


class UpsertProjectArgs(BaseModel):
    customer_id: int
    name: str
    status: Optional[str] = None
    due_date: Optional[str] = None
    value: Optional[float] = None


class LinkDocumentArgs(BaseModel):
    document_id: int
    customer_id: Optional[int] = None
    project_id: Optional[int] = None
    proposal_id: Optional[int] = None


class CreateTaskArgs(BaseModel):
    project_id: Optional[int] = None
    title: str
    priority: Optional[str] = "med"
    type: Optional[str] = "doc"
    due_date: Optional[str] = None
    assigned_to: Optional[int] = None


class CreateNotificationArgs(BaseModel):
    message: str
    user_id: Optional[int] = None
    role: Optional[str] = None
    entity_table: Optional[str] = None
    entity_id: Optional[int] = None
    type: Optional[str] = None


class AuditEventArgs(BaseModel):
    entity_table: str
    entity_id: int
    action: str
    payload_json: Optional[Dict[str, Any]] = None
    actor_user_id: Optional[int] = None


def _get_db() -> Session:
    return SessionLocal()


def get_document_context(args: DocumentContextArgs) -> ToolResult:
    db = _get_db()
    try:
        document = db.query(models.Document).filter_by(id=args.document_id).first()
        if not document:
            return ToolResult(success=False, data={"error": "Document not found"})
        return ToolResult(
            success=True,
            data={
                "id": document.id,
                "filename": document.filename,
                "mime": document.mime,
                "customer_id": document.customer_id,
                "project_id": document.project_id,
            },
        )
    finally:
        db.close()


def set_document_classification(args: DocumentClassificationArgs) -> ToolResult:
    db = _get_db()
    try:
        document = db.query(models.Document).filter_by(id=args.document_id).first()
        if not document:
            return ToolResult(success=False, data={"error": "Document not found"})
        document.document_type = args.document_type
        document.classification_confidence = args.confidence
        document.extracted_fields = args.extracted_fields_json
        document.agent_summary = args.agent_summary
        db.commit()
        return ToolResult(success=True, data={"document_id": document.id})
    finally:
        db.close()


def search_customers(args: SearchArgs) -> ToolResult:
    db = _get_db()
    try:
        results = (
            db.query(models.Customer)
            .filter(
                models.Customer.name.ilike(f"%{args.query}%")
                | models.Customer.aliases.contains([args.query])
            )
            .limit(5)
            .all()
        )
        return ToolResult(
            success=True,
            data={"results": [{"id": c.id, "name": c.name, "status": c.status} for c in results]},
        )
    finally:
        db.close()


def upsert_customer(args: UpsertCustomerArgs) -> ToolResult:
    db = _get_db()
    try:
        customer = find_similar_customer(db, args.name) or db.query(models.Customer).filter_by(name=args.name).first()
        if not customer:
            customer = models.Customer(name=args.name, aliases=args.aliases or [])
            db.add(customer)
        elif args.name and args.name not in (customer.aliases or []) and args.name != customer.name:
            customer.aliases = sorted({*(customer.aliases or []), args.name})
        if args.industry is not None:
            customer.industry = args.industry
        if args.status is not None:
            customer.status = args.status
        if args.aliases is not None:
            customer.aliases = args.aliases
        if args.notes is not None:
            customer.notes = args.notes
        if args.tags is not None:
            customer.tags = args.tags
        db.commit()
        return ToolResult(success=True, data={"id": customer.id, "name": customer.name})
    finally:
        db.close()


def search_projects(args: SearchProjectArgs) -> ToolResult:
    db = _get_db()
    try:
        query = db.query(models.Project).filter(models.Project.name.ilike(f"%{args.query}%"))
        if args.customer_id:
            query = query.filter(models.Project.customer_id == args.customer_id)
        results = query.limit(5).all()
        return ToolResult(
            success=True,
            data={"results": [{"id": p.id, "name": p.name, "status": p.status} for p in results]},
        )
    finally:
        db.close()


def upsert_project(args: UpsertProjectArgs) -> ToolResult:
    db = _get_db()
    try:
        project = (
            db.query(models.Project)
            .filter(models.Project.customer_id == args.customer_id, models.Project.name == args.name)
            .first()
        )
        if not project:
            project = models.Project(project_code=f"AUTO-{args.customer_id}-{args.name[:4]}", name=args.name, customer_id=args.customer_id)
            db.add(project)
        if args.status is not None:
            project.status = args.status
        if args.due_date is not None:
            project.due_date = date.fromisoformat(args.due_date)
        db.commit()
        return ToolResult(success=True, data={"id": project.id, "name": project.name})
    finally:
        db.close()


def link_document(args: LinkDocumentArgs) -> ToolResult:
    db = _get_db()
    try:
        document = db.query(models.Document).filter_by(id=args.document_id).first()
        if not document:
            return ToolResult(success=False, data={"error": "Document not found"})
        if args.customer_id is not None:
            document.customer_id = args.customer_id
        if args.project_id is not None:
            document.project_id = args.project_id
        db.commit()
        return ToolResult(success=True, data={"document_id": document.id})
    finally:
        db.close()


def create_task(args: CreateTaskArgs) -> ToolResult:
    db = _get_db()
    try:
        if args.project_id is None:
            return ToolResult(success=False, data={"error": "project_id required"})
        due_date = date.fromisoformat(args.due_date) if args.due_date else None
        task = models.Task(
            project_id=args.project_id,
            title=args.title,
            priority=args.priority or "med",
            type=args.type or "doc",
            due_date=due_date,
            owner_id=args.assigned_to,
            status="open",
        )
        db.add(task)
        db.commit()
        return ToolResult(success=True, data={"id": task.id})
    finally:
        db.close()


def create_notification(args: CreateNotificationArgs) -> ToolResult:
    db = _get_db()
    try:
        notification = models.Notification(
            message=args.message,
            user_id=args.user_id,
            role=args.role,
            entity_table=args.entity_table,
            entity_id=args.entity_id,
            type=args.type,
        )
        db.add(notification)
        db.commit()
        return ToolResult(success=True, data={"id": notification.id})
    finally:
        db.close()


def append_audit_event(args: AuditEventArgs) -> ToolResult:
    db = _get_db()
    try:
        event = models.AuditEvent(
            actor_user_id=args.actor_user_id,
            entity_table=args.entity_table,
            entity_id=args.entity_id,
            action=args.action,
            payload_json=args.payload_json,
        )
        db.add(event)
        db.commit()
        return ToolResult(success=True, data={"id": event.id})
    finally:
        db.close()


TOOL_REGISTRY = {
    "get_document_context": (DocumentContextArgs, get_document_context),
    "set_document_classification": (DocumentClassificationArgs, set_document_classification),
    "search_customers": (SearchArgs, search_customers),
    "upsert_customer": (UpsertCustomerArgs, upsert_customer),
    "search_projects": (SearchProjectArgs, search_projects),
    "upsert_project": (UpsertProjectArgs, upsert_project),
    "link_document": (LinkDocumentArgs, link_document),
    "create_task": (CreateTaskArgs, create_task),
    "create_notification": (CreateNotificationArgs, create_notification),
    "append_audit_event": (AuditEventArgs, append_audit_event),
}


def run_tool(name: str, raw_args: Dict[str, Any]) -> ToolResult:
    if name not in TOOL_REGISTRY:
        return ToolResult(success=False, data={"error": "Tool not allowed"})
    arg_model, handler = TOOL_REGISTRY[name]
    try:
        args = arg_model(**raw_args)
    except ValidationError as exc:
        return ToolResult(success=False, data={"error": "Invalid args", "details": exc.errors()})
    return handler(args)
