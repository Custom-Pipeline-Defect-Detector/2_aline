from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.rbac import PROJECTS_READ_ROLES, PROJECTS_WRITE_ROLES, require_project_access
from app.deps import get_db, require_roles, get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])



def compute_project_health(project: models.Project) -> str:
    today = date.today()
    overdue_high = any(
        task.priority == "high" and task.due_date and task.due_date < today and task.status != "done"
        for task in project.tasks
    )
    critical_issue = any(
        issue.status == "open" and issue.severity.lower() == "critical" for issue in project.issues
    )
    if overdue_high or critical_issue:
        return "red"
    blocked_tasks = any(task.status == "blocked" for task in project.tasks)
    milestone_due = any(
        milestone.due_date
        and milestone.due_date <= today + timedelta(days=7)
        and milestone.status != "done"
        for milestone in project.milestones
    )
    if blocked_tasks or milestone_due:
        return "yellow"
    return "green"


def compute_project_risk(project: models.Project) -> str:
    today = date.today()
    overdue_milestones = any(
        milestone.due_date and milestone.due_date < today and milestone.status != "done"
        for milestone in project.milestones
    )
    open_issues = [issue for issue in project.issues if issue.status == "open"]
    if overdue_milestones or len(open_issues) >= 5:
        return "high"
    if len(open_issues) >= 2:
        return "medium"
    return "low"

@router.get("", response_model=list[schemas.ProjectOut], dependencies=[Depends(require_roles(PROJECTS_READ_ROLES))])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).order_by(models.Project.created_at.desc()).all()
    return [
        schemas.ProjectOut(
            id=project.id,
            project_code=project.project_code,
            name=project.name,
            customer_id=project.customer_id,
            status=project.status,
            stage=project.stage,
            value_amount=project.value_amount,
            currency=project.currency,
            start_date=project.start_date,
            due_date=project.due_date,
            health=compute_project_health(project),
            risk=compute_project_risk(project),
        )
        for project in projects
    ]


