from typing import Any, Dict, Optional
from datetime import date, datetime
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
    query: str = ""


class UpsertCustomerArgs(BaseModel):
    name: str
    aliases: Optional[list[str]] = None
    industry: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None


class SearchProjectArgs(BaseModel):
    query: str = ""
    customer_id: Optional[int] = None


class UpsertProjectArgs(BaseModel):
    customer_id: Optional[int] = None
    name: Optional[str] = None
    project_code: Optional[str] = None
    status: Optional[str] = None
    stage: Optional[str] = None
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


class UpsertProposalArgs(BaseModel):
    customer_id: int
    project_id: Optional[int] = None
    title: str
    status: Optional[str] = "draft"
    value: Optional[float] = None
    notes: Optional[str] = None


class SearchProposalArgs(BaseModel):
    query: str = ""
    status: Optional[str] = None
    customer_id: Optional[int] = None


class UpsertIssueArgs(BaseModel):
    issue_id: Optional[int] = None
    project_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = "medium"
    owner_id: Optional[int] = None
    status: Optional[str] = "open"
    source_doc_id: Optional[int] = None


class SearchIssueArgs(BaseModel):
    query: str = ""
    status: Optional[str] = None
    project_id: Optional[int] = None


class UpsertNCRArgs(BaseModel):
    ncr_id: Optional[int] = None
    project_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    status: Optional[str] = "open"
    source_doc_id: Optional[int] = None


class SearchNCRArgs(BaseModel):
    query: str = ""
    status: Optional[str] = None
    severity: Optional[str] = None
    project_id: Optional[int] = None


class UpsertWorklogArgs(BaseModel):
    project_id: int
    user_id: Optional[int] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None  # ISO format date string


class SearchWorklogArgs(BaseModel):
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    date_from: Optional[str] = None  # ISO format date string
    date_to: Optional[str] = None  # ISO format date string


class SearchTaskArgs(BaseModel):
    query: Optional[str] = None
    project_id: Optional[int] = None
    status: Optional[str] = None
    limit: Optional[int] = 10


class UpsertTaskArgs(BaseModel):
    task_id: Optional[int] = None
    project_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    owner_id: Optional[int] = None
    due_date: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    type: Optional[str] = None
    source_doc_id: Optional[int] = None


class WorkspaceSnapshotArgs(BaseModel):
    limit: Optional[int] = 8


class SearchDocumentsArgs(BaseModel):
    query: Optional[str] = None
    processing_status: Optional[str] = None
    customer_id: Optional[int] = None
    project_id: Optional[int] = None
    limit: Optional[int] = 10


class ApproveProposalArgs(BaseModel):
    proposal_id: int
    proposed_fields: Optional[Dict[str, Any]] = None
    actor_user_id: Optional[int] = None


class RejectProposalArgs(BaseModel):
    proposal_id: int
    reason: Optional[str] = None
    actor_user_id: Optional[int] = None


class AutoApprovePendingProposalsArgs(BaseModel):
    limit: Optional[int] = 100
    actor_user_id: Optional[int] = None


def _get_db() -> Session:
    return SessionLocal()


def _resolve_actor_user(db: Session, actor_user_id: Optional[int]) -> Optional[models.User]:
    if actor_user_id is not None:
        user = db.query(models.User).filter(models.User.id == actor_user_id).first()
        if user:
            return user
    return db.query(models.User).order_by(models.User.id.asc()).first()


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
        query_text = (args.query or "").strip()
        query = db.query(models.Customer)
        if query_text:
            query = query.filter(
                models.Customer.name.ilike(f"%{query_text}%")
                | models.Customer.aliases.contains([query_text])
            )
        results = query.order_by(models.Customer.updated_at.desc()).limit(10).all()
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
        query_text = (args.query or "").strip()
        query = db.query(models.Project)
        if query_text:
            query = query.filter(models.Project.name.ilike(f"%{query_text}%"))
        if args.customer_id:
            query = query.filter(models.Project.customer_id == args.customer_id)
        results = query.order_by(models.Project.created_at.desc()).limit(10).all()
        return ToolResult(
            success=True,
            data={"results": [{"id": p.id, "name": p.name, "status": p.status} for p in results]},
        )
    finally:
        db.close()


