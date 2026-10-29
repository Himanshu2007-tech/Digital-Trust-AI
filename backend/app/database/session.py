from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# Configure engine based on dialect (e.g. SQLite requires check_same_thread=False)
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> dict:
    """
    Checks whether the database connection is healthy.
    Returns status dict with connectivity information.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"connected": True, "type": engine.dialect.name}
    except Exception as exc:
        return {"connected": False, "type": engine.dialect.name, "error": str(exc)}
