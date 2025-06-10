from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os
import time
from dotenv import load_dotenv

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

if ENVIRONMENT == "docker" or ENVIRONMENT == "production":
    DATABASE_URL = os.getenv(
        "DATABASE_URL", "postgresql://admin:alphabet@localhost:5432/grunland_db"
    )
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,
        echo=True,  # Set to True for SQL debugging
        connect_args={"options": "-c timezone=utc"},
    )
    print(f"Using PostgreSQL: {DATABASE_URL.split('@')[1]}")
else:
    SQLITE_DATABASE_URL = "sqlite:///./grunland.db"

    engine = create_engine(
        SQLITE_DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,
        },
        poolclass=StaticPool,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )
    print("Using SQLite for local development")

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)

from app.models.base import Base

# Base = declarative_base()


def wait_for_database(max_retries=30, delay=2):
    """Wait for database to be available"""
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            print(f"Database connection successful on attempt {attempt + 1}")
            return True
        except Exception as e:
            print(
                f"Database connection attempt {attempt + 1}/{max_retries} failed: {e}"
            )
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("Failed to connect to database after all attempts")
                raise
    return False


def create_tables():
    """Create all tables defined in models"""
    print("Creating database tables...")
    print(f"Tables to create: {list(Base.metadata.tables.keys())}")

    Base.metadata.create_all(bind=engine)

    # Verify tables were created
    inspector = inspect(engine)
    actual_tables = inspector.get_table_names()
    print(f"Tables created in database: {actual_tables}")

    if not actual_tables:
        raise Exception("No tables were created!")

    print("Table creation completed successfully")


def drop_tables():
    Base.metadata.drop_all(bind=engine)

def create_root_admin(db: Session):
    from app.crud.user import get_user_by_email, create_user_with_hashed_password
    from app.crud.roles import get_role_by_name, assign_role_to_user
    from app.schemas.user import UserCreate

    admin_email = os.getenv("ROOT_ADMIN_EMAIL")
    admin_password = os.getenv("ROOT_ADMIN_PASSWORD")
    admin_company = os.getenv("ROOT_ADMIN_COMPANY")

    if not all([admin_email, admin_password, admin_company]):
        print("ROOT_ADMIN_* environment variables are not fully set. Skipping root admin creation.")
        return

    existing_user = get_user_by_email(db, admin_email)
    if existing_user:
        print("Root admin user already exists.")
        return

    admin_role = get_role_by_name(db, "admin")
    if not admin_role:
        raise Exception("Admin role must be created in the table before creating roo user")

    root_user_create = UserCreate(
        email = admin_email,
        password = admin_password,
        company_name = admin_company,
        is_active=True
    )

    root_user = create_user_with_hashed_password(
        db,
        root_user_create
    )

    assign_role_to_user(db, root_user, "admin")
    print(f"Root admin user: '{root_user.email} created")

def init_database():
    """Initialize database with proper error handling and retries"""
    print("Starting database initialization...")

    try:
        # Wait for database to be available
        wait_for_database()

        # Import models to register them with Base
        print("Importing models...")
        from app.models.user import Role, User

        print("Models imported successfully!")
        print(f"Registered models: {list(Base.metadata.tables.keys())}")

        # Create tables
        create_tables()

        # Initialize default data
        print("Initializing default roles...")
        db = SessionLocal()
        try:
            from app.crud.roles import initialize_default_roles

            initialize_default_roles(db)
            print("Default roles initialized successfully")
            create_root_admin(db)
        finally:
            db.close()

        print("Database initialization completed successfully!")

    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection():
    """Check if database is accessible"""
    try:
        db = SessionLocal()
        # Simple query to test connection
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
