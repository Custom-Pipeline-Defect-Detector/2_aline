from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.rbac import TASKS_READ_ROLES, TASKS_WRITE_ROLES
from app.deps import get_db, get_current_user, require_roles

router = APIRouter(prefix="/issues", tags=["issues"])



def _log_audit(db: Session, actor_id: int, action: str, entity_id: int, before, after):
    db.add(
        models.AuditLog(
            actor_user_id=actor_id,
            action=action,
            entity_table="issues",
            entity_id=entity_id,
            before=before,
            after=after,
        )
    )


def _resolve_project(db: Session, project_id: int | None, project_code: str | None):
    if project_id:
        project = db.query(models.Project).filter_by(id=project_id).first()
        if project:
            return project
    if project_code:
        project = db.query(models.Project).filter_by(project_code=project_code).first()
        if project:
            return project
    raise HTTPException(status_code=400, detail="Project not found")


@router.get("", response_model=list[schemas.IssueOut], dependencies=[Depends(require_roles(TASKS_READ_ROLES))])
def list_issues(db: Session = Depends(get_db), project_id: int | None = None, status: str | None = None):
    query = db.query(models.Issue)
    if project_id:
        query = query.filter(models.Issue.project_id == project_id)
    if status:
        query = query.filter(models.Issue.status == status)
    issues = query.order_by(models.Issue.created_at.desc()).all()
    return [
        schemas.IssueOut(
            id=issue.id,
            project_id=issue.project_id,
            severity=issue.severity,
            description=issue.description,
            owner_id=issue.owner_id,
            status=issue.status,
            source_doc_id=issue.source_doc_id,
            created_at=issue.created_at,
            project_name=issue.project.name if issue.project else None,
            project_code=issue.project.project_code if issue.project else None,
        )
        for issue in issues
    ]


@router.post("", response_model=schemas.IssueOut, dependencies=[Depends(require_roles(TASKS_WRITE_ROLES))])
def create_issue(
    payload: schemas.IssueCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = _resolve_project(db, payload.project_id, payload.project_code)
    issue = models.Issue(
        project_id=project.id,
        severity=payload.severity,
        description=payload.description,
        owner_id=payload.owner_id,
        status=payload.status or "open",
        source_doc_id=payload.source_doc_id,
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    _log_audit(db, current_user.id, "created", issue.id, None, {"severity": issue.severity})
    db.commit()
    return schemas.IssueOut(
        id=issue.id,
        project_id=issue.project_id,
        severity=issue.severity,
        description=issue.description,
        owner_id=issue.owner_id,
        status=issue.status,
        source_doc_id=issue.source_doc_id,
        created_at=issue.created_at,
        project_name=project.name,
        project_code=project.project_code,
    )


@router.patch("/{issue_id}", response_model=schemas.IssueOut, dependencies=[Depends(require_roles(TASKS_WRITE_ROLES))])
def update_issue(
    issue_id: int,
    payload: schemas.IssueUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    issue = db.query(models.Issue).filter_by(id=issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    before = {"severity": issue.severity, "status": issue.status}
    updates = payload.model_dump(exclude_unset=True)
    if "project_id" in updates or "project_code" in updates:
        project = _resolve_project(db, updates.get("project_id"), updates.get("project_code"))
        issue.project_id = project.id
        updates.pop("project_id", None)
        updates.pop("project_code", None)
    for field, value in updates.items():
        setattr(issue, field, value)
    db.commit()
    db.refresh(issue)
    _log_audit(db, current_user.id, "updated", issue.id, before, {"severity": issue.severity, "status": issue.status})
    db.commit()
    return schemas.IssueOut(
        id=issue.id,
        project_id=issue.project_id,
        severity=issue.severity,
        description=issue.description,
        owner_id=issue.owner_id,
        status=issue.status,
        source_doc_id=issue.source_doc_id,
        created_at=issue.created_at,
        project_name=issue.project.name if issue.project else None,
        project_code=issue.project.project_code if issue.project else None,
    )


@router.delete("/{issue_id}", status_code=204, dependencies=[Depends(require_roles(TASKS_WRITE_ROLES))])
def delete_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    issue = db.query(models.Issue).filter_by(id=issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    before = {"severity": issue.severity, "status": issue.status}
    db.delete(issue)
    db.commit()
    _log_audit(db, current_user.id, "deleted", issue_id, before, None)
    db.commit()
    return None
