from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.rbac import TASKS_READ_ROLES, TASKS_WRITE_ROLES
from app.deps import get_db, get_current_user, require_roles
from app.rbac import has_role

router = APIRouter(prefix="/worklogs", tags=["worklogs"])



def _log_audit(db: Session, actor_id: int, action: str, entity_id: int, before, after):
    db.add(
        models.AuditLog(
            actor_user_id=actor_id,
            action=action,
            entity_table="work_logs",
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


@router.get("", response_model=list[schemas.WorkLogOut], dependencies=[Depends(require_roles(TASKS_READ_ROLES))])
def list_worklogs(
    db: Session = Depends(get_db),
    project_id: int | None = None,
    user_id: int | None = None,
):
    query = db.query(models.WorkLog)
    if project_id:
        query = query.filter(models.WorkLog.project_id == project_id)
    if user_id:
        query = query.filter(models.WorkLog.user_id == user_id)
    logs = query.order_by(models.WorkLog.date.desc()).all()
    results: list[schemas.WorkLogOut] = []
    for log in logs:
        results.append(
            schemas.WorkLogOut(
                id=log.id,
                user_id=log.user_id,
                project_id=log.project_id,
                date=log.date,
                summary=log.summary,
                derived_from_doc_id=log.derived_from_doc_id,
                created_at=log.created_at,
                project_name=log.project.name if log.project else None,
                project_code=log.project.project_code if log.project else None,
                user_name=None,
            )
        )
    return results


@router.post("", response_model=schemas.WorkLogOut, dependencies=[Depends(require_roles(TASKS_WRITE_ROLES))])
def create_worklog(
    payload: schemas.WorkLogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = _resolve_project(db, payload.project_id, payload.project_code)
    log = models.WorkLog(
        user_id=payload.user_id or current_user.id,
        project_id=project.id,
        date=payload.date,
        summary=payload.summary,
        derived_from_doc_id=payload.derived_from_doc_id,
        status="draft"  # Default to draft status
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    _log_audit(db, current_user.id, "created", log.id, None, {"summary": log.summary})
    db.commit()
    return schemas.WorkLogOut(
        id=log.id,
        user_id=log.user_id,
        project_id=log.project_id,
        date=log.date,
        summary=log.summary,
        derived_from_doc_id=log.derived_from_doc_id,
        created_at=log.created_at,
        project_name=log.project.name if log.project else None,
        project_code=log.project.project_code if log.project else None,
        user_name=None,
    )


@router.post("/{log_id}/submit", dependencies=[Depends(require_roles(TASKS_WRITE_ROLES))])
def submit_worklog(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Submit a worklog for approval based on the reporting hierarchy"""
    log = db.query(models.WorkLog).filter_by(id=log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Work log not found")
    
    # Check if user owns this worklog
    if log.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot submit worklog that doesn't belong to you")
    
    # Check if worklog is already submitted/approved
    if log.status in ["submitted", "approved"]:
        raise HTTPException(status_code=400, detail="Worklog already submitted or approved")
    
    # Determine who to submit to based on hierarchy
    # Find the project member record for the user
    project_member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == log.project_id,
        models.ProjectMember.user_id == current_user.id
    ).first()
    
    if not project_member:
        raise HTTPException(status_code=400, detail="User not assigned to this project")
    
    submitted_to_user_id = None
    
    if project_member.project_role == "engineer":
        # Engineer submits to their lead
        submitted_to_user_id = project_member.report_to_user_id
    elif project_member.project_role == "lead_engineer":
        # Lead engineer submits to PM
        submitted_to_user_id = project_member.report_to_user_id
    elif project_member.project_role == "project_manager":
        # PM submits to manager/admin (find first admin user)
        admin_user = db.query(models.User).join(models.UserRole).join(models.Role).filter(
            models.Role.name == "admin"
        ).first()
        if admin_user:
            submitted_to_user_id = admin_user.id
        else:
            # If no admin, submit to any manager
            manager_user = db.query(models.User).join(models.UserRole).join(models.Role).filter(
                models.Role.name == "manager"
            ).first()
            if manager_user:
                submitted_to_user_id = manager_user.id
    
    if not submitted_to_user_id:
        raise HTTPException(status_code=400, detail="Could not determine approver for worklog submission")
    
    # Update worklog status and submitted_to
    log.status = "submitted"
    log.submitted_to_user_id = submitted_to_user_id
    db.commit()
    db.refresh(log)
    
    _log_audit(db, current_user.id, "submitted", log.id, {"status": "draft"}, {"status": "submitted"})
    db.commit()
    
    return {"message": "Worklog submitted successfully", "submitted_to_user_id": submitted_to_user_id}


@router.post("/{log_id}/approve", dependencies=[Depends(require_roles(TASKS_WRITE_ROLES))])
def approve_worklog(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Approve a submitted worklog"""
    log = db.query(models.WorkLog).filter_by(id=log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Work log not found")
    
    # Check if this worklog is submitted to the current user
    if log.submitted_to_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Worklog not submitted to you for approval")
    
    if log.status != "submitted":
        raise HTTPException(status_code=400, detail="Worklog is not in submitted status")
    
    # Approve the worklog
    log.status = "approved"
    log.approved_by_user_id = current_user.id
    log.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(log)
    
    _log_audit(db, current_user.id, "approved", log.id, {"status": "submitted"}, {"status": "approved"})
    db.commit()
    
    return {"message": "Worklog approved successfully"}


@router.post("/{log_id}/return", dependencies=[Depends(require_roles(TASKS_WRITE_ROLES))])
def return_worklog(
    log_id: int,
    reject_reason: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Return a worklog for revision"""
    log = db.query(models.WorkLog).filter_by(id=log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Work log not found")
    
    # Check if this worklog is submitted to the current user
    if log.submitted_to_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Worklog not submitted to you for approval")
    
    if log.status != "submitted":
        raise HTTPException(status_code=400, detail="Worklog is not in submitted status")
    
    # Return the worklog
    log.status = "returned"
    log.reject_reason = reject_reason
    db.commit()
    db.refresh(log)
    
    _log_audit(db, current_user.id, "returned", log.id, {"status": "submitted"}, {"status": "returned"})
    db.commit()
    
    return {"message": "Worklog returned for revision", "reject_reason": reject_reason}


@router.patch("/{log_id}", response_model=schemas.WorkLogOut, dependencies=[Depends(require_roles(TASKS_WRITE_ROLES))])
def update_worklog(
    log_id: int,
    payload: schemas.WorkLogUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    log = db.query(models.WorkLog).filter_by(id=log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Work log not found")
    before = {"summary": log.summary, "date": log.date}
    updates = payload.model_dump(exclude_unset=True)
    if "project_id" in updates or "project_code" in updates:
        project = _resolve_project(db, updates.get("project_id"), updates.get("project_code"))
        log.project_id = project.id
        updates.pop("project_id", None)
        updates.pop("project_code", None)
    for field, value in updates.items():
        setattr(log, field, value)
    db.commit()
    db.refresh(log)
    _log_audit(db, current_user.id, "updated", log.id, before, {"summary": log.summary, "date": log.date})
    db.commit()
    return schemas.WorkLogOut(
        id=log.id,
        user_id=log.user_id,
        project_id=log.project_id,
        date=log.date,
        summary=log.summary,
        derived_from_doc_id=log.derived_from_doc_id,
        created_at=log.created_at,
        project_name=log.project.name if log.project else None,
        project_code=log.project.project_code if log.project else None,
        user_name=None,
    )


@router.delete("/{log_id}", status_code=204, dependencies=[Depends(require_roles(TASKS_WRITE_ROLES))])
def delete_worklog(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    log = db.query(models.WorkLog).filter_by(id=log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Work log not found")
    before = {"summary": log.summary, "date": log.date}
    db.delete(log)
    db.commit()
    _log_audit(db, current_user.id, "deleted", log_id, before, None)
    db.commit()
    return None
