from app.database.session import engine
from app.models import Base
import logging

logger = logging.getLogger(__name__)


def init_db() -> None:
    """
    Initialize database schema.
    Creates all defined tables if they do not exist.
    """
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
