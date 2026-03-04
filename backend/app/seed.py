from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models
from app.auth import get_password_hash
from app.core.config import settings
from pathlib import Path

ROLE_NAMES = ["Admin", "Manager", "PM", "Sales", "Engineer", "Technician", "QC", "Viewer"]
ENGINEER_TYPES = ["plc_engineer", "software_engineer", "mechanical_engineer", "electrical_engineer", "hardware_engineer", "design_3d_engineer"]


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

        # Add engineering hierarchy sample data
        if db.query(models.EngineerProfile).count() == 0:
            # Create engineering users
            manager_user = db.query(models.User).filter_by(email="manager@aline.local").first()
            if not manager_user:
                manager_user = models.User(
                    email="manager@aline.local",
                    name="Project Manager",
                    password_hash=get_password_hash("Welcome123!"),
                    is_active=True,
                )
                manager_user.roles = [roles["Manager"]]
                db.add(manager_user)

            pm_user = db.query(models.User).filter_by(email="pm@aline.local").first()
            if not pm_user:
                pm_user = models.User(
                    email="pm@aline.local",
                    name="Project Manager John",
                    password_hash=get_password_hash("Welcome123!"),
                    is_active=True,
                )
                pm_user.roles = [roles["PM"]]
                db.add(pm_user)

            # Create engineer profiles
            engineers = []
            for i, eng_type in enumerate(ENGINEER_TYPES):
                for level in ["lead", "normal"]:
                    email = f"{eng_type.split('_')[0]}_{level}@aline.local"
                    user = db.query(models.User).filter_by(email=email).first()
                    if not user:
                        user = models.User(
                            email=email,
                            name=f"{eng_type.replace('_', ' ').title()} {level.title()}",
                            password_hash=get_password_hash("Welcome123!"),
                            is_active=True,
                        )
                        user.roles = [roles["Engineer"]]
                        db.add(user)
                        db.flush()  # Get the user ID

                    profile = models.EngineerProfile(
                        user_id=user.id,
                        engineer_type=eng_type,
                        level=level
                    )
                    db.add(profile)
                    engineers.append({"user": user, "profile": profile})

            db.commit()

            # Create project assignments
            project_alpha = db.query(models.Project).filter_by(project_code="ALPHA-001").first()
            project_beta = db.query(models.Project).filter_by(project_code="VECTOR-002").first()

            if project_alpha and project_beta:
                # Assign PM to projects
                pm_assignment = models.ProjectMember(
                    project_id=project_alpha.id,
                    user_id=pm_user.id,
                    project_role="project_manager",
                    assigned_by_user_id=admin.id
                )
                db.add(pm_assignment)

                # Assign lead engineers to project alpha
                for eng_type in ENGINEER_TYPES[:3]:  # Use first 3 types for alpha project
                    lead_user = db.query(models.User).join(models.EngineerProfile).filter(
                        models.EngineerProfile.engineer_type == eng_type,
                        models.EngineerProfile.level == "lead"
                    ).first()
                    
                    if lead_user:
                        lead_assignment = models.ProjectMember(
                            project_id=project_alpha.id,
                            user_id=lead_user.id,
                            project_role="lead_engineer",
                            engineer_type=eng_type,
                            report_to_user_id=pm_user.id,
                            assigned_by_user_id=pm_user.id
                        )
                        db.add(lead_assignment)

                # Assign normal engineers to project alpha under their respective leads
                for eng_type in ENGINEER_TYPES[:3]:
                    lead_user = db.query(models.User).join(models.EngineerProfile).filter(
                        models.EngineerProfile.engineer_type == eng_type,
                        models.EngineerProfile.level == "lead"
                    ).first()
                    
                    normal_user = db.query(models.User).join(models.EngineerProfile).filter(
                        models.EngineerProfile.engineer_type == eng_type,
                        models.EngineerProfile.level == "normal"
                    ).first()
                    
                    if lead_user and normal_user:
                        engineer_assignment = models.ProjectMember(
                            project_id=project_alpha.id,
                            user_id=normal_user.id,
                            project_role="engineer",
                            engineer_type=eng_type,
                            report_to_user_id=lead_user.id,
                            assigned_by_user_id=lead_user.id
                        )
                        db.add(engineer_assignment)

                db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    seed()
