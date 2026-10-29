from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
import os
from pathlib import Path


class Settings(BaseSettings):
    """
    TruthLens AI Application Settings.
    Loaded from environment variables and .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Project metadata
    PROJECT_NAME: str = "TruthLens AI"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "AI-Powered Fake News & Multimedia Verification System (Part 1 Foundation)"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api"

    # Server Host & Port
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database Configuration
    # Uses SQLite dev fallback if PostgreSQL is not active
    DATABASE_URL: str = "sqlite:///./truthlens_dev.db"

    # Security & Tokens
    SECRET_KEY: str = "dev-secret-key-truthlens-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            try:
                return json.loads(v)
            except Exception:
                return [v]
        elif isinstance(v, list):
            return v
        return []

    # Storage settings for multimedia files
    STORAGE_PROVIDER: str = "local"
    STORAGE_PATH: str = "./storage/media"
    STORAGE_BUCKET: str = "truthlens-media-dev"
    MAX_UPLOAD_SIZE_BYTES: int = 52428800  # 50 MB

    # Allowed mime types for security
    ALLOWED_IMAGE_MIME_TYPES: List[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif"
    ]
    ALLOWED_AUDIO_MIME_TYPES: List[str] = [
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/ogg",
        "audio/x-m4a",
        "audio/m4a",
        "audio/aac",
        "audio/mp4"
    ]
    ALLOWED_VIDEO_MIME_TYPES: List[str] = [
        "video/mp4",
        "video/webm",
        "video/quicktime",
        "video/x-matroska",
        "video/mkv"
    ]

    # External APIs
    LLM_API_KEY: str = ""
    LLM_PROVIDER: str = "openai"  # openai, gemini, anthropic, ollama, or none
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: int = 15

    # Search APIs
    SEARCH_PROVIDER: str = "duckduckgo"  # duckduckgo, tavily, google, serpapi, brave, mock, none
    SEARCH_API_KEY: str = ""
    SEARCH_ENGINE_ID: str = ""  # For Google Custom Search
    SEARCH_MAX_RESULTS: int = 5
    SEARCH_TIMEOUT_SECONDS: int = 15

    # Configurable Reliable News & Fact-Checking Sources
    RELIABLE_SOURCE_DOMAINS: List[str] = [
        "reuters.com",
        "apnews.com",
        "bbc.com",
        "bbc.co.uk",
        "thehindu.com",
        "timesofindia.indiatimes.com",
        "indianexpress.com",
        "ptinews.com",
        "pib.gov.in",
        "snopes.com",
        "factcheck.org",
        "politifact.com",
        "altnews.in",
        "boomlive.in",
        "who.int",
        "isro.gov.in",
        "rbi.org.in",
        "bloomberg.com",
        "afp.com"
    ]

    # News URL / Article Fetching (Part 7)
    MAX_ARTICLE_RESPONSE_MB: int = 5
    ARTICLE_REQUEST_TIMEOUT_SECONDS: int = 15
    ARTICLE_CONNECT_TIMEOUT_SECONDS: int = 5
    MAX_ARTICLE_REDIRECTS: int = 5
    ALLOWED_ARTICLE_CONTENT_TYPES: List[str] = [
        "text/html",
        "application/xhtml+xml",
        "text/plain"
    ]

    # Image & OCR Verification (Part 8)
    MAX_IMAGE_FILE_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB
    MAX_IMAGE_PIXELS: int = 25_000_000  # 25 MP (decompression bomb protection)
    MAX_IMAGE_DIMENSION: int = 6000  # Max pixel dimension on any axis
    TESSERACT_CMD: str = ""  # Custom path to tesseract binary if not on PATH
    OCR_CONFIDENCE_THRESHOLD: float = 30.0  # Minimum word confidence

    # Audio & Video Claim Verification (Part 9)
    MAX_AUDIO_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    MAX_VIDEO_SIZE_BYTES: int = 200 * 1024 * 1024  # 200 MB
    MAX_AUDIO_DURATION_SECONDS: int = 600  # 10 minutes
    MAX_VIDEO_DURATION_SECONDS: int = 600  # 10 minutes
    TRANSCRIPTION_PROVIDER: str = "auto"
    TRANSCRIPTION_CONFIDENCE_THRESHOLD: float = 0.40

    # Advanced Video & Multimedia Analysis Engine (Part 10)
    FRAME_INTERVAL_SECONDS: float = 5.0
    MAX_ANALYZED_FRAMES: int = 15
    MAX_FRAME_ANALYSIS_TIME_SECONDS: float = 30.0
    SCENE_CHANGE_THRESHOLD: float = 0.35
    MAX_ANALYSIS_FRAME_WIDTH: int = 1280
    KEYFRAME_STORAGE_PATH: str = "./storage/media/frames"

    # Report Generation (Part 12)
    REPORTS_STORAGE_PATH: str = "./storage/reports"


# Instantiate cached settings
settings = Settings()

# Ensure local storage directory exists
Path(settings.STORAGE_PATH).mkdir(parents=True, exist_ok=True)
Path(settings.KEYFRAME_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
Path(settings.REPORTS_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
Path("./storage/temp").mkdir(parents=True, exist_ok=True)