def upsert_project(args: UpsertProjectArgs) -> ToolResult:
    db = _get_db()
    try:
        customer = None
        if args.customer_id is not None:
            customer = db.query(models.Customer).filter(models.Customer.id == args.customer_id).first()
        if customer is None:
            customer = db.query(models.Customer).order_by(models.Customer.id.asc()).first()
        if customer is None:
            auto_name = f"Auto Customer {int(datetime.utcnow().timestamp())}"
            customer = models.Customer(name=auto_name, aliases=[])
            db.add(customer)
            db.flush()

        normalized_name = (args.name or args.project_code or "Auto Project").strip()
        normalized_code = (args.project_code or "").strip()

        project = None
        if normalized_code:
            project = db.query(models.Project).filter(models.Project.project_code == normalized_code).first()
        if project is None:
            project = (
                db.query(models.Project)
                .filter(models.Project.customer_id == customer.id, models.Project.name == normalized_name)
                .first()
            )

        if not project:
            auto_code = normalized_code or f"AUTO-{customer.id}-{int(datetime.utcnow().timestamp())}"
            project = models.Project(project_code=auto_code, name=normalized_name, customer_id=customer.id)
            db.add(project)
        else:
            project.name = normalized_name
            project.customer_id = customer.id
            if normalized_code:
                project.project_code = normalized_code

        if args.status is not None:
            project.status = args.status
        if args.stage is not None:
            project.stage = args.stage
        if args.due_date is not None:
            project.due_date = date.fromisoformat(args.due_date)
        if args.value is not None:
            project.value_amount = args.value
        db.commit()
        return ToolResult(
            success=True,
            data={"id": project.id, "name": project.name, "project_code": project.project_code, "customer_id": project.customer_id},
        )
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


def upsert_proposal(args: UpsertProposalArgs) -> ToolResult:
    return ToolResult(
        success=False,
        data={"error": "Proposal business upsert is not supported by current schema"},
    )


def search_proposals(args: SearchProposalArgs) -> ToolResult:
    db = _get_db()
    try:
        query = db.query(models.Proposal)
        query_text = (args.query or "").strip()
        if query_text:
            pattern = f"%{query_text}%"
            query = query.filter(
                (models.Proposal.proposed_action.ilike(pattern))
                | (models.Proposal.target_table.ilike(pattern))
                | (models.Proposal.target_module.ilike(pattern))
            )

        if args.status:
            query = query.filter(models.Proposal.status == args.status)

        if args.customer_id is not None:
            query = (
                query.join(models.DocumentVersion, models.DocumentVersion.id == models.Proposal.doc_version_id)
                .join(models.Document, models.Document.id == models.DocumentVersion.doc_id)
                .filter(models.Document.customer_id == args.customer_id)
            )

        results = query.order_by(models.Proposal.created_at.desc()).limit(20).all()
        return ToolResult(
            success=True,
            data={
                "results": [
                    {
                        "id": proposal.id,
                        "doc_version_id": proposal.doc_version_id,
                        "target_table": proposal.target_table,
                        "target_entity_id": proposal.target_entity_id,
                        "status": proposal.status,
                        "proposed_action": proposal.proposed_action,
                        "created_at": proposal.created_at.isoformat() if proposal.created_at else None,
                    }
                    for proposal in results
                ]
            },
        )
    finally:
        db.close()


def upsert_issue(args: UpsertIssueArgs) -> ToolResult:
    db = _get_db()
    try:
        issue = None
        if args.issue_id is not None:
            issue = db.query(models.Issue).filter(models.Issue.id == args.issue_id).first()
            if not issue:
                return ToolResult(success=False, data={"error": "Issue not found"})

        normalized_description = (args.description or args.title or "").strip()
        if issue is None and args.project_id is not None and normalized_description:
            issue = (
                db.query(models.Issue)
                .filter(models.Issue.project_id == args.project_id, models.Issue.description == normalized_description)
                .first()
            )

        if not issue:
            if args.project_id is None:
                return ToolResult(success=False, data={"error": "project_id required for issue create"})
            if not normalized_description:
                return ToolResult(success=False, data={"error": "description required for issue create"})
            issue = models.Issue(
                project_id=args.project_id,
                description=normalized_description,
                severity=(args.severity or "medium"),
                owner_id=args.owner_id,
                status=(args.status or "open"),
                source_doc_id=args.source_doc_id,
            )
            db.add(issue)
        else:
            if args.project_id is not None:
                issue.project_id = args.project_id
            if normalized_description:
                issue.description = normalized_description
            if args.status is not None:
                issue.status = args.status
            if args.severity is not None:
                issue.severity = args.severity
            if args.owner_id is not None:
                issue.owner_id = args.owner_id
            if args.source_doc_id is not None:
                issue.source_doc_id = args.source_doc_id

        db.commit()
        return ToolResult(
            success=True,
            data={
                "id": issue.id,
                "project_id": issue.project_id,
                "description": issue.description,
                "severity": issue.severity,
                "status": issue.status,
            },
        )
    finally:
        db.close()


def search_issues(args: SearchIssueArgs) -> ToolResult:
    db = _get_db()
    try:
        query_text = (args.query or "").strip()
        query = db.query(models.Issue)
        if query_text:
            query = query.filter(models.Issue.description.ilike(f"%{query_text}%"))
        if args.status:
            query = query.filter(models.Issue.status == args.status)
        if args.project_id:
            query = query.filter(models.Issue.project_id == args.project_id)
        results = query.order_by(models.Issue.created_at.desc()).limit(10).all()
        return ToolResult(
            success=True,
            data={"results": [
                {"id": i.id, "description": i.description, "status": i.status, "severity": i.severity}
                for i in results
            ]}
        )
    finally:
        db.close()


def upsert_ncr(args: UpsertNCRArgs) -> ToolResult:
    db = _get_db()
    try:
        ncr = None
        if args.ncr_id is not None:
            ncr = db.query(models.NCR).filter(models.NCR.id == args.ncr_id).first()
            if not ncr:
                return ToolResult(success=False, data={"error": "NCR not found"})

        normalized_description = (args.description or args.title or "").strip()
        if ncr is None and args.project_id is not None and normalized_description:
            ncr = (
                db.query(models.NCR)
                .filter(models.NCR.project_id == args.project_id, models.NCR.description == normalized_description)
                .first()
            )

        if not ncr:
            if args.project_id is None:
                return ToolResult(success=False, data={"error": "project_id required for NCR create"})
            if not normalized_description:
                return ToolResult(success=False, data={"error": "description required for NCR create"})
            ncr = models.NCR(
                project_id=args.project_id,
                description=normalized_description,
                root_cause=args.root_cause,
                corrective_action=args.corrective_action,
                status=(args.status or "open"),
                source_doc_id=args.source_doc_id,
            )
            db.add(ncr)
        else:
            if args.project_id is not None:
                ncr.project_id = args.project_id
            if normalized_description:
                ncr.description = normalized_description
            if args.root_cause is not None:
                ncr.root_cause = args.root_cause
            if args.corrective_action is not None:
                ncr.corrective_action = args.corrective_action
            if args.status is not None:
                ncr.status = args.status
            if args.source_doc_id is not None:
                ncr.source_doc_id = args.source_doc_id

        db.commit()
        return ToolResult(
            success=True,
            data={
                "id": ncr.id,
                "project_id": ncr.project_id,
                "description": ncr.description,
                "status": ncr.status,
            },
        )
    finally:
        db.close()


