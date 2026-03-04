from pathlib import Path
import hashlib
import mimetypes
import magic  # python-magic for better MIME type detection
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app import models, schemas
from app.deps import get_db, require_roles, get_current_user
from app.rbac import DOCUMENTS_READ_ROLES, DOCUMENTS_WRITE_ROLES
from app.core.config import settings
from app.tasks import extract_and_propose, process_document
from app.security import sanitize_input, is_safe_filename

router = APIRouter(prefix="/documents", tags=["documents"])

# Define allowed file types and maximum size
ALLOWED_EXTENSIONS: set = set(settings.allowed_file_types.split(","))
MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # Convert MB to bytes (using 50MB as default)


def _allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _validate_file_size(file: UploadFile) -> None:
    """Validate that the uploaded file is within the allowed size limit."""
    # Read the file to check its size
    file.file.seek(0, 2)  # Seek to end of file
    file_size = file.file.tell()
    file.file.seek(0)  # Reset file pointer to beginning
    
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE}MB"
        )


def _validate_file_type(file: UploadFile) -> None:
    """Validate that the file type is allowed using both extension and content detection."""
    if not _allowed_file(file.filename or ""):
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {settings.allowed_file_types}"
        )
    
    # Read file contents to detect actual MIME type with python-magic
    file.file.seek(0)  # Go to beginning of file
    contents = file.file.read(2048)  # Read first 2KB to detect type
    detected_mime = magic.from_buffer(contents, mime=True)
    file.file.seek(0)  # Reset file pointer to beginning
    
    # Check if detected MIME type is in allowed types
    if not any(allowed_type in detected_mime.lower() for allowed_type in ALLOWED_EXTENSIONS):
        # For security, we'll also check against common dangerous file types
        dangerous_types = ['application/x-executable', 'application/x-msdownload', 'application/x-sh', 'text/html', 'application/javascript', 'text/javascript']
        if any(dangerous in detected_mime.lower() for dangerous in dangerous_types):
            raise HTTPException(
                status_code=400,
                detail="Potentially dangerous file type detected"
            )
        # Additional check: if extension suggests it's allowed but content detection says otherwise, warn
        file_ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if file_ext in ALLOWED_EXTENSIONS and detected_mime not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Suspicious file detected. Extension suggests {file_ext}, but content appears to be {detected_mime}"
            )


