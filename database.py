from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Using SQLite for local development. 
# For production, swap this to a PostgreSQL URL (e.g., "postgresql://user:password@localhost/dbname")
SQLALCHEMY_DATABASE_URL = "sqlite:///./interview_agent.db"

# connect_args={"check_same_thread": False} is required only for SQLite in FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Dependency function to yield a database session for FastAPI routes.
    Ensures the connection is closed after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()