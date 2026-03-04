from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.rbac import TASKS_READ_ROLES, TASKS_WRITE_ROLES
from app.deps import get_db, get_current_user, require_roles
from app.rbac import has_role

router = APIRouter(prefix="/tasks", tags=["tasks"])



def _log_audit(db: Session, actor_id: int, action: str, entity_id: int, before, after):
    db.add(
        models.AuditLog(
            actor_user_id=actor_id,
            action=action,
            entity_table="tasks",
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


@router.get("", response_model=list[schemas.TaskOut], dependencies=[Depends(require_roles(TASKS_READ_ROLES))])
def list_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    project_id: int | None = None,
    owner_id: int | None = None,
    status: str | None = None,
    mine: bool | None = False,
):
    query = db.query(models.Task)
    
    # Apply project access filtering (unless admin/manager)
    user_roles = [role.name for role in current_user.roles]
    if "Admin" not in user_roles and "Manager" not in user_roles:
        # Get all projects the user has access to
        accessible_projects = db.query(models.ProjectMember.project_id).filter(
            models.ProjectMember.user_id == current_user.id
        ).subquery()
        query = query.filter(models.Task.project_id.in_(accessible_projects))
    else:
        # Admins/managers can see all tasks
        pass
    
    if project_id:
        query = query.filter(models.Task.project_id == project_id)
    if owner_id:
        query = query.filter(models.Task.owner_id == owner_id)
    if status:
        query = query.filter(models.Task.status == status)
    if mine:
        query = query.filter(models.Task.owner_id == current_user.id)

    tasks = query.order_by(models.Task.created_at.desc()).all()
    results: list[schemas.TaskOut] = []
    for task in tasks:
        results.append(
            schemas.TaskOut(
                id=task.id,
                project_id=task.project_id,
                title=task.title,
                description=task.description,
                owner_id=task.owner_id,
                due_date=task.due_date,
                status=task.status,
                priority=task.priority,
                type=task.type,
                source_doc_id=task.source_doc_id,
                completed_at=task.completed_at,
                created_at=task.created_at,
                project_name=task.project.name if task.project else None,
                project_code=task.project.project_code if task.project else None,
                owner_name=None,
            )
        )
    return results


@router.post("", response_model=schemas.TaskOut, dependencies=[Depends(require_roles(TASKS_WRITE_ROLES))])
def create_task(
    payload: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = _resolve_project(db, payload.project_id, payload.project_code)
    
    # Check permissions for task assignment based on engineering hierarchy
    assigned_to_user_id = payload.owner_id  # Using owner_id as assigned_to_user_id for compatibility
    if assigned_to_user_id:
        # Check if current user can assign tasks to the target user
        can_assign = False
        
        # Admins and managers can assign to anyone
        if has_role(current_user, ["admin", "manager"]):
            can_assign = True
        else:
            # Check if current user is PM of the project
            pm_member = db.query(models.ProjectMember).filter(
                models.ProjectMember.project_id == project.id,
                models.ProjectMember.user_id == current_user.id,
                models.ProjectMember.project_role == "project_manager"
            ).first()
            
            if pm_member:
                # PM can assign to leads and engineers in the project
                target_member = db.query(models.ProjectMember).filter(
                    models.ProjectMember.project_id == project.id,
                    models.ProjectMember.user_id == assigned_to_user_id
                ).first()
                if target_member:
                    can_assign = True
            else:
                # Check if current user is a lead in the project
                lead_member = db.query(models.ProjectMember).filter(
                    models.ProjectMember.project_id == project.id,
                    models.ProjectMember.user_id == current_user.id,
                    models.ProjectMember.project_role == "lead_engineer"
                ).first()
                
                if lead_member:
                    # Lead can assign to engineers who report to them
                    target_member = db.query(models.ProjectMember).filter(
                        models.ProjectMember.project_id == project.id,
                        models.ProjectMember.user_id == assigned_to_user_id,
                        models.ProjectMember.report_to_user_id == current_user.id
                    ).first()
                    if target_member:
                        can_assign = True
        
        if not can_assign:
            raise HTTPException(status_code=403, detail="Insufficient permissions to assign task to this user")
    
    task = models.Task(
        project_id=project.id,
        title=payload.title,
        description=payload.description,
        owner_id=payload.owner_id,
        due_date=payload.due_date,
        status=payload.status or "open",
        priority=payload.priority or "med",
        type=payload.type or "engineering",
        source_doc_id=payload.source_doc_id,
        created_by_user_id=current_user.id,
        assigned_to_user_id=payload.owner_id,
        assigned_by_user_id=current_user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    _log_audit(db, current_user.id, "created", task.id, None, {"title": task.title})
    db.commit()
    return schemas.TaskOut(
        id=task.id,
        project_id=task.project_id,
        title=task.title,
        description=task.description,
        owner_id=task.owner_id,
        due_date=task.due_date,
        status=task.status,
        priority=task.priority,
        type=task.type,
        source_doc_id=task.source_doc_id,
        completed_at=task.completed_at,
        created_at=task.created_at,
        project_name=task.project.name if task.project else None,
        project_code=task.project.project_code if task.project else None,
        owner_name=None,
    )


@router.patch("/{task_id}", response_model=schemas.TaskOut, dependencies=[Depends(require_roles(TASKS_WRITE_ROLES))])
def update_task(
    task_id: int,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = db.query(models.Task).filter_by(id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if user has access to the project this task belongs to (unless they're admin/manager)
    user_roles = [role.name for role in current_user.roles]
    if "Admin" not in user_roles and "Manager" not in user_roles:
        # Check if user is assigned to this project
        project_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == task.project_id,
            models.ProjectMember.user_id == current_user.id
        ).first()
        if not project_member:
            raise HTTPException(status_code=403, detail="Access to project denied")

    before = {
        "title": task.title,
        "status": task.status,
        "due_date": task.due_date,
        "owner_id": task.owner_id,
    }

    updates = payload.model_dump(exclude_unset=True)
    if "project_id" in updates or "project_code" in updates:
        project = _resolve_project(db, updates.get("project_id"), updates.get("project_code"))
        task.project_id = project.id
        updates.pop("project_id", None)
        updates.pop("project_code", None)
    for field, value in updates.items():
        setattr(task, field, value)

    if task.status == "done" and not task.completed_at:
        task.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(task)
    _log_audit(db, current_user.id, "updated", task.id, before, {"title": task.title, "status": task.status})
    db.commit()
    return schemas.TaskOut(
        id=task.id,
        project_id=task.project_id,
        title=task.title,
        description=task.description,
        owner_id=task.owner_id,
        due_date=task.due_date,
        status=task.status,
        priority=task.priority,
        type=task.type,
        source_doc_id=task.source_doc_id,
        completed_at=task.completed_at,
        created_at=task.created_at,
        project_name=task.project.name if task.project else None,
        project_code=task.project.project_code if task.project else None,
        owner_name=None,
    )


@router.delete("/{task_id}", status_code=204, dependencies=[Depends(require_roles(TASKS_WRITE_ROLES))])
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = db.query(models.Task).filter_by(id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if user has access to the project this task belongs to (unless they're admin/manager)
    user_roles = [role.name for role in current_user.roles]
    if "Admin" not in user_roles and "Manager" not in user_roles:
        # Check if user is assigned to this project
        project_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == task.project_id,
            models.ProjectMember.user_id == current_user.id
        ).first()
        if not project_member:
            raise HTTPException(status_code=403, detail="Access to project denied")
    
    before = {"title": task.title, "status": task.status}
    db.delete(task)
    db.commit()
    _log_audit(db, current_user.id, "deleted", task_id, before, None)
    db.commit()
    return None
