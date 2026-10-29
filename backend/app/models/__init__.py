"""
TruthLens AI Database Models
All 10 core entities representing the verification pipeline data architecture.
"""

from app.database.base import Base
from app.models.user import User
from app.models.media_file import MediaFile
from app.models.verification_request import VerificationRequest
from app.models.claim import Claim
from app.models.source import Source
from app.models.evidence import Evidence
from app.models.source_comparison import SourceComparison
from app.models.verification_result import VerificationResult
from app.models.search_query import SearchQuery
from app.models.report import Report
from app.models.article import Article
from app.models.image_verification import ImageVerification
from app.models.media_verification import MediaVerification
from app.models.transcript_segment import TranscriptSegment
from app.models.video_frame import VideoFrame
from app.models.claim_occurrence import ClaimOccurrence
from app.models.verification_event import VerificationEvent

__all__ = [
    "Base",
    "User",
    "MediaFile",
    "VerificationRequest",
    "Claim",
    "Source",
    "Evidence",
    "SourceComparison",
    "VerificationResult",
    "SearchQuery",
    "Report",
    "Article",
    "ImageVerification",
    "MediaVerification",
    "TranscriptSegment",
    "VideoFrame",
    "ClaimOccurrence",
    "VerificationEvent",
]
