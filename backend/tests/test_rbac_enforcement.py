from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.deps import get_current_user, get_db
from app.core.config import settings
from app.routers import dashboard, documents, ncrs, projects, tasks, worklogs


class _Role:
    def __init__(self, name: str):
        self.name = name


class _User:
    def __init__(self, user_id: int, roles: list[str]):
        self.id = user_id
        self.roles = [_Role(r) for r in roles]


def _make_session():
    engine = create_engine(
        'sqlite+pysqlite:///:memory:',
        future=True,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE customers (id INTEGER PRIMARY KEY, name VARCHAR, aliases TEXT, status VARCHAR, industry VARCHAR, owner_id INTEGER, notes TEXT, tags TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)"))
        conn.execute(text("CREATE TABLE projects (id INTEGER PRIMARY KEY, project_code VARCHAR, name VARCHAR, customer_id INTEGER, status VARCHAR, stage VARCHAR, value_amount FLOAT, currency VARCHAR, start_date DATE, due_date DATE, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"))
        conn.execute(text("CREATE TABLE milestones (id INTEGER PRIMARY KEY, project_id INTEGER, name VARCHAR, due_date DATE, status VARCHAR, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"))
        conn.execute(text("CREATE TABLE tasks (id INTEGER PRIMARY KEY, project_id INTEGER, title VARCHAR, description TEXT, owner_id INTEGER, due_date DATE, status VARCHAR, priority VARCHAR, type VARCHAR, completed_at DATETIME, source_doc_id INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"))
        conn.execute(text("CREATE TABLE work_logs (id INTEGER PRIMARY KEY, user_id INTEGER, project_id INTEGER, date DATE, summary TEXT, derived_from_doc_id INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"))
        conn.execute(text("CREATE TABLE ncrs (id INTEGER PRIMARY KEY, project_id INTEGER, description TEXT, root_cause TEXT, corrective_action TEXT, status VARCHAR, source_doc_id INTEGER, opened_date DATE, closed_date DATE, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"))
        conn.execute(text("CREATE TABLE issues (id INTEGER PRIMARY KEY, project_id INTEGER, severity VARCHAR, description TEXT, owner_id INTEGER, status VARCHAR, source_doc_id INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"))
        conn.execute(text("CREATE TABLE proposals (id INTEGER PRIMARY KEY, doc_version_id INTEGER, proposed_action VARCHAR, target_module VARCHAR, target_table VARCHAR, target_entity_id INTEGER, proposed_fields TEXT, field_confidence TEXT, evidence TEXT, questions TEXT, status VARCHAR, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, reviewed_at DATETIME, reviewer_id INTEGER)"))
        conn.execute(text("CREATE TABLE documents (id INTEGER PRIMARY KEY, filename VARCHAR, mime VARCHAR, storage_path VARCHAR, uploader_id INTEGER, folder_path_hint VARCHAR, file_hash VARCHAR, processing_status VARCHAR, document_type VARCHAR, classification_confidence FLOAT, extracted_text TEXT, extracted_fields TEXT, agent_summary TEXT, needs_review BOOLEAN, processing_error TEXT, customer_id INTEGER, project_id INTEGER, last_processed_at DATETIME, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"))
        conn.execute(text("CREATE TABLE document_versions (id INTEGER PRIMARY KEY, doc_id INTEGER, version INTEGER, extracted_text_path VARCHAR, router_json TEXT, extractor_json TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"))
        conn.execute(text("CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, actor_user_id INTEGER, action VARCHAR, entity_table VARCHAR, entity_id INTEGER, before TEXT, after TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"))

        conn.execute(text("INSERT INTO customers (id, name, aliases, status, tags) VALUES (1, 'Acme', '[]', 'active', '[]')"))
        conn.execute(text("INSERT INTO projects (id, project_code, name, customer_id, status, stage, currency) VALUES (1, 'PRJ-1', 'Project 1', 1, 'active', 'execution', 'USD')"))
        conn.execute(text("INSERT INTO documents (id, filename, mime, storage_path, uploader_id, folder_path_hint, file_hash, processing_status, needs_review, customer_id, project_id) VALUES (1, 'doc.pdf', 'application/pdf', '/tmp/doc.pdf', 1, '', 'abc', 'done', 0, 1, 1)"))

    return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def _client_with_roles(roles: list[str]) -> TestClient:
    app = FastAPI()
    app.include_router(documents.router, prefix='/api')
    app.include_router(projects.router, prefix='/api')
    app.include_router(dashboard.router, prefix='/api')
    app.include_router(tasks.router, prefix='/api')
    app.include_router(worklogs.router, prefix='/api')
    app.include_router(ncrs.router, prefix='/api')

    local_session = _make_session()

    def _override_db():
        db = local_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _User(1, roles)

    settings.run_tasks_inline = False
    documents.process_document.delay = lambda doc_id: SimpleNamespace(id=f'test-{doc_id}')

    return TestClient(app)


def test_viewer_is_read_only_and_engineer_can_write():
    viewer = _client_with_roles(['Viewer'])
    assert viewer.get('/api/documents').status_code == 200
    assert viewer.get('/api/projects').status_code == 200
    assert viewer.get('/api/dashboard/summary').status_code == 200

    assert viewer.post('/api/tasks', json={'project_code': 'PRJ-1', 'title': 'T1'}).status_code == 403
    assert viewer.post('/api/worklogs', json={'project_id': 1, 'project_code': 'PRJ-1', 'date': '2025-01-01', 'summary': 'log', 'user_id': 1}).status_code == 403
    assert viewer.post('/api/ncrs', json={'project_id': 1, 'project_code': 'PRJ-1', 'description': 'bad part'}).status_code == 403
    assert viewer.post('/api/documents/1/reprocess').status_code == 403

    engineer = _client_with_roles(['Engineer'])
    assert engineer.post('/api/tasks', json={'project_code': 'PRJ-1', 'title': 'T1'}).status_code == 200
    assert engineer.post('/api/worklogs', json={'project_id': 1, 'project_code': 'PRJ-1', 'date': '2025-01-01', 'summary': 'log', 'user_id': 1}).status_code == 200
    assert engineer.post('/api/ncrs', json={'project_id': 1, 'project_code': 'PRJ-1', 'description': 'bad part'}).status_code == 200
    assert engineer.post('/api/documents/1/reprocess').status_code == 202
