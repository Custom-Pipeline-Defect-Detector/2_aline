from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from .. import models, schemas, deps, rbac
from ..database import get_db

router = APIRouter(prefix="/projects", tags=["project-team"])


@router.post("/register-engineer")
def register_engineer(
    engineer_data: schemas.UserCreate,
    engineer_type: schemas.EngineerType,
    engineer_level: schemas.EngineerLevel,
    title: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Register a new engineer with their profile"""
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == engineer_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user first
    from ..auth import get_password_hash
    hashed_password = get_password_hash(engineer_data.password)
    user = models.User(
        email=engineer_data.email,
        name=engineer_data.name,
        password_hash=hashed_password
    )
    db.add(user)
    db.flush()  # Get the user ID
    
    # Add role if specified
    if engineer_data.role_name:
        role = db.query(models.Role).filter(models.Role.name == engineer_data.role_name).first()
        if role:
            user_role = models.UserRole(user_id=user.id, role_id=role.id)
            db.add(user_role)
    
    # Create engineer profile
    engineer_profile = models.EngineerProfile(
        user_id=user.id,
        engineer_type=engineer_type.value,
        level=engineer_level.value,
        title=title
    )
    db.add(engineer_profile)
    db.commit()
    db.refresh(user)
    
    return {"message": "Engineer registered successfully", "user_id": user.id}


@router.post("/{project_id}/assign-pm")
def assign_project_manager(
    project_id: int,
    pm_user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(rbac.require_role(["Admin", "Manager"]))
):
    """Assign a project manager to a project"""
    # Check if project exists
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if user exists and is an engineer
    user = db.query(models.User).filter(models.User.id == pm_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user has engineer profile (for PM role, we might want to be flexible)
    engineer_profile = db.query(models.EngineerProfile).filter(models.EngineerProfile.user_id == pm_user_id).first()
    
    # Check if user is already assigned to this project
    existing_assignment = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.user_id == pm_user_id
    ).first()
    
    if existing_assignment:
        # Update existing assignment to PM role
        existing_assignment.project_role = "project_manager"
        existing_assignment.engineer_type = engineer_profile.engineer_type if engineer_profile else None
        existing_assignment.report_to_user_id = None  # PM reports to no one in project context
        existing_assignment.assigned_by_user_id = current_user.id
        db.commit()
        return {"message": "Project manager assigned successfully", "member_id": existing_assignment.id}
    else:
        # Create new project member record for PM
        project_member = models.ProjectMember(
            project_id=project_id,
            user_id=pm_user_id,
            project_role="project_manager",
            engineer_type=engineer_profile.engineer_type if engineer_profile else None,
            report_to_user_id=None,  # PM reports to no one in project context
            assigned_by_user_id=current_user.id
        )
        db.add(project_member)
        db.commit()
        return {"message": "Project manager assigned successfully", "member_id": project_member.id}


@router.post("/{project_id}/assign-lead")
def assign_lead_engineer(
    project_id: int,
    engineer_type: schemas.EngineerType,
    lead_user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Assign a lead engineer to a project discipline"""
    # Check if user is PM of this project or admin
    project_member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.user_id == current_user.id,
        models.ProjectMember.project_role == "project_manager"
    ).first()
    
    # Check if user has admin role
    user_roles = db.query(models.UserRole).join(models.Role).filter(
        models.UserRole.user_id == current_user.id,
        models.Role.name.in_(["admin", "manager"])
    ).count()
    is_admin_or_manager = user_roles > 0
    
    if not project_member and not is_admin_or_manager:
        raise HTTPException(status_code=403, detail="Only project manager or admin can assign leads")
    
    # Check if user exists and has matching engineer profile
    user = db.query(models.User).filter(models.User.id == lead_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    engineer_profile = db.query(models.EngineerProfile).filter(
        models.EngineerProfile.user_id == lead_user_id,
        models.EngineerProfile.engineer_type == engineer_type.value,
        models.EngineerProfile.level == "lead"
    ).first()
    
    if not engineer_profile:
        raise HTTPException(status_code=400, detail="User is not a lead engineer of the specified type")
    
    # Check if lead already exists for this discipline in this project
    existing_lead = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.engineer_type == engineer_type.value,
        models.ProjectMember.project_role == "lead_engineer"
    ).first()
    
    if existing_lead:
        db.delete(existing_lead)
    
    # Create project member record for lead
    # Find the PM for this project to set report_to
    pm_member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.project_role == "project_manager"
    ).first()
    
    project_member = models.ProjectMember(
        project_id=project_id,
        user_id=lead_user_id,
        project_role="lead_engineer",
        engineer_type=engineer_type.value,
        report_to_user_id=pm_member.user_id if pm_member else None,
        assigned_by_user_id=current_user.id
    )
    db.add(project_member)
    db.commit()
    
    return {"message": "Lead engineer assigned successfully", "member_id": project_member.id}


