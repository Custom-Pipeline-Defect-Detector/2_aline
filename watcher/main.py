import hashlib
import os
from pathlib import Path
from typing import List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from celery import Celery

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://aline:aline@localhost:5432/aline")
FILE_STORAGE_ROOT = os.getenv("FILE_STORAGE_ROOT", "/data/aline_docs")
WATCH_PATHS = os.getenv("WATCH_PATHS", FILE_STORAGE_ROOT)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    mime = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    uploader_id = Column(Integer, nullable=True)
    folder_path_hint = Column(String, nullable=True)
    file_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id = Column(Integer, primary_key=True)
    doc_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    extracted_text_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, future=True)
celery_app = Celery("aline", broker=CELERY_BROKER_URL)


def _hash_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _should_ignore(path: Path) -> bool:
    name = path.name
    return name.startswith("~") or name.startswith(".$") or name.endswith(".tmp")


class WatchHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        self._handle(Path(event.src_path))

    def on_modified(self, event):
        if event.is_directory:
            return
        self._handle(Path(event.src_path))

    def _handle(self, path: Path) -> None:
        if _should_ignore(path):
            return
        if not path.exists():
            return
        db = SessionLocal()
        try:
            file_hash = _hash_file(path)
            document = db.query(Document).filter_by(storage_path=str(path)).first()
            if document and document.file_hash == file_hash:
                return
            if not document:
                document = Document(
                    filename=path.name,
                    mime="application/octet-stream",
                    storage_path=str(path),
                    uploader_id=None,
                    folder_path_hint="",
                    file_hash=file_hash,
                )
                db.add(document)
                db.flush()
                version_num = 1
            else:
                document.file_hash = file_hash
                latest = (
                    db.query(DocumentVersion)
                    .filter_by(doc_id=document.id)
                    .order_by(DocumentVersion.version.desc())
                    .first()
                )
                version_num = (latest.version + 1) if latest else 1
            version = DocumentVersion(doc_id=document.id, version=version_num)
            db.add(version)
            db.commit()
            celery_app.send_task("extract_and_propose", args=[version.id])
        finally:
            db.close()


def main():
    paths: List[str] = [p.strip() for p in WATCH_PATHS.split(",") if p.strip()]
    observer = Observer()
    handler = WatchHandler()
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)
        observer.schedule(handler, path, recursive=True)
    observer.start()
    try:
        while True:
            observer.join(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
