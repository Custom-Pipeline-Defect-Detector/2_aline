from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Document, Customer, Project, Proposal, User, Message, Notification, Task, WorkLog, NCR, Issue, InspectionRecord, ProjectMember
from app.auth import get_current_user
from app.deps import require_roles
from app.rbac import DASHBOARD_READ_ROLES
from app import schemas
from app.services.dashboard import build_ncr_weekly_counts, build_engineering_dashboard, build_pm_dashboard

router = APIRouter()

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    range: str = "month",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get dashboard statistics focusing on projects, work orders, quality, and clients
    instead of document-centric metrics.
    """
    # Calculate date range based on parameter
    now = datetime.utcnow()
    if range == "week":
        start_date = now - timedelta(days=7)
    elif range == "quarter":
        start_date = now - timedelta(days=90)
    else:  # month
        start_date = now - timedelta(days=30)

    # Project statistics
    total_projects = db.query(Project).count()
    active_projects = db.query(Project).filter(
        Project.status != 'completed'
    ).count()
    completed_projects = db.query(Project).filter(
        Project.status == 'completed'
    ).count()
    
    # Work order (Task) statistics
    total_tasks = db.query(Task).count()
    open_tasks = db.query(Task).filter(Task.status == 'open').count()
    in_progress_tasks = db.query(Task).filter(Task.status == 'in_progress').count()
    completed_tasks = db.query(Task).filter(Task.status == 'completed').count()
    
    # Quality statistics (NCRs, Issues, Inspections)
    total_ncrs = db.query(NCR).count()
    open_ncrs = db.query(NCR).filter(NCR.status == 'open').count()
    closed_ncrs = db.query(NCR).filter(NCR.status == 'closed').count()
    total_issues = db.query(Issue).count()
    open_issues = db.query(Issue).filter(Issue.status == 'open').count()
    total_inspections = db.query(InspectionRecord).count()
    open_inspections = db.query(InspectionRecord).filter(InspectionRecord.status == 'open').count()
    
    # Client (Customer) statistics
    total_customers = db.query(Customer).count()
    active_customers = db.query(Customer).filter(Customer.status == 'active').count()
    lead_customers = db.query(Customer).filter(Customer.status == 'lead').count()
    total_proposals = db.query(Proposal).count()
    
    # Pending proposals
    pending_proposals = db.query(Proposal).filter(
        Proposal.status == 'pending'
    ).count()
    
    # Approved proposals
    approved_proposals = db.query(Proposal).filter(
        Proposal.status == 'approved'
    ).count()
    
    # Work log statistics
    total_work_logs = db.query(WorkLog).count()
    recent_work_logs = db.query(WorkLog).filter(WorkLog.date >= start_date.date()).count()
    
    # Project status distribution
    project_statuses = db.query(
        Project.status.label('status'),
        func.count(Project.id).label('count')
    ).group_by(Project.status).all()
    
    project_status_data = [
        {"status": ps.status or "Unknown", "count": ps.count} 
        for ps in project_statuses
    ]
    
    # Task trends over time
    if range == "week":
        date_group = func.to_char(Task.created_at, 'YYYY-MM-DD')
    elif range == "quarter":
        date_group = func.to_char(Task.created_at, 'YYYY-"Q"Q')
    else:  # month
        date_group = func.to_char(Task.created_at, 'YYYY-MM')
    
    task_trends = db.query(
        date_group.label('date'),
        func.count(Task.id).label('count')
    ).filter(Task.created_at >= start_date).group_by(date_group).order_by('date').all()
    
    task_trends_data = [
        {"date": str(dt.date), "count": dt.count} 
        for dt in task_trends
    ]
    
    # Recent activity (projects, tasks, customers, quality items)
    recent_activities = []
    
    # Recent projects
    recent_projects = db.query(Project).filter(Project.created_at >= start_date).order_by(desc(Project.created_at)).limit(5).all()
    for proj in recent_projects:
        recent_activities.append({
            "type": "project",
            "action": f"Created project: {proj.name}",
            "description": f"Project: {proj.name} for {proj.customer.name if proj.customer else 'Unknown Customer'}",
            "timestamp": proj.created_at.strftime("%Y-%m-%d %H:%M") if proj.created_at else "Unknown"
        })
    
    # Recent tasks
    recent_tasks = db.query(Task).filter(Task.created_at >= start_date).order_by(desc(Task.created_at)).limit(5).all()
    for task in recent_tasks:
        recent_activities.append({
            "type": "task",
            "action": f"Created task: {task.title}",
            "description": f"Task in project: {task.project.name if task.project else 'Unknown Project'}",
            "timestamp": task.created_at.strftime("%Y-%m-%d %H:%M") if task.created_at else "Unknown"
        })
    
    # Recent customers
    recent_customers = db.query(Customer).filter(Customer.created_at >= start_date).order_by(desc(Customer.created_at)).limit(5).all()
    for cust in recent_customers:
        recent_activities.append({
            "type": "customer",
            "action": f"Added customer: {cust.name}",
            "description": f"Customer status: {cust.status}",
            "timestamp": cust.created_at.strftime("%Y-%m-%d %H:%M") if cust.created_at else "Unknown"
        })
    
    # Recent NCRs
    recent_ncrs = db.query(NCR).filter(NCR.created_at >= start_date).order_by(desc(NCR.created_at)).limit(5).all()
    for ncr in recent_ncrs:
        recent_activities.append({
            "type": "ncr",
            "action": f"NCR opened: {ncr.description[:50]}...",
            "description": f"In project: {ncr.project.name if ncr.project else 'Unknown Project'}",
            "timestamp": ncr.created_at.strftime("%Y-%m-%d %H:%M") if ncr.created_at else "Unknown"
        })
    
    # Sort activities by timestamp descending
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_activities[:8]  # Limit to 8 most recent
    
    # Top contributors (users with most task assignments and work logs)
    top_contributors = db.query(
        User.name.label('name'),
        User.email.label('email'),
        func.count(Task.id).label('tasks'),
        func.count(WorkLog.id).label('work_logs'),
        (func.coalesce(func.count(Task.id), 0) + func.coalesce(func.count(WorkLog.id), 0)).label('score')
    ).outerjoin(Task, Task.owner_id == User.id).outerjoin(WorkLog, WorkLog.user_id == User.id).group_by(User.id, User.name, User.email).order_by(desc((func.coalesce(func.count(Task.id), 0) + func.coalesce(func.count(WorkLog.id), 0)))).limit(10).all()
    
    top_contributors_data = [
        {
            "name": tc.name or "Unknown User",
            "email": tc.email or "",
            "tasks": tc.tasks or 0,
            "work_logs": tc.work_logs or 0,
            "score": min(int(tc.score or 0), 100)  # Cap score at 100%
        }
        for tc in top_contributors
    ]
    
    # Additional stats for the dashboard cards
    pending_reviews = db.query(Notification).filter(Notification.is_read == False).count()
    overdue_tasks = db.query(Task).filter(Task.due_date < datetime.now(), Task.status != 'completed').count()
    
    return {
        "total_projects": total_projects,
        "active_projects": active_projects,
        "total_tasks": total_tasks,
        "open_tasks": open_tasks,
        "total_customers": total_customers,
        "active_customers": active_customers,
        "total_ncrs": total_ncrs,
        "open_ncrs": open_ncrs,
        "pending_reviews": pending_reviews,
        "overdue_tasks": overdue_tasks,
        "project_statuses": project_status_data,
        "task_trends": task_trends_data,
        "recent_activity": recent_activities,
        "top_contributors": top_contributors_data
    }


@router.get("/dashboard/engineering", response_model=schemas.DashboardEngineering, dependencies=[Depends(require_roles(DASHBOARD_READ_ROLES))])
def get_engineering_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get engineering dashboard data showing projects, tasks, and reporting status"""
    return build_engineering_dashboard(db, current_user)
