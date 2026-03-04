from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user
from ..rbac import require_role

router = APIRouter(prefix="/quality", tags=["quality"])

@router.get("/reports", response_model=List[Dict[str, Any]])
def get_quality_reports(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get quality control reports
    """
    query = db.query(models.Document)  # Assuming we're tracking quality via documents
    
    if status:
        if status == "pending":
            query = query.filter(models.Document.processing_status != "completed")
        elif status == "in_review":
            # Filter documents that need review
            query = query.filter(models.Document.needs_review == True)
        elif status == "approved":
            query = query.filter(models.Document.needs_review == False)
        elif status == "rejected":
            query = query.filter(models.Document.processing_error.isnot(None))
    
    documents = query.offset(offset).limit(limit).all()
    
    reports = []
    for doc in documents:
        # Calculate a quality score based on various factors
        score = calculate_quality_score(doc)
        
        reports.append({
            "id": doc.id,
            "title": doc.filename,
            "document_id": f"DOC-{doc.id:03d}",
            "status": "pending",  # Default status since review_status doesn't exist
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.created_at.isoformat(),
            "reviewer": "System",  # Default reviewer since reviewed_by_user doesn't exist
            "score": score
        })
    
    return reports


@router.get("/reports/{report_id}", response_model=Dict[str, Any])
def get_quality_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a specific quality control report
    """
    document = db.query(models.Document).filter(models.Document.id == report_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Quality report not found")
    
    score = calculate_quality_score(document)
    
    return {
        "id": document.id,
        "title": document.filename,
        "document_id": f"DOC-{document.id:03d}",
        "status": "pending",  # Default status since review_status doesn't exist
        "created_at": document.created_at.isoformat(),
        "updated_at": document.created_at.isoformat(),
        "reviewer": "System",  # Default reviewer since reviewed_by_user doesn't exist
        "score": score,
        "details": {
            "filename": document.filename,
            "file_size": getattr(document, 'file_size', 0),  # Default to 0 if file_size doesn't exist
            "content_type": document.mime,
            "extraction_accuracy": getattr(document, 'extraction_accuracy', 0.0),
            "completeness_score": getattr(document, 'completeness_score', 0.0),
            "consistency_score": getattr(document, 'consistency_score', 0.0)
        }
    }


@router.post("/reports/{document_id}/review")
def submit_quality_review(
    document_id: int,
    status: str,
    comment: str = None,
    score: int = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Submit a quality review for a document
    """
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update document review status - only update fields that exist in the Document model
    # Since Document model doesn't have review-related fields, we'll just update the needs_review flag
    if status in ['approved', 'rejected']:
        document.needs_review = False
    elif status == 'in_review':
        document.needs_review = True
    
    # If there's an error in processing, we can set that
    if status == 'rejected' and comment:
        document.processing_error = f"Rejected: {comment}"
    
    db.commit()
    db.refresh(document)
    
    return {"message": "Quality review submitted successfully", "document_id": document.id}


def calculate_quality_score(document: models.Document) -> int:
    """
    Calculate a quality score for a document based on various factors
    """
    # Base score calculation - this is a simplified example
    # In a real implementation, this would consider multiple factors like:
    # - Extraction accuracy
    # - Completeness of extracted data
    # - Consistency of data
    # - Format compliance
    # - Content validation
    
    base_score = 50  # Base score
    
    # Increase score based on processing status
    if document.processing_status == "completed":
        base_score += 20
    elif document.processing_status == "processing":
        base_score += 10
    
    # Additional factors could be added here based on document properties
    if hasattr(document, 'extraction_accuracy'):
        base_score += int(document.extraction_accuracy * 30)
    
    # Cap the score between 0 and 100
    return min(max(base_score, 0), 100)