def search_ncrs(args: SearchNCRArgs) -> ToolResult:
    db = _get_db()
    try:
        query_text = (args.query or "").strip()
        query = db.query(models.NCR)
        if query_text:
            query = query.filter(models.NCR.description.ilike(f"%{query_text}%"))
        if args.status:
            query = query.filter(models.NCR.status == args.status)
        if args.project_id:
            query = query.filter(models.NCR.project_id == args.project_id)
        results = query.order_by(models.NCR.created_at.desc()).limit(10).all()
        return ToolResult(
            success=True,
            data={"results": [
                {"id": n.id, "description": n.description, "status": n.status}
                for n in results
            ]}
        )
    finally:
        db.close()


def upsert_worklog(args: UpsertWorklogArgs) -> ToolResult:
    db = _get_db()
    try:
        summary = (args.summary or args.description or "").strip()
        if not summary:
            return ToolResult(success=False, data={"error": "summary required"})

        # Create new worklog entry
        worklog = models.WorkLog(
            project_id=args.project_id,
            user_id=args.user_id,
            summary=summary,
        )
        if args.date:
            worklog.date = date.fromisoformat(args.date)
        else:
            worklog.date = datetime.now().date()
        db.add(worklog)
        db.commit()
        return ToolResult(
            success=True,
            data={"id": worklog.id, "project_id": worklog.project_id, "summary": worklog.summary, "date": worklog.date.isoformat()},
        )
    finally:
        db.close()


def search_worklogs(args: SearchWorklogArgs) -> ToolResult:
    db = _get_db()
    try:
        query = db.query(models.WorkLog)
        if args.project_id:
            query = query.filter(models.WorkLog.project_id == args.project_id)
        if args.user_id:
            query = query.filter(models.WorkLog.user_id == args.user_id)
        if args.date_from:
            query = query.filter(models.WorkLog.date >= date.fromisoformat(args.date_from))
        if args.date_to:
            query = query.filter(models.WorkLog.date <= date.fromisoformat(args.date_to))
        results = query.limit(10).all()
        return ToolResult(
            success=True,
            data={"results": [
                {"id": w.id, "project_id": w.project_id, "summary": w.summary, "date": w.date.isoformat()}
                for w in results
            ]}
        )
    finally:
        db.close()


def search_tasks(args: SearchTaskArgs) -> ToolResult:
    db = _get_db()
    try:
        query = db.query(models.Task)
        if args.query:
            pattern = f"%{args.query}%"
            query = query.filter((models.Task.title.ilike(pattern)) | (models.Task.description.ilike(pattern)))
        if args.project_id:
            query = query.filter(models.Task.project_id == args.project_id)
        if args.status:
            query = query.filter(models.Task.status == args.status)

        limit = max(1, min(int(args.limit or 10), 100))
        results = query.order_by(models.Task.created_at.desc()).limit(limit).all()
        return ToolResult(
            success=True,
            data={
                "results": [
                    {
                        "id": task.id,
                        "project_id": task.project_id,
                        "title": task.title,
                        "status": task.status,
                        "priority": task.priority,
                        "due_date": task.due_date.isoformat() if task.due_date else None,
                    }
                    for task in results
                ]
            },
        )
    finally:
        db.close()


def upsert_task(args: UpsertTaskArgs) -> ToolResult:
    db = _get_db()
    try:
        task = None
        if args.task_id is not None:
            task = db.query(models.Task).filter(models.Task.id == args.task_id).first()
            if not task:
                return ToolResult(success=False, data={"error": "Task not found"})

        normalized_title = (args.title or "").strip()
        if task is None and args.project_id is not None and normalized_title:
            task = (
                db.query(models.Task)
                .filter(models.Task.project_id == args.project_id, models.Task.title == normalized_title)
                .first()
            )

        if not task:
            if args.project_id is None:
                return ToolResult(success=False, data={"error": "project_id required for task create"})
            if not normalized_title:
                return ToolResult(success=False, data={"error": "title required for task create"})
            task = models.Task(
                project_id=args.project_id,
                title=normalized_title,
                description=args.description,
                owner_id=args.owner_id,
                status=args.status or "open",
                priority=args.priority or "med",
                type=args.type or "engineering",
                source_doc_id=args.source_doc_id,
            )
            if args.due_date:
                task.due_date = date.fromisoformat(args.due_date)
            db.add(task)
        else:
            if args.project_id is not None:
                task.project_id = args.project_id
            if normalized_title:
                task.title = normalized_title
            if args.description is not None:
                task.description = args.description
            if args.owner_id is not None:
                task.owner_id = args.owner_id
            if args.status is not None:
                task.status = args.status
            if args.priority is not None:
                task.priority = args.priority
            if args.type is not None:
                task.type = args.type
            if args.source_doc_id is not None:
                task.source_doc_id = args.source_doc_id
            if args.due_date is not None:
                task.due_date = date.fromisoformat(args.due_date) if args.due_date else None

        db.commit()
        return ToolResult(
            success=True,
            data={
                "id": task.id,
                "project_id": task.project_id,
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
            },
        )
    finally:
        db.close()


def get_workspace_snapshot(args: WorkspaceSnapshotArgs) -> ToolResult:
    db = _get_db()
    try:
        limit = max(1, min(int(args.limit or 8), 50))
        data = {
            "counts": {
                "customers": db.query(models.Customer).count(),
                "projects": db.query(models.Project).count(),
                "documents": db.query(models.Document).count(),
                "tasks": db.query(models.Task).count(),
                "issues": db.query(models.Issue).count(),
                "ncrs": db.query(models.NCR).count(),
                "pending_proposals": db.query(models.Proposal).filter(models.Proposal.status == "pending").count(),
            },
            "recent_customers": [
                {"id": c.id, "name": c.name, "status": c.status}
                for c in db.query(models.Customer).order_by(models.Customer.updated_at.desc()).limit(limit).all()
            ],
            "recent_projects": [
                {
                    "id": p.id,
                    "project_code": p.project_code,
                    "name": p.name,
                    "status": p.status,
                    "stage": p.stage,
                }
                for p in db.query(models.Project).order_by(models.Project.created_at.desc()).limit(limit).all()
            ],
            "recent_documents": [
                {
                    "id": d.id,
                    "filename": d.filename,
                    "processing_status": d.processing_status,
                    "document_type": d.document_type,
                }
                for d in db.query(models.Document).order_by(models.Document.created_at.desc()).limit(limit).all()
            ],
            "open_tasks": [
                {
                    "id": t.id,
                    "project_id": t.project_id,
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority,
                }
                for t in db.query(models.Task)
                .filter(models.Task.status != "done")
                .order_by(models.Task.created_at.desc())
                .limit(limit)
                .all()
            ],
        }
        return ToolResult(success=True, data=data)
    finally:
        db.close()


def search_documents(args: SearchDocumentsArgs) -> ToolResult:
    db = _get_db()
    try:
        query = db.query(models.Document)
        if args.query:
            pattern = f"%{args.query}%"
            query = query.filter(
                (models.Document.filename.ilike(pattern))
                | (models.Document.document_type.ilike(pattern))
            )
        if args.processing_status:
            query = query.filter(models.Document.processing_status == args.processing_status)
        if args.customer_id:
            query = query.filter(models.Document.customer_id == args.customer_id)
        if args.project_id:
            query = query.filter(models.Document.project_id == args.project_id)

        limit = max(1, min(int(args.limit or 10), 100))
        results = query.order_by(models.Document.created_at.desc()).limit(limit).all()
        return ToolResult(
            success=True,
            data={
                "results": [
                    {
                        "id": doc.id,
                        "filename": doc.filename,
                        "processing_status": doc.processing_status,
                        "document_type": doc.document_type,
                        "customer_id": doc.customer_id,
                        "project_id": doc.project_id,
                    }
                    for doc in results
                ]
            },
        )
    finally:
        db.close()


