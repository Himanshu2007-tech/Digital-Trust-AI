from fastapi import APIRouter, status
from app.schemas.health import HealthResponse, DatabaseHealth
from app.database.session import check_db_connection
from app.core.config import settings

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health & Connectivity Check",
    description="Returns backend service identity, version, environment, and database connection status."
)
async def get_health():
    db_status = check_db_connection()
    return HealthResponse(
        status="ok",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database=DatabaseHealth(
            connected=db_status["connected"],
            type=db_status["type"],
            error=db_status.get("error")
        )
    )
