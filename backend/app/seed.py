from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models
from app.auth import get_password_hash
from app.core.config import settings
from pathlib import Path

ROLE_NAMES = ["Admin", "Manager", "PM", "Sales", "Engineer", "Technician", "QC", "Viewer"]


def seed():
    db: Session = SessionLocal()
    try:
        roles = {}
        for name in ROLE_NAMES:
            role = db.query(models.Role).filter_by(name=name).first()
            if not role:
                role = models.Role(name=name)
                db.add(role)
                db.flush()
            roles[name] = role

        admin = db.query(models.User).filter_by(email="admin@aline.local").first()
        if not admin:
            admin = models.User(
                email="admin@aline.local",
                name="Admin",
                password_hash=get_password_hash("Admin123!"),
                is_active=True,
            )
            admin.roles = [roles["Admin"]]
            db.add(admin)
        demo_user = db.query(models.User).filter_by(email="mirshaeek@aline.local").first()
        if not demo_user:
            demo_user = models.User(
                email="mirshaeek@aline.local",
                name="MirShaeek",
                password_hash=get_password_hash("Welcome123!"),
                is_active=True,
            )
            demo_user.roles = [roles["Sales"]]
            db.add(demo_user)
        db.commit()

        if db.query(models.Customer).count() == 0:
            customers = [
                models.Customer(name="Atlas Automation", status="active", industry="Manufacturing", tags=["priority"]),
                models.Customer(name="Vector Controls", status="lead", industry="Energy"),
                models.Customer(name="Summit Robotics", status="active", industry="Robotics"),
                models.Customer(name="Pioneer Metals", status="on_hold", industry="Metals"),
                models.Customer(name="Orchid Labs", status="inactive", industry="Biotech"),
            ]
            db.add_all(customers)
            db.flush()

            contacts = [
                models.CustomerContact(customer_id=customers[0].id, name="Lina Chen", email="lina@atlas.test", role_title="Operations"),
                models.CustomerContact(customer_id=customers[0].id, name="Marco Diaz", email="marco@atlas.test", role_title="Buyer"),
                models.CustomerContact(customer_id=customers[1].id, name="Sam Lee", email="sam@vector.test", role_title="Engineering"),
                models.CustomerContact(customer_id=customers[2].id, name="Priya Rao", email="priya@summit.test", role_title="Director"),
                models.CustomerContact(customer_id=customers[3].id, name="Jon Blake", email="jon@pioneer.test", role_title="Quality"),
            ]
            db.add_all(contacts)

            project_alpha = models.Project(
                project_code="ALPHA-001",
                name="Atlas Retrofit Line 3",
                customer_id=customers[0].id,
                status="active",
            )
            project_beta = models.Project(
                project_code="VECTOR-002",
                name="Vector Controls Upgrade",
                customer_id=customers[1].id,
                status="planning",
            )
            db.add_all([project_alpha, project_beta])
            db.flush()

            db.add_all(
                [
                    models.Task(project_id=project_alpha.id, title="Review electrical drawings", status="open", priority="high"),
                    models.Task(project_id=project_alpha.id, title="PLC IO mapping", status="blocked", priority="med"),
                    models.Task(project_id=project_beta.id, title="Site survey scheduling", status="in_progress", priority="low"),
                ]
            )
            db.add_all(
                [
                    models.Milestone(project_id=project_alpha.id, name="Design freeze", status="in_progress"),
                    models.Milestone(project_id=project_beta.id, name="Kickoff", status="planned"),
                ]
            )

            db.add_all(
                [
                    models.Notification(message="Proposal pending approval for Atlas.", role="Sales", type="proposal_pending"),
                    models.Notification(message="Document needs review for Vector Controls.", role="Admin", type="needs_review"),
                ]
            )

            storage_root = Path(settings.file_storage_root)
            storage_root.mkdir(parents=True, exist_ok=True)
            sample_path = storage_root / "sample_doc.txt"
            if not sample_path.exists():
                sample_path.write_text("Sample document content for seeding.", encoding="utf-8")

            documents = [
                models.Document(
                    filename="atlas_contract.pdf",
                    mime="application/pdf",
                    storage_path=str(sample_path),
                    uploader_id=admin.id,
                    file_hash="seed1",
                    processing_status="done",
                    document_type="contract",
                    classification_confidence=0.91,
                    agent_summary="Service contract for Atlas.",
                    customer_id=customers[0].id,
                ),
                models.Document(
                    filename="vector_spec.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    storage_path=str(sample_path),
                    uploader_id=admin.id,
                    file_hash="seed2",
                    processing_status="failed",
                    processing_error="Parser timeout",
                    customer_id=customers[1].id,
                ),
            ]
            db.add_all(documents)

            db.add(
                models.AuditEvent(
                    actor_user_id=admin.id,
                    entity_table="customers",
                    entity_id=customers[0].id,
                    action="created",
                    payload_json={"source": "seed"},
                )
            )

            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
