import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import asyncio
import logging
import json

from sqlalchemy.orm import Session

from ..models import Document, User
from ..extract_text import extract_text_from_file
from ..doc_agent import process_document_with_agents

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, db_session: Session):
        self.db = db_session

    async def upload_document(self, file, current_user_id: str) -> Dict[str, Any]:
        """
        Upload and save a document to the system
        """
        try:
            # Validate file type
            allowed_types = [".pdf", ".docx", ".txt", ".xlsx", ".pptx"]
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if file_ext not in allowed_types:
                raise ValueError(f"File type not allowed. Allowed types: {', '.join(allowed_types)}")
            
            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}_{file.filename}"
            file_path = os.path.join("uploads", unique_filename)
            
            # Create uploads directory if it doesn't exist
            os.makedirs("uploads", exist_ok=True)
            
            # Save file
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Create document record in database
            document = Document(
                id=str(uuid.uuid4()),
                filename=file.filename,
                mime=file_ext,
                storage_path=file_path,
                uploader_id=current_user_id,
                file_hash=str(uuid.uuid4()),  # Generate a unique hash for the file
                processing_status="queued",  # Default to queued for processing
                created_at=datetime.utcnow()
            )
            
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            
            # Get the user who uploaded the document
            user = self.db.query(User).filter(User.id == current_user_id).first()
            username = user.username if user else "Unknown User"
            
            # Log the document upload event
            logger.info(f"Document {document.filename} uploaded by {username} (ID: {current_user_id})")
            
            return {
                "id": document.id,
                "filename": document.filename,
                "file_type": document.mime,
                "file_size": os.path.getsize(file_path),
                "uploaded_at": document.created_at,
                "status": document.processing_status,
                "message": "Document uploaded successfully"
            }
            
        except Exception as e:
            logger.error(f"Error uploading document: {str(e)}")
            raise

    async def process_document(self, document_id: str) -> Dict[str, Any]:
        """
        Process a document with AI agents
        """
        try:
            # Get document from database
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document with ID {document_id} not found")
            
            # Get the user who uploaded the document
            user = self.db.query(User).filter(User.id == document.uploader_id).first()
            username = user.username if user else "Unknown User"
            
            # Update status to processing
            document.processing_status = "processing"
            document.extracted_fields = {
                **(document.extracted_fields or {}),
                "processing_started_at": datetime.utcnow().isoformat(),
                "progress": 25
            }
            self.db.commit()
            
            # Log the processing start event
            logger.info(f"Started processing document {document.filename} for {username} (ID: {document.uploader_id})")
            
            # Extract text from the document
            text_content = extract_text_from_file(document.storage_path)
            
            # Update progress to 50%
            document.extracted_fields = {
                **(document.extracted_fields or {}),
                "progress": 50
            }
            self.db.commit()
            
            # Process document with AI agents
            result = process_document_with_agents(text_content)
            
            # Update progress to 75%
            document.extracted_fields = {
                **(document.extracted_fields or {}),
                "progress": 75
            }
            self.db.commit()
            
            # Update document with processing results
            document.processing_status = "completed"
            document.last_processed_at = datetime.utcnow()
            document.extracted_fields = {
                **(document.extracted_fields or {}),
                "extraction_result": result,
                "processed_by_ai": True,
                "progress": 100,
                "processing_completed_at": datetime.utcnow().isoformat()
            }
            
            self.db.commit()
            self.db.refresh(document)
            
            # Log the processing completion event
            logger.info(f"Completed processing document {document.filename} for {username} (ID: {document.uploader_id})")
            
            return {
                "document_id": document.id,
                "status": document.processing_status,
                "message": "Document processed successfully",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            
            # Update document status to failed
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.processing_status = "failed"
                document.extracted_fields = {
                    **(document.extracted_fields or {}),
                    "error": str(e),
                    "progress": 0,
                    "processing_failed_at": datetime.utcnow().isoformat()
                }
                self.db.commit()
            
            # Get the user who uploaded the document
            if document:
                user = self.db.query(User).filter(User.id == document.uploader_id).first()
                username = user.username if user else "Unknown User"
                
                # Log the processing failure event
                logger.error(f"Failed processing document {document.filename} for {username} (ID: {document.uploader_id}): {str(e)}")
            
            raise

    def get_document_status(self, document_id: str) -> Dict[str, Any]:
        """
        Get the processing status of a document
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {
                    "document_id": document_id,
                    "status": "not_found",
                    "progress": 0,
                    "updated_at": datetime.utcnow(),
                    "message": "Document not found"
                }
            
            # Get progress from extracted_fields if available, otherwise calculate based on status
            progress = (document.extracted_fields or {}).get("progress", self._get_document_progress(document.processing_status))
            
            return {
                "document_id": document.id,
                "status": document.processing_status,
                "progress": progress,
                "updated_at": document.updated_at or document.created_at,
                "metadata": document.extracted_fields
            }
            
        except Exception as e:
            logger.error(f"Error getting document status {document_id}: {str(e)}")
            raise

    def get_user_documents(self, user_id: str) -> list:
        """
        Get all documents for a specific user
        """
        try:
            documents = self.db.query(Document).filter(Document.uploader_id == user_id).all()
            
            return [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "file_type": doc.mime,
                    "file_size": os.path.getsize(doc.storage_path) if os.path.exists(doc.storage_path) else 0,
                    "uploaded_at": doc.created_at,
                    "status": doc.processing_status,
                    "progress": (doc.extracted_fields or {}).get("progress", self._get_document_progress(doc.processing_status)),
                    "summary": (doc.extracted_fields or {}).get("summary", f"Uploaded document: {doc.filename}"),
                    "processed_at": doc.last_processed_at,
                    "metadata": doc.extracted_fields
                }
                for doc in documents
            ]
            
        except Exception as e:
            logger.error(f"Error getting user documents for user {user_id}: {str(e)}")
            raise

    def _get_document_progress(self, status: str) -> int:
        """
        Helper method to get progress percentage based on status
        """
        progress_map = {
            "uploaded": 10,
            "processing": 50,
            "completed": 100,
            "failed": 0
        }
        return progress_map.get(status, 0)
