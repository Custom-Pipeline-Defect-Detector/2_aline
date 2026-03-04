from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Iterable

from sqlalchemy.orm import Session

from app import models
from app.rbac import has_role


def week_start(value: date | datetime | None) -> date | None:
    """Return ISO week start (Monday) for a date-like value."""
    if value is None:
        return None
    day = value.date() if isinstance(value, datetime) else value
    return day - timedelta(days=day.weekday())


def build_ncr_weekly_counts(
    created_dates: Iterable[datetime | date | None],
    closed_dates: Iterable[date | datetime | None],
) -> list[dict[str, int | str]]:
    opened_weekly: dict[date, int] = defaultdict(int)
    closed_weekly: dict[date, int] = defaultdict(int)

    for created_at in created_dates:
        bucket = week_start(created_at)
        if bucket is not None:
            opened_weekly[bucket] += 1

    for closed_date in closed_dates:
        bucket = week_start(closed_date)
        if bucket is not None:
            closed_weekly[bucket] += 1

    week_keys = sorted(set(opened_weekly) | set(closed_weekly))
    return [
        {
            "week": week.isoformat(),
            "opened": opened_weekly.get(week, 0),
            "closed": closed_weekly.get(week, 0),
        }
        for week in week_keys
    ]


def build_engineering_dashboard(db: Session, user: models.User):
    """Build dashboard data for engineering users showing their projects, tasks, and reporting status"""
    from app.schemas import DashboardEngineering
    
    # Get user's project memberships
    project_memberships = db.query(models.ProjectMember).filter(
        models.ProjectMember.user_id == user.id
    ).all()
    
    projects = []
    for member in project_memberships:
        project = db.query(models.Project).filter(models.Project.id == member.project_id).first()
        if project:
            projects.append({
                "id": project.id,
                "name": project.name,
                "code": project.project_code,
                "role": member.project_role
            })
    
    # Get user's assigned tasks
    assigned_tasks = db.query(models.Task).filter(
        models.Task.assigned_to_user_id == user.id
    ).all()
    
    my_tasks = []
    blocked_tasks = []
    for task in assigned_tasks:
        task_data = {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "due_date": task.due_date,
            "project_id": task.project_id,
            "project_name": task.project.name if task.project else None
        }
        my_tasks.append(task_data)
        if task.status == "blocked":
            blocked_tasks.append(task_data)
    
    # Get pending worklog approvals if user is a lead or PM
    pending_approvals = []
    if has_role(user, ["admin", "manager"]) or any(
        member.project_role in ["lead_engineer", "project_manager"] 
        for member in project_memberships
    ):
        pending_approvals = db.query(models.WorkLog).filter(
            models.WorkLog.submitted_to_user_id == user.id,
            models.WorkLog.status == "submitted"
        ).all()
    
    # Get team members if user is a lead
    team_members = []
    if any(member.project_role in ["lead_engineer", "project_manager"] for member in project_memberships):
        team_members = db.query(models.ProjectMember).filter(
            models.ProjectMember.report_to_user_id == user.id
        ).all()
        team_members = [{
            "id": member.user_id,
            "name": member.user.name if member.user else None,
            "role": member.project_role,
            "engineer_type": member.engineer_type,
            "project_id": member.project_id
        } for member in team_members]
    
    # Calculate task KPIs
    open_tasks = len([t for t in my_tasks if t["status"] in ["open", "in_progress"]])
    in_progress_tasks = len([t for t in my_tasks if t["status"] == "in_progress"])
    blocked_tasks_count = len(blocked_tasks)
    done_tasks = len([t for t in my_tasks if t["status"] == "done"])
    
    return DashboardEngineering(
        my_projects=projects,
        my_tasks=my_tasks,
        blocked_tasks=blocked_tasks,
        worklog_status={
            "pending_approvals": len(pending_approvals),
            "pending_submissions": len([w for w in db.query(models.WorkLog).filter(
                models.WorkLog.user_id == user.id,
                models.WorkLog.status == "draft"
            ).all()])
        },
        task_kpis={
            "open": open_tasks,
            "in_progress": in_progress_tasks,
            "blocked": blocked_tasks_count,
            "done": done_tasks
        },
        my_team=team_members if team_members else [],
        waiting_on_tasks=[]  # Tasks assigned by this user but not updated by assignees
    )


def build_pm_dashboard(db: Session, user: models.User):
    """Build dashboard data for project managers"""
    from app.schemas import DashboardEngineering
    
    # Get projects managed by this user
    managed_projects = db.query(models.ProjectMember).filter(
        models.ProjectMember.user_id == user.id,
        models.ProjectMember.project_role == "project_manager"
    ).all()
    
    projects = []
    for member in managed_projects:
        project = db.query(models.Project).filter(models.Project.id == member.project_id).first()
        if project:
            # Check team completeness
            leads = db.query(models.ProjectMember).filter(
                models.ProjectMember.project_id == project.id,
                models.ProjectMember.project_role == "lead_engineer"
            ).count()
            
            projects.append({
                "id": project.id,
                "name": project.name,
                "code": project.project_code,
                "leads_count": leads,
                "total_members": db.query(models.ProjectMember).filter(
                    models.ProjectMember.project_id == project.id
                ).count()
            })
    
    # Get pending approvals
    pending_approvals = db.query(models.WorkLog).filter(
        models.WorkLog.submitted_to_user_id == user.id,
        models.WorkLog.status == "submitted"
    ).count()
    
    # Get blocked tasks in managed projects
    blocked_tasks = db.query(models.Task).join(models.ProjectMember).filter(
        models.ProjectMember.user_id == user.id,
        models.ProjectMember.project_role == "project_manager",
        models.Task.status == "blocked"
    ).count()
    
    return {
        "managed_projects": projects,
        "team_completeness": {
            "projects_with_missing_leads": len([p for p in projects if p["leads_count"] == 0])
        },
        "daily_reports_summary": {
            "pending_approvals": pending_approvals
        },
        "risks": {
            "blocked_tasks": blocked_tasks,
            "overdue_tasks": db.query(models.Task).join(models.ProjectMember).filter(
                models.ProjectMember.user_id == user.id,
                models.ProjectMember.project_role == "project_manager",
                models.Task.due_date < datetime.now(),
                models.Task.status != "done"
            ).count()
        }
    }