def approve_proposal(args: ApproveProposalArgs) -> ToolResult:
    db = _get_db()
    try:
        proposal = db.query(models.Proposal).filter(models.Proposal.id == args.proposal_id).first()
        if not proposal:
            return ToolResult(success=False, data={"error": "Proposal not found"})

        if args.proposed_fields is not None:
            proposal.proposed_fields = args.proposed_fields

        actor = _resolve_actor_user(db, args.actor_user_id)
        if not actor:
            return ToolResult(success=False, data={"error": "No actor user available to approve proposal"})

        try:
            from app import schemas as app_schemas
            from app.routers.proposals import _apply_decision

            approved = _apply_decision(
                proposal,
                app_schemas.ProposalDecision(status="approved"),
                db,
                actor,
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            return ToolResult(success=False, data={"error": str(exc)})

        return ToolResult(
            success=True,
            data={
                "proposal_id": approved.id,
                "status": approved.status,
                "target_table": approved.target_table,
            },
        )
    finally:
        db.close()


def reject_proposal(args: RejectProposalArgs) -> ToolResult:
    db = _get_db()
    try:
        proposal = db.query(models.Proposal).filter(models.Proposal.id == args.proposal_id).first()
        if not proposal:
            return ToolResult(success=False, data={"error": "Proposal not found"})

        actor = _resolve_actor_user(db, args.actor_user_id)
        if not actor:
            return ToolResult(success=False, data={"error": "No actor user available to reject proposal"})

        try:
            from app import schemas as app_schemas
            from app.routers.proposals import _apply_decision

            rejected = _apply_decision(
                proposal,
                app_schemas.ProposalDecision(status="rejected", reviewer_note=args.reason),
                db,
                actor,
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            return ToolResult(success=False, data={"error": str(exc)})

        return ToolResult(
            success=True,
            data={
                "proposal_id": rejected.id,
                "status": rejected.status,
                "target_table": rejected.target_table,
            },
        )
    finally:
        db.close()


def auto_approve_pending_proposals(args: AutoApprovePendingProposalsArgs) -> ToolResult:
    db = _get_db()
    try:
        actor = _resolve_actor_user(db, args.actor_user_id)
        if not actor:
            return ToolResult(success=False, data={"error": "No actor user available for approvals"})

        limit = max(1, min(int(args.limit or 100), 500))
        pending = (
            db.query(models.Proposal)
            .filter(models.Proposal.status == "pending")
            .order_by(models.Proposal.created_at.asc())
            .limit(limit)
            .all()
        )

        approved_ids: list[int] = []
        failed: list[dict[str, Any]] = []
        from app import schemas as app_schemas
        from app.routers.proposals import _apply_decision

        for proposal in pending:
            try:
                approved = _apply_decision(
                    proposal,
                    app_schemas.ProposalDecision(status="approved"),
                    db,
                    actor,
                )
                approved_ids.append(approved.id)
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                failed.append({"proposal_id": proposal.id, "error": str(exc)})

        return ToolResult(
            success=True,
            data={
                "approved_count": len(approved_ids),
                "approved_ids": approved_ids,
                "failed": failed,
            },
        )
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
    "upsert_issue": (UpsertIssueArgs, upsert_issue),
    "search_issues": (SearchIssueArgs, search_issues),
    "upsert_ncr": (UpsertNCRArgs, upsert_ncr),
    "search_ncrs": (SearchNCRArgs, search_ncrs),
    "upsert_worklog": (UpsertWorklogArgs, upsert_worklog),
    "search_worklogs": (SearchWorklogArgs, search_worklogs),
    "search_tasks": (SearchTaskArgs, search_tasks),
    "upsert_task": (UpsertTaskArgs, upsert_task),
    "get_workspace_snapshot": (WorkspaceSnapshotArgs, get_workspace_snapshot),
    "search_documents": (SearchDocumentsArgs, search_documents),
    "search_proposals": (SearchProposalArgs, search_proposals),
    "approve_proposal": (ApproveProposalArgs, approve_proposal),
    "reject_proposal": (RejectProposalArgs, reject_proposal),
    "auto_approve_pending_proposals": (AutoApprovePendingProposalsArgs, auto_approve_pending_proposals),
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
