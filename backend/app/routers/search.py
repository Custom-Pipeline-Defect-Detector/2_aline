from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..database import get_db
from ..models import Document, Customer, Project, Proposal, User
from ..auth import get_current_user
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/search")
async def search_all(
    query: str = Query(..., min_length=1, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Search across all entities (documents, customers, projects, proposals) 
    with the given query string.
    """
    try:
        logger.info(f"Performing search with query: {query}")
        
        # Search documents
        document_results = db.query(Document).filter(
            or_(
                Document.filename.ilike(f"%{query}%"),
                Document.extracted_text.ilike(f"%{query}%")
            )
        ).filter(Document.extracted_text.isnot(None)).limit(10).all()
        
        # Search customers
        customer_results = db.query(Customer).filter(
            or_(
                Customer.name.ilike(f"%{query}%"),
                Customer.email.ilike(f"%{query}%"),
                Customer.company.ilike(f"%{query}%")
            )
        ).limit(10).all()
        
        # Search projects
        project_results = db.query(Project).filter(
            or_(
                Project.name.ilike(f"%{query}%"),
                Project.description.ilike(f"%{query}%")
            )
        ).limit(10).all()
        
        # Search proposals
        proposal_results = db.query(Proposal).filter(
            or_(
                Proposal.title.ilike(f"%{query}%"),
                Proposal.description.ilike(f"%{query}%")
            )
        ).limit(10).all()
        
        # Format results
        results = {
            "documents": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "type": doc.mime,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "processing_status": doc.processing_status
                }
                for doc in document_results
            ],
            "customers": [
                {
                    "id": cust.id,
                    "name": cust.name,
                    "email": cust.email,
                    "company": cust.company
                }
                for cust in customer_results
            ],
            "projects": [
                {
                    "id": proj.id,
                    "name": proj.name,
                    "description": proj.description,
                    "status": proj.status
                }
                for proj in project_results
            ],
            "proposals": [
                {
                    "id": prop.id,
                    "title": prop.title,
                    "description": prop.description,
                    "status": prop.status
                }
                for prop in proposal_results
            ]
        }
        
        # Add counts
        results["counts"] = {
            "documents": len(results["documents"]),
            "customers": len(results["customers"]),
            "projects": len(results["projects"]),
            "proposals": len(results["proposals"])
        }
        
        logger.info(f"Search completed. Found {sum(results['counts'].values())} total results")
        return results
    except Exception as e:
        logger.error(f"Error in search_all: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/search/documents")
async def search_documents(
    query: str = Query(..., min_length=1, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Search specifically in documents.
    """
    try:
        logger.info(f"Performing document search with query: {query}")
        documents = db.query(Document).filter(
            or_(
                Document.filename.ilike(f"%{query}%"),
                Document.extracted_text.ilike(f"%{query}%")
            )
        ).filter(Document.extracted_text.isnot(None)).limit(20).all()
        
        result = [
            {
                "id": doc.id,
                "filename": doc.filename,
                "type": doc.mime,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "processing_status": doc.processing_status,
                "summary": doc.agent_summary[:200] + "..." if doc.agent_summary and len(doc.agent_summary) > 200 else doc.agent_summary
            }
            for doc in documents
        ]
        logger.info(f"Document search completed. Found {len(result)} results")
        return result
    except Exception as e:
        logger.error(f"Error in search_documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Document search failed: {str(e)}")

@router.get("/search/customers")
async def search_customers(
    query: str = Query(..., min_length=1, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Search specifically in customers.
    """
    try:
        logger.info(f"Performing customer search with query: {query}")
        customers = db.query(Customer).filter(
            or_(
                Customer.name.ilike(f"%{query}%"),
                Customer.email.ilike(f"%{query}%"),
                Customer.company.ilike(f"%{query}%")
            )
        ).limit(20).all()
        
        result = [
            {
                "id": cust.id,
                "name": cust.name,
                "email": cust.email,
                "company": cust.company,
                "phone": cust.phone
            }
            for cust in customers
        ]
        logger.info(f"Customer search completed. Found {len(result)} results")
        return result
    except Exception as e:
        logger.error(f"Error in search_customers: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Customer search failed: {str(e)}")

@router.get("/search/projects")
async def search_projects(
    query: str = Query(..., min_length=1, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Search specifically in projects.
    """
    try:
        logger.info(f"Performing project search with query: {query}")
        projects = db.query(Project).filter(
            or_(
                Project.name.ilike(f"%{query}%"),
                Project.description.ilike(f"%{query}%")
            )
        ).limit(20).all()
        
        result = [
            {
                "id": proj.id,
                "name": proj.name,
                "description": proj.description,
                "status": proj.status
            }
            for proj in projects
        ]
        logger.info(f"Project search completed. Found {len(result)} results")
        return result
    except Exception as e:
        logger.error(f"Error in search_projects: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Project search failed: {str(e)}")

@router.get("/search/proposals")
async def search_proposals(
    query: str = Query(..., min_length=1, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Search specifically in proposals.
    """
    try:
        logger.info(f"Performing proposal search with query: {query}")
        proposals = db.query(Proposal).filter(
            or_(
                Proposal.title.ilike(f"%{query}%"),
                Proposal.description.ilike(f"%{query}%")
            )
        ).limit(20).all()
        
        result = [
            {
                "id": prop.id,
                "title": prop.title,
                "description": prop.description,
                "status": prop.status
            }
            for prop in proposals
        ]
        logger.info(f"Proposal search completed. Found {len(result)} results")
        return result
    except Exception as e:
        logger.error(f"Error in search_proposals: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Proposal search failed: {str(e)}")