def _hash_file(contents: bytes) -> str:
    """Generate SHA-256 hash of file contents."""
    return hashlib.sha256(contents).hexdigest()


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks."""
    # Sanitize the input first
    sanitized = sanitize_input(filename) if filename else filename
    if not sanitized:
        raise HTTPException(status_code=400, detail="Invalid filename provided")
    
    # Check if filename is safe
    if not is_safe_filename(sanitized):
        raise HTTPException(status_code=400, detail="Unsafe filename detected")
    
    # Remove any path separators to prevent directory traversal
    sanitized = sanitized.replace("/", "_").replace("\\", "_")
    # Limit length to prevent overly long filenames
    return sanitized[:255]


def _get_document_with_relations(db: Session, document_id: int) -> models.Document:
    """Helper function to get a document with all related data loaded."""
    return db.query(models.Document)\
        .options(selectinload(models.Document.customer))\
        .options(selectinload(models.Document.project))\
        .options(selectinload(models.Document.versions.and_(models.DocumentVersion.proposals)))\
        .filter(models.Document.id == document_id).first()


def _serialize_document(document: models.Document) -> schemas.DocumentOut:
    proposals = []
    for version in document.versions:
        for proposal in version.proposals:
            proposals.append(
                {
                    "id": proposal.id,
                    "status": proposal.status,
                    "proposed_action": proposal.proposed_action,
                    "target_table": proposal.target_table,
                    "created_at": proposal.created_at.isoformat() if proposal.created_at else None,
                }
            )
    return schemas.DocumentOut(
        id=document.id,
        filename=document.filename,
        mime=document.mime,
        storage_path=document.storage_path,
        file_hash=document.file_hash,
        processing_status=document.processing_status,
        document_type=document.document_type,
        classification_confidence=document.classification_confidence,
        extracted_fields=document.extracted_fields,
        agent_summary=document.agent_summary,
        needs_review=document.needs_review,
        processing_error=document.processing_error,
        customer_id=document.customer_id,
        project_id=document.project_id,
        customer_name=document.customer.name if document.customer else None,
        project_name=document.project.name if document.project else None,
        created_at=document.created_at.isoformat() if document.created_at else None,
        versions=[schemas.DocumentVersionOut.model_validate(version) for version in document.versions],
        proposals=proposals,
    )


@router.post(
    "/upload",
    response_model=schemas.DocumentOut,
    dependencies=[
        Depends(
            require_roles(DOCUMENTS_WRITE_ROLES)
        )
    ],
)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Validate file type and size
    _validate_file_type(file)
    _validate_file_size(file)
    
    storage_root = Path(settings.file_storage_root)
    storage_root.mkdir(parents=True, exist_ok=True)

    contents = file.file.read()
    file_hash = _hash_file(contents)
    filename = _sanitize_filename(file.filename or "upload")
    storage_path = storage_root / f"{file_hash}_{filename}"
    storage_path.write_bytes(contents)

    document = models.Document(
        filename=filename,
        mime=file.content_type or "application/octet-stream",
        storage_path=str(storage_path),
        uploader_id=current_user.id,
        folder_path_hint="",
        file_hash=file_hash,
        processing_status="queued",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    version = models.DocumentVersion(doc_id=document.id, version=1)
    db.add(version)
    db.commit()
    db.refresh(version)

    if settings.run_tasks_inline and background_tasks:
        background_tasks.add_task(extract_and_propose, version.id)
        background_tasks.add_task(process_document, document.id)
    else:
        extract_and_propose.delay(version.id)
        process_document.delay(document.id)

    # Get the document with all related data loaded
    document_with_relations = db.query(models.Document)\
        .options(selectinload(models.Document.customer))\
        .options(selectinload(models.Document.project))\
        .options(selectinload(models.Document.versions.and_(models.DocumentVersion.proposals)))\
        .filter(models.Document.id == document.id).first()
    
    return _serialize_document(document_with_relations)


@router.get(
    "",
    response_model=list[schemas.DocumentOut],
    dependencies=[
        Depends(
            require_roles(DOCUMENTS_READ_ROLES)
        )
    ],
)
def list_documents(db: Session = Depends(get_db)):
    documents = db.query(models.Document)\
        .options(selectinload(models.Document.customer))\
        .options(selectinload(models.Document.project))\
        .options(selectinload(models.Document.versions.and_(models.DocumentVersion.proposals)))\
        .order_by(models.Document.created_at.desc()).all()
    return [_serialize_document(doc) for doc in documents]


@router.post(
    "/{document_id}/reprocess",
    response_model=schemas.ReprocessJobOut,
    status_code=202,
    dependencies=[
        Depends(
            require_roles(DOCUMENTS_WRITE_ROLES)
        )
    ],
)
def reprocess_document(document_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    document = db.query(models.Document).filter_by(id=document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    document.processing_status = "queued"
    document.processing_error = None
    document.needs_review = False
    db.commit()

    if settings.run_tasks_inline:
        background_tasks.add_task(process_document, document.id)
        job_id = f"inline-{document.id}"
    else:
        async_result = process_document.delay(document.id)
        job_id = async_result.id

    return schemas.ReprocessJobOut(job_id=job_id, document_id=document.id, status=document.processing_status)


@router.get(
    "/{document_id}",
    response_model=schemas.DocumentOut,
    dependencies=[
        Depends(
            require_roles(DOCUMENTS_READ_ROLES)
        )
    ],
)
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = _get_document_with_relations(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return _serialize_document(document)


@router.patch(
    "/{document_id}",
    response_model=schemas.DocumentOut,
    dependencies=[
        Depends(
            require_roles(DOCUMENTS_WRITE_ROLES)
        )
    ],
)
def update_document(document_id: int, payload: schemas.DocumentUpdate, db: Session = Depends(get_db)):
    document = db.query(models.Document).filter_by(id=document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    updates = payload.model_dump(exclude_unset=True)
    if "processing_status" in updates and updates["processing_status"] not in {
        "queued",
        "processing",
        "done",
        "failed",
    }:
        raise HTTPException(status_code=400, detail="Invalid processing status")

    for field, value in updates.items():
        setattr(document, field, value)

    db.commit()
    # Refresh the document with all relations loaded
    document_with_relations = _get_document_with_relations(db, document_id)
    return _serialize_document(document_with_relations)


@router.delete(
    "/{document_id}",
    status_code=204,
    dependencies=[
        Depends(
            require_roles(DOCUMENTS_WRITE_ROLES)
        )
    ],
)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(models.Document).filter_by(id=document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.processing_status != "queued":
        raise HTTPException(status_code=400, detail="Only queued documents can be deleted")

    storage_path = Path(document.storage_path)
    if storage_path.exists():
        storage_path.unlink()

    db.delete(document)
    db.commit()
    return None


@router.get(
    "/{document_id}/download",
    response_class=FileResponse,
    dependencies=[
        Depends(
            require_roles(DOCUMENTS_READ_ROLES)
        )
    ],
)
def download_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(models.Document).filter_by(id=document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(path=document.storage_path, filename=document.filename, media_type=document.mime)


@router.get(
    "/{document_id}/reprocess-status",
    response_model=schemas.DocumentProcessingStatusOut,
    dependencies=[
        Depends(
            require_roles(DOCUMENTS_READ_ROLES)
        )
    ],
)
def get_reprocess_status(document_id: int, db: Session = Depends(get_db)):
    document = db.query(models.Document).filter_by(id=document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return schemas.DocumentProcessingStatusOut(
        document_id=document.id, status=document.processing_status, processing_error=document.processing_error
    )


@router.post(
    "/{document_id}/retry",
    response_model=schemas.DocumentOut,
    dependencies=[
        Depends(
            require_roles(DOCUMENTS_WRITE_ROLES)
        )
    ],
)
def retry_failed_document(document_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    document = db.query(models.Document).filter_by(id=document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.processing_status != "failed":
        raise HTTPException(status_code=400, detail="Only failed documents can be retried")
    
    # Reset document status to queued for retry
    document.processing_status = "queued"
    document.processing_error = None
    db.commit()
    db.refresh(document)

    # Re-run the processing tasks
    if settings.run_tasks_inline:
        background_tasks.add_task(process_document, document.id)
    else:
        process_document.delay(document.id)

    # Return the updated document
    document_with_relations = _get_document_with_relations(db, document_id)
    return _serialize_document(document_with_relations)


@router.get("/download-excel/{filename:path}")
def download_excel_file(filename: str, db: Session = Depends(get_db)):
    """Download an Excel file generated by the AI assistant."""
    # Sanitize the filename to prevent path traversal attacks
    if not is_safe_filename(filename):
        raise HTTPException(status_code=400, detail="Unsafe filename detected")
    
    # Construct the file path
    uploads_dir = Path("uploads")
    file_path = uploads_dir / filename
    
    # Check if the file exists
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Excel file not found")
    
    # Verify that the file is indeed an Excel file
    if not (file_path.suffix.lower() == '.xlsx' or file_path.suffix.lower() == '.xls'):
        raise HTTPException(status_code=400, detail="File is not an Excel file")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
