from pathlib import Path
import hashlib

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db, require_roles, get_current_user
from app.rbac import DOCUMENTS_READ_ROLES, DOCUMENTS_WRITE_ROLES
from app.core.config import settings
from app.tasks import extract_and_propose, process_document

router = APIRouter(prefix="/documents", tags=["documents"])


def _hash_file(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


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
                    "created_at": proposal.created_at,
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
        created_at=document.created_at,
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
    storage_root = Path(settings.file_storage_root)
    storage_root.mkdir(parents=True, exist_ok=True)

    contents = file.file.read()
    file_hash = _hash_file(contents)
    filename = file.filename or "upload"
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

    return _serialize_document(document)


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
    documents = db.query(models.Document).order_by(models.Document.created_at.desc()).all()
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
    db.refresh(document)
    return _serialize_document(document)


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
