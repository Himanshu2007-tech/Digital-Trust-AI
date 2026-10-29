from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime


class DatabaseHealth(BaseModel):
    connected: bool
    type: str
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check payload for GET /api/health."""
    status: str = Field(default="ok", description="Overall health status")
    service: str = Field(default="TruthLens AI", description="Service identifier")
    version: str = Field(default="1.0.0", description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Server UTC timestamp")
    environment: str = Field(default="development", description="Current environment")
    database: DatabaseHealth = Field(description="Database connectivity status")
    features: Dict[str, str] = Field(
        default={
            "verification_engine": "planned_part_2",
            "multimedia_pipeline": "planned_part_3",
            "web_search": "planned_part_2",
            "source_credibility": "planned_part_2"
        },
        description="Feature activation flags"
    )
