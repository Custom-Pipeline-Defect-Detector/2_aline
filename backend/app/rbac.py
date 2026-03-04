from __future__ import annotations

from typing import Final
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from . import models
from .auth import get_current_user
from .database import get_db

READ_ROLES_ALL: Final = ["Admin", "Manager", "PM", "Sales", "Technician", "QC", "Viewer"]
WRITE_ROLES_DEFAULT: Final = ["Admin", "Manager", "PM", "Sales", "Technician", "QC"]
APPROVE_ROLES: Final = ["Admin", "Manager", "PM"]

# Engineer roles have restricted access - only to their projects
ENGINEER_READ_ROLES: Final = ["Admin", "Manager", "PM", "Sales", "Technician", "QC", "Viewer", "Engineer"]
ENGINEER_WRITE_ROLES: Final = ["Admin", "Manager", "PM", "Technician", "QC", "Engineer"]

CUSTOMERS_READ_ROLES: Final = READ_ROLES_ALL
CUSTOMERS_WRITE_ROLES: Final = ["Admin", "Manager", "Sales", "PM"]

DOCUMENTS_READ_ROLES: Final = ENGINEER_READ_ROLES  # Engineers can read documents
DOCUMENTS_WRITE_ROLES: Final = ["Admin", "Manager", "PM", "Sales", "Engineer", "Technician", "QC"]

PROPOSALS_READ_ROLES: Final = READ_ROLES_ALL  # Engineers excluded from proposals
PROPOSALS_APPROVE_ROLES: Final = READ_ROLES_ALL

QUALITY_READ_ROLES: Final = ENGINEER_READ_ROLES  # Engineers can read quality data
QUALITY_WRITE_ROLES: Final = ["Admin", "Manager", "QC", "Engineer", "Technician"]

AUDIT_READ_ROLES: Final = ["Admin", "Manager", "PM", "QC"]  # Engineers excluded from audit

TASKS_READ_ROLES: Final = ENGINEER_READ_ROLES
TASKS_WRITE_ROLES: Final = ENGINEER_WRITE_ROLES

PROJECTS_READ_ROLES: Final = ENGINEER_READ_ROLES  # Engineers can read projects
PROJECTS_WRITE_ROLES: Final = WRITE_ROLES_DEFAULT  # Only higher roles can write projects

NOTIFICATION_READ_ROLES: Final = ENGINEER_READ_ROLES
NOTIFICATION_WRITE_ROLES: Final = ENGINEER_WRITE_ROLES

DASHBOARD_READ_ROLES: Final = ENGINEER_READ_ROLES

ADMIN_ONLY_ROLES: Final = ["Admin"]
MANAGER_ADMIN_ROLES: Final = ["Admin", "Manager"]

def has_role(user: models.User, roles: list[str]) -> bool:
    """Check if user has any of the specified roles"""
    user_roles = [role.name.lower() for role in user.roles]
    check_roles = [role.lower() for role in roles]
    return any(role in user_roles for role in check_roles)


def require_role(required_roles: list):
    """Dependency to check if user has required role(s)"""
    async def role_checker(current_user: models.User = Depends(get_current_user)):
        user_roles = [role.name for role in current_user.roles]
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(status_code=403, detail="Operation not permitted")
        return current_user
    return role_checker


def require_project_access():
    """Dependency to check if user has access to specific project based on project membership"""
    async def project_access_checker(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
    ):
        # Admins and Managers have access to all projects
        user_roles = [role.name for role in current_user.roles]
        if "Admin" in user_roles or "Manager" in user_roles:
            return current_user
            
        # Check if user is assigned to this project
        project_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.user_id == current_user.id
        ).first()
        
        if not project_member:
            raise HTTPException(status_code=403, detail="Access to project denied")
            
        return current_user
    return project_access_checker
