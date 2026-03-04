from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from typing import List
import uuid
import os
from datetime import datetime
import asyncio
from sqlalchemy.orm import Session

from ..models import User
from ..database import get_db
from ..deps import get_current_active_user
from ..schemas import DocumentResponse
from ..services.document_processor import DocumentProcessor

router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload a document for processing
    """
    try:
        processor = DocumentProcessor(db)
        result = await processor.upload_document(file, current_user.id)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/status/{document_id}")
async def get_document_status(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the processing status of a document
    """
    try:
        processor = DocumentProcessor(db)
        result = processor.get_document_status(document_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/process/{document_id}")  # Changed to POST since this triggers an action
async def process_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger processing of a document
    """
    try:
        processor = DocumentProcessor(db)
        result = await processor.process_document(document_id)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all")
async def get_all_documents(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all documents for the current user
    """
    try:
        processor = DocumentProcessor(db)
        documents = processor.get_user_documents(current_user.id)
        return {
            "documents": documents,
            "total_count": len(documents),
            "user_id": current_user.id,
            "message": f"Retrieved {len(documents)} documents for user {current_user.username}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
