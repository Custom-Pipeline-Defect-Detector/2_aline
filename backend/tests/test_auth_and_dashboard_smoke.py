from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.deps import get_db
from app.routers import auth, dashboard
from app.auth import get_password_hash


def _make_session(create_dashboard_tables: bool = True):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR UNIQUE NOT NULL, name VARCHAR NOT NULL, password_hash VARCHAR NOT NULL, is_active BOOLEAN NOT NULL, created_at DATETIME)"))
        conn.execute(text("CREATE TABLE roles (id INTEGER PRIMARY KEY, name VARCHAR UNIQUE NOT NULL)"))
        conn.execute(text("CREATE TABLE user_roles (user_id INTEGER NOT NULL, role_id INTEGER NOT NULL)"))
        if create_dashboard_tables:
            conn.execute(text("CREATE TABLE projects (id INTEGER PRIMARY KEY, project_code VARCHAR, name VARCHAR, customer_id INTEGER, status VARCHAR, stage VARCHAR, value_amount FLOAT, currency VARCHAR, start_date DATE, due_date DATE, created_at DATETIME)"))
            conn.execute(text("CREATE TABLE tasks (id INTEGER PRIMARY KEY, project_id INTEGER, title VARCHAR, description TEXT, owner_id INTEGER, due_date DATE, status VARCHAR, priority VARCHAR, type VARCHAR, completed_at DATETIME, source_doc_id INTEGER, created_at DATETIME)"))
            conn.execute(text("CREATE TABLE issues (id INTEGER PRIMARY KEY, project_id INTEGER, severity VARCHAR, description TEXT, owner_id INTEGER, status VARCHAR, source_doc_id INTEGER, created_at DATETIME)"))
            conn.execute(text("CREATE TABLE ncrs (id INTEGER PRIMARY KEY, project_id INTEGER, description TEXT, root_cause TEXT, corrective_action TEXT, status VARCHAR, source_doc_id INTEGER, opened_date DATE, closed_date DATE, created_at DATETIME)"))
            conn.execute(text("CREATE TABLE proposals (id INTEGER PRIMARY KEY, doc_version_id INTEGER, proposed_action VARCHAR, target_module VARCHAR, target_table VARCHAR, target_entity_id INTEGER, proposed_fields TEXT, field_confidence TEXT, evidence TEXT, questions TEXT, status VARCHAR, created_at DATETIME, reviewed_at DATETIME, reviewer_id INTEGER)"))

        conn.execute(text("INSERT INTO roles (id, name) VALUES (1, 'Admin')"))
        conn.execute(text("INSERT INTO roles (id, name) VALUES (2, 'Viewer')"))
        conn.execute(text("INSERT INTO roles (id, name) VALUES (3, 'Sales')"))
        conn.execute(text("INSERT INTO users (id, email, name, password_hash, is_active) VALUES (1, 'admin@example.com', 'Admin', :hash, 1)"), {"hash": get_password_hash("Admin123!")})
        conn.execute(text("INSERT INTO user_roles (user_id, role_id) VALUES (1, 1)"))

    return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def _make_client(local_session):
    app = FastAPI()
    app.include_router(auth.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")

    def _override_db():
        db = local_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    return TestClient(app)


def test_login_then_me_succeeds():
    client = _make_client(_make_session())
    res = client.post("/api/auth/login", data={"username": "admin@example.com", "password": "Admin123!"})
    assert res.status_code == 200
    token = res.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "admin@example.com"


def test_dashboard_summary_200_when_db_ok():
    client = _make_client(_make_session(create_dashboard_tables=True))
    res = client.post("/api/auth/login", data={"username": "admin@example.com", "password": "Admin123!"})
    token = res.json()["access_token"]

    summary = client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
    assert summary.status_code == 200
    assert "open_tasks" in summary.json()


def test_dashboard_summary_503_when_db_unavailable():
    client = _make_client(_make_session(create_dashboard_tables=False))
    res = client.post("/api/auth/login", data={"username": "admin@example.com", "password": "Admin123!"})
    token = res.json()["access_token"]

    summary = client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
    assert summary.status_code == 503
    assert "Database unavailable" in summary.text


def test_register_with_sales_role_assigns_sales_role():
    client = _make_client(_make_session())

    res = client.post(
        "/api/auth/register",
        json={
            "email": "sales.user@example.com",
            "name": "Sales User",
            "password": "SalesPass123!",
            "role_name": "Sales",
        },
    )
    assert res.status_code == 200
    role_names = [role["name"] for role in res.json()["roles"]]
    assert "Sales" in role_names


def test_register_with_admin_role_is_rejected():
    client = _make_client(_make_session())

    res = client.post(
        "/api/auth/register",
        json={
            "email": "bad.admin@example.com",
            "name": "Bad Admin",
            "password": "AdminPass123!",
            "role_name": "Admin",
        },
    )
    assert res.status_code == 400
    assert "Invalid role" in res.text