@router.post("/{project_id}/add-engineer")
def add_engineer_to_project(
    project_id: int,
    engineer_user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Add an engineer to a project under the current user's supervision"""
    # Check if current user is a lead in this project
    current_user_member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.user_id == current_user.id,
        models.ProjectMember.project_role == "lead_engineer"
    ).first()
    
    if not current_user_member:
        raise HTTPException(status_code=403, detail="Only lead engineers can add engineers to project")
    
    # Check if user exists and has matching engineer profile
    user = db.query(models.User).filter(models.User.id == engineer_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    engineer_profile = db.query(models.EngineerProfile).filter(
        models.EngineerProfile.user_id == engineer_user_id,
        models.EngineerProfile.engineer_type == current_user_member.engineer_type
    ).first()
    
    if not engineer_profile:
        raise HTTPException(status_code=400, detail="Engineer type does not match lead's discipline")
    
    # Check if engineer already exists in this project
    existing_engineer = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.user_id == engineer_user_id
    ).first()
    
    if existing_engineer:
        raise HTTPException(status_code=400, detail="Engineer already assigned to this project")
    
    # Create project member record for engineer
    project_member = models.ProjectMember(
        project_id=project_id,
        user_id=engineer_user_id,
        project_role="engineer",
        engineer_type=current_user_member.engineer_type,
        report_to_user_id=current_user.id,
        assigned_by_user_id=current_user.id
    )
    db.add(project_member)
    db.commit()
    
    return {"message": "Engineer added to project successfully", "member_id": project_member.id}


@router.get("/{project_id}/team")
def get_project_team(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get all team members for a project"""
    # Check if user has access to this project
    project_member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.user_id == current_user.id
    ).first()
    
    if not project_member and not rbac.has_role(current_user, ["admin", "manager"]):
        raise HTTPException(status_code=403, detail="No access to this project")
    
    team_members = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id
    ).all()
    
    result = []
    for member in team_members:
        user_info = db.query(models.User).filter(models.User.id == member.user_id).first()
        engineer_profile = db.query(models.EngineerProfile).filter(
            models.EngineerProfile.user_id == member.user_id
        ).first()
        
        result.append({
            "id": member.id,
            "user_id": member.user_id,
            "user_name": user_info.name,
            "user_email": user_info.email,
            "project_role": member.project_role,
            "engineer_type": member.engineer_type,
            "engineer_level": engineer_profile.level if engineer_profile else None,
            "report_to_user_id": member.report_to_user_id,
            "assigned_by_user_id": member.assigned_by_user_id,
            "created_at": member.created_at
        })
    
    return result


@router.get("/users/{user_id}/reports-to")
def get_reports_to(
    user_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get who a user reports to in a specific project"""
    # Check if user has access to this project
    project_member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.user_id == current_user.id
    ).first()
    
    if not project_member and not rbac.has_role(current_user, ["admin", "manager"]):
        raise HTTPException(status_code=403, detail="No access to this project")
    
    member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.user_id == user_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="User not found in project")
    
    if not member.report_to_user_id:
        return {"reports_to": None}
    
    report_to_user = db.query(models.User).filter(models.User.id == member.report_to_user_id).first()
    return {
        "reports_to": {
            "user_id": report_to_user.id,
            "name": report_to_user.name,
            "email": report_to_user.email
        }
    }


@router.get("/users/{user_id}/subordinates")
def get_subordinates(
    user_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get all subordinates of a user in a specific project"""
    # Check if user has access to this project
    project_member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.user_id == current_user.id
    ).first()
    
    if not project_member and not rbac.has_role(current_user, ["admin", "manager"]):
        raise HTTPException(status_code=403, detail="No access to this project")
    
    subordinates = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.report_to_user_id == user_id
    ).all()
    
    result = []
    for sub in subordinates:
        user_info = db.query(models.User).filter(models.User.id == sub.user_id).first()
        result.append({
            "user_id": sub.user_id,
            "name": user_info.name,
            "email": user_info.email,
            "project_role": sub.project_role,
            "engineer_type": sub.engineer_type
        })
    
    return result