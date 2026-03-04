from app.database import engine, Base
from app.models import *
from app.seed import seed

def init_database():
    """Initialize the database with tables and seed data."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")
    
    print("Seeding initial data...")
    seed()
    print("Initial data seeded successfully.")

if __name__ == "__main__":
    init_database()