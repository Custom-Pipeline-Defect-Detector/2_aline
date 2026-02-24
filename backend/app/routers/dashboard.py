import logging

from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from app import models, schemas
from app.deps import get_db, require_roles, get_current_user
from app.rbac import ADMIN_ONLY_ROLES, READ_ROLES_ALL
from app.services.dashboard import build_ncr_weekly_counts

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)


@router.get("/counts", response_model=schemas.DashboardCounts, dependencies=[Depends(require_roles(READ_ROLES_ALL))])
def get_counts(db: Session = Depends(get_db)):
    return schemas.DashboardCounts(
        projects=db.query(models.Project).count(),
        tasks=db.query(models.Task).count(),
        pending_proposals=db.query(models.Proposal).filter(models.Proposal.status == "pending").count(),
        ncrs=db.query(models.NCR).count(),
    )


@router.get(
    "/summary",
    response_model=schemas.DashboardSummary,
    dependencies=[Depends(require_roles(READ_ROLES_ALL))],
)
def get_summary(db: Session = Depends(get_db)):
    try:
        tasks_by_status = dict(
            db.query(models.Task.status, func.count(models.Task.id))
            .group_by(models.Task.status)
            .all()
        )
        projects_by_stage = dict(
            db.query(models.Project.stage, func.count(models.Project.id))
            .group_by(models.Project.stage)
            .all()
        )
        ncr_date_rows = db.query(models.NCR.created_at, models.NCR.closed_date).all()
        if ncr_date_rows:
            created_dates = [row.created_at for row in ncr_date_rows]
            closed_dates = [row.closed_date for row in ncr_date_rows]
            ncrs_weekly = build_ncr_weekly_counts(created_dates, closed_dates)
        else:
            ncrs_weekly = []
        return schemas.DashboardSummary(
            projects=db.query(models.Project).count(),
            open_tasks=db.query(models.Task).filter(models.Task.status == "open").count(),
            open_issues=db.query(models.Issue).filter(models.Issue.status == "open").count(),
            open_ncrs=db.query(models.NCR).filter(models.NCR.status == "open").count(),
            pending_ai_actions=db.query(models.Proposal).filter(models.Proposal.status == "pending").count(),
            ncrs_weekly=ncrs_weekly,
            tasks_by_status=[{"status": key, "count": value} for key, value in tasks_by_status.items()],
            projects_by_stage=[{"stage": key, "count": value} for key, value in projects_by_stage.items()],
        )
    except SQLAlchemyError as exc:
        logger.exception("Dashboard summary unavailable due to database error")
        raise HTTPException(status_code=503, detail="Database unavailable. Run migrations and verify DB settings.") from exc


@router.get("/admin", response_model=schemas.DashboardAdmin, dependencies=[Depends(require_roles(ADMIN_ONLY_ROLES))])
def admin_dashboard(db: Session = Depends(get_db)):
    counts = {
        "users": db.query(models.User).count(),
        "customers": db.query(models.Customer).count(),
        "projects": db.query(models.Project).count(),
        "proposals": db.query(models.Proposal).count(),
        "documents": db.query(models.Document).count(),
    }
    queue = dict(
        db.query(models.Document.processing_status, func.count(models.Document.id))
        .group_by(models.Document.processing_status)
        .all()
    )
    recent_audit = (
        db.query(models.AuditEvent)
        .order_by(models.AuditEvent.created_at.desc())
        .limit(20)
        .all()
    )
    needs_review = db.query(models.Document).filter(models.Document.needs_review.is_(True)).count()
    return schemas.DashboardAdmin(
        counts=counts,
        queue={
            "queued": queue.get("queued", 0),
            "processing": queue.get("processing", 0),
            "failed": queue.get("failed", 0),
            "needs_review": needs_review,
        },
        recent_audit_events=[
            {
                "id": event.id,
                "entity_table": event.entity_table,
                "entity_id": event.entity_id,
                "action": event.action,
                "created_at": event.created_at,
            }
            for event in recent_audit
        ],
    )


@router.get("/sales", response_model=schemas.DashboardSales, dependencies=[Depends(require_roles(["Admin", "Sales"]))])
def sales_dashboard(db: Session = Depends(get_db)):
    customer_status = dict(
        db.query(models.Customer.status, func.count(models.Customer.id))
        .group_by(models.Customer.status)
        .all()
    )
    proposal_status = dict(
        db.query(models.Proposal.status, func.count(models.Proposal.id))
        .group_by(models.Proposal.status)
        .all()
    )
    stale_cutoff = date.today() - timedelta(days=30)
    stale_customers = []
    for customer in db.query(models.Customer).all():
        doc_time = (
            db.query(func.max(models.Document.created_at))
            .filter(models.Document.customer_id == customer.id)
            .scalar()
        )
        audit_time = (
            db.query(func.max(models.AuditEvent.created_at))
            .filter(models.AuditEvent.entity_table == "customers", models.AuditEvent.entity_id == customer.id)
            .scalar()
        )
        last_activity = max([t for t in [doc_time, audit_time] if t], default=None)
        if not last_activity or last_activity.date() <= stale_cutoff:
            stale_customers.append({"id": customer.id, "name": customer.name, "last_activity_at": last_activity})
    return schemas.DashboardSales(
        customer_status_counts=customer_status,
        proposal_status_counts=proposal_status,
        stale_customers=stale_customers,
    )


@router.get("/engineering", response_model=schemas.DashboardEngineering, dependencies=[Depends(require_roles(["Admin", "Engineer"]))])
def engineering_dashboard(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    my_tasks = db.query(models.Task).filter(models.Task.owner_id == user.id).order_by(models.Task.created_at.desc()).all()
    if not my_tasks:
        my_tasks = db.query(models.Task).filter(models.Task.status == "open").order_by(models.Task.created_at.desc()).limit(10).all()
    blocked_tasks = db.query(models.Task).filter(models.Task.status == "blocked").order_by(models.Task.created_at.desc()).limit(10).all()
    due_soon = date.today() + timedelta(days=14)
    projects_due = (
        db.query(models.Project)
        .filter(models.Project.due_date.isnot(None), models.Project.due_date <= due_soon)
        .order_by(models.Project.due_date.asc())
        .limit(10)
        .all()
    )
    return schemas.DashboardEngineering(
        my_tasks=[{"id": t.id, "title": t.title, "status": t.status} for t in my_tasks],
        blocked_tasks=[{"id": t.id, "title": t.title, "status": t.status} for t in blocked_tasks],
        projects_due_soon=[{"id": p.id, "name": p.name, "due_date": p.due_date} for p in projects_due],
    )


@router.get("/quality", response_model=schemas.DashboardQuality, dependencies=[Depends(require_roles(["Admin", "QC"]))])
def quality_dashboard(db: Session = Depends(get_db)):
    issue_counts = dict(
        db.query(models.Issue.severity, func.count(models.Issue.id))
        .filter(models.Issue.status == "open")
        .group_by(models.Issue.severity)
        .all()
    )
    worst_projects = (
        db.query(models.Project, func.count(models.Issue.id).label("issue_count"))
        .join(models.Issue, models.Issue.project_id == models.Project.id)
        .filter(models.Issue.status == "open")
        .group_by(models.Project.id)
        .order_by(func.count(models.Issue.id).desc())
        .limit(5)
        .all()
    )
    documents_needing_review = db.query(models.Document).filter(models.Document.needs_review.is_(True)).count()
    return schemas.DashboardQuality(
        issue_counts=issue_counts,
        worst_projects=[
            {"id": project.id, "name": project.name, "open_issues": count}
            for project, count in worst_projects
        ],
        documents_needing_review=documents_needing_review,
    )
