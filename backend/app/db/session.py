from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

from app.models.user import User
from app.models.workspace import (
    Workspace,
    WorkspaceMember,
    Project,
    Task,
    AuditLog,
)

__all__ = ["User", "Workspace", "WorkspaceMember", "Project", "Task", "AuditLog"]




SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()