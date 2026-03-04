from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user
from ..rbac import require_role

router = APIRouter(prefix="/inbox", tags=["inbox"])

@router.get("/items", response_model=List[Dict[str, Any]])
def get_inbox_items(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get items for the user's inbox including documents, proposals, projects, etc.
    """
    inbox_items = []
    
    # Get pending documents
    pending_docs = db.query(models.Document).filter(
        models.Document.processing_status != "completed"
    ).order_by(models.Document.created_at.desc()).limit(20).all()
    
    for doc in pending_docs:
        inbox_items.append({
            "id": f"doc_{doc.id}",
            "title": f"Document: {doc.filename}",
            "description": f"Processing status: {doc.processing_status}",
            "type": "document",
            "priority": "medium",  # Could be determined by document type or other factors
            "status": doc.processing_status,
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.created_at.isoformat()
        })
    
    # Get recent proposals
    recent_proposals = db.query(models.Proposal).order_by(
        models.Proposal.created_at.desc()
    ).limit(20).all()
    
    for proposal in recent_proposals:
        inbox_items.append({
            "id": f"prop_{proposal.id}",
            "title": f"Proposal: {proposal.proposed_action[:50]}",
            "description": f"Proposal for {proposal.target_table}",
            "type": "proposal",
            "priority": "high" if proposal.status == "pending" else "medium",
            "status": proposal.status,
            "created_at": proposal.created_at.isoformat(),
            "updated_at": proposal.created_at.isoformat()
        })
    
    # Get recent projects
    recent_projects = db.query(models.Project).order_by(
        models.Project.created_at.desc()
    ).limit(20).all()
    
    for project in recent_projects:
        inbox_items.append({
            "id": f"proj_{project.id}",
            "title": f"Project: {project.name}",
            "description": project.name or "No description",  # Use project.name since description doesn't exist
            "type": "project",
            "priority": "medium",
            "status": project.status,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.created_at.isoformat()  # Use created_at since updated_at doesn't exist
        })
    
    # Sort by updated date (most recent first)
    inbox_items.sort(key=lambda x: x['updated_at'], reverse=True)
    
    return inbox_items


@router.get("/counts", response_model=Dict[str, int])
def get_inbox_counts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get counts of different types of items in the inbox
    """
    pending_docs_count = db.query(models.Document).filter(
        models.Document.processing_status != "completed"
    ).count()
    
    pending_proposals_count = db.query(models.Proposal).filter(
        models.Proposal.status == "pending"
    ).count()
    
    recent_projects_count = db.query(models.Project).count()
    
    return {
        "pending_documents": pending_docs_count,
        "pending_proposals": pending_proposals_count,
        "recent_projects": recent_projects_count,
        "total_items": pending_docs_count + pending_proposals_count + recent_projects_count
    }