@router.get("/{project_id}", response_model=schemas.ProjectDetail, dependencies=[Depends(require_roles(PROJECTS_READ_ROLES))])
def get_project(project_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Check if user has access to this project (unless they're admin/manager)
    user_roles = [role.name for role in current_user.roles]
    if "Admin" not in user_roles and "Manager" not in user_roles:
        # Check if user is assigned to this project
        project_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.user_id == current_user.id
        ).first()
        if not project_member:
            raise HTTPException(status_code=403, detail="Access to project denied")
    
    project = db.query(models.Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    recent_documents = (
        db.query(models.Document)
        .filter(models.Document.project_id == project.id)
        .order_by(models.Document.created_at.desc())
        .limit(5)
        .all()
    )
    pending_ai_actions = (
        db.query(models.Proposal)
        .filter(models.Proposal.status == "pending")
        .filter(
            (models.Proposal.target_table == "projects") & (models.Proposal.target_entity_id == project.id)
        )
        .count()
    )
    return schemas.ProjectDetail(
        id=project.id,
        project_code=project.project_code,
        name=project.name,
        customer_id=project.customer_id,
        status=project.status,
        stage=project.stage,
        value_amount=project.value_amount,
        currency=project.currency,
        start_date=project.start_date,
        due_date=project.due_date,
        health=compute_project_health(project),
        risk=compute_project_risk(project),
        tasks=[{"id": t.id, "title": t.title, "status": t.status} for t in project.tasks],
        issues=[{"id": i.id, "description": i.description, "severity": i.severity} for i in project.issues],
        ncrs=[{"id": n.id, "description": n.description, "status": n.status} for n in project.ncrs],
        recent_documents=[
            {
                "id": doc.id,
                "filename": doc.filename,
                "created_at": doc.created_at,
                "processing_status": doc.processing_status,
            }
            for doc in recent_documents
        ],
        pending_ai_actions=pending_ai_actions,
    )


@router.patch("/{project_id}", response_model=schemas.ProjectDetail, dependencies=[Depends(require_roles(PROJECTS_WRITE_ROLES))])
def update_project(
    project_id: int,
    payload: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Check if user has access to this project (unless they're admin/manager)
    user_roles = [role.name for role in current_user.roles]
    if "Admin" not in user_roles and "Manager" not in user_roles:
        # Check if user is assigned to this project
        project_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.user_id == current_user.id
        ).first()
        if not project_member:
            raise HTTPException(status_code=403, detail="Access to project denied")
    
    project = db.query(models.Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    before = {"name": project.name, "status": project.status, "stage": project.stage}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    db.add(
        models.AuditLog(
            actor_user_id=current_user.id,
            action="updated",
            entity_table="projects",
            entity_id=project.id,
            before=before,
            after={"name": project.name, "status": project.status, "stage": project.stage},
        )
    )
    db.commit()
    recent_documents = (
        db.query(models.Document)
        .filter(models.Document.project_id == project.id)
        .order_by(models.Document.created_at.desc())
        .limit(5)
        .all()
    )
    pending_ai_actions = (
        db.query(models.Proposal)
        .filter(models.Proposal.status == "pending")
        .filter(
            (models.Proposal.target_table == "projects") & (models.Proposal.target_entity_id == project.id)
        )
        .count()
    )
    return schemas.ProjectDetail(
        id=project.id,
        project_code=project.project_code,
        name=project.name,
        customer_id=project.customer_id,
        status=project.status,
        stage=project.stage,
        value_amount=project.value_amount,
        currency=project.currency,
        start_date=project.start_date,
        due_date=project.due_date,
        health=compute_project_health(project),
        risk=compute_project_risk(project),
        tasks=[{"id": t.id, "title": t.title, "status": t.status} for t in project.tasks],
        issues=[{"id": i.id, "description": i.description, "severity": i.severity} for i in project.issues],
        ncrs=[{"id": n.id, "description": n.description, "status": n.status} for n in project.ncrs],
        recent_documents=[
            {
                "id": doc.id,
                "filename": doc.filename,
                "created_at": doc.created_at,
                "processing_status": doc.processing_status,
            }
            for doc in recent_documents
        ],
        pending_ai_actions=pending_ai_actions,
    )


@router.post("/{project_id}/milestones", response_model=schemas.MilestoneOut, dependencies=[Depends(require_roles(PROJECTS_WRITE_ROLES))])
def create_milestone(project_id: int, payload: schemas.MilestoneCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Check if user has access to this project (unless they're admin/manager)
    user_roles = [role.name for role in current_user.roles]
    if "Admin" not in user_roles and "Manager" not in user_roles:
        # Check if user is assigned to this project
        project_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.user_id == current_user.id
        ).first()
        if not project_member:
            raise HTTPException(status_code=403, detail="Access to project denied")
    
    project = db.query(models.Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    milestone = models.Milestone(
        project_id=project_id,
        name=payload.name,
        due_date=payload.due_date,
        status=payload.status or "planned",
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return milestone


@router.get("/{project_id}/milestones", response_model=list[schemas.MilestoneOut], dependencies=[Depends(require_roles(PROJECTS_READ_ROLES))])
def list_milestones(project_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Check if user has access to this project (unless they're admin/manager)
    user_roles = [role.name for role in current_user.roles]
    if "Admin" not in user_roles and "Manager" not in user_roles:
        # Check if user is assigned to this project
        project_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.user_id == current_user.id
        ).first()
        if not project_member:
            raise HTTPException(status_code=403, detail="Access to project denied")
    
    return db.query(models.Milestone).filter_by(project_id=project_id).order_by(models.Milestone.created_at.desc()).all()


@router.patch("/milestones/{milestone_id}", response_model=schemas.MilestoneOut, dependencies=[Depends(require_roles(PROJECTS_WRITE_ROLES))])
def update_milestone(milestone_id: int, payload: schemas.MilestoneUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    milestone = db.query(models.Milestone).filter_by(id=milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    
    # Check if user has access to the project this milestone belongs to (unless they're admin/manager)
    user_roles = [role.name for role in current_user.roles]
    if "Admin" not in user_roles and "Manager" not in user_roles:
        # Check if user is assigned to this project
        project_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == milestone.project_id,
            models.ProjectMember.user_id == current_user.id
        ).first()
        if not project_member:
            raise HTTPException(status_code=403, detail="Access to project denied")
    
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(milestone, field, value)
    db.commit()
    db.refresh(milestone)
    return milestone


@router.delete("/milestones/{milestone_id}", status_code=204, dependencies=[Depends(require_roles(PROJECTS_WRITE_ROLES))])
def delete_milestone(milestone_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    milestone = db.query(models.Milestone).filter_by(id=milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    
    # Check if user has access to the project this milestone belongs to (unless they're admin/manager)
    user_roles = [role.name for role in current_user.roles]
    if "Admin" not in user_roles and "Manager" not in user_roles:
        # Check if user is assigned to this project
        project_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == milestone.project_id,
            models.ProjectMember.user_id == current_user.id
        ).first()
        if not project_member:
            raise HTTPException(status_code=403, detail="Access to project denied")
    
    db.delete(milestone)
    db.commit()
    return None
