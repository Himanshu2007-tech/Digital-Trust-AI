import io
import os
import uuid
import hashlib
import logging
from typing import Tuple, Dict, Any, Optional

from app.core.config import settings
from app.core.exceptions import SecurityRiskException
from app.utils.security_helpers import sanitize_filename

logger = logging.getLogger(__name__)

# File signatures / magic bytes for audio and video formats
MEDIA_MAGIC_SIGNATURES = [
    # MP3
    (b"ID3", "audio/mpeg", "mp3", "audio"),
    (b"\xFF\xFB", "audio/mpeg", "mp3", "audio"),
    (b"\xFF\xF3", "audio/mpeg", "mp3", "audio"),
    (b"\xFF\xF2", "audio/mpeg", "mp3", "audio"),
    # OGG
    (b"OggS", "audio/ogg", "ogg", "audio"),
    # WEBM / Matroska (MKV)
    (b"\x1a\x45\xdf\xa3", "video/webm", "webm", "video"),
]


def detect_media_container(data: bytes, original_filename: str = "") -> Optional[Tuple[str, str, str]]:
    """
    Detects audio/video MIME type, canonical extension, and media type ('audio' | 'video')
    using magic byte headers.
    Returns (mime_type, extension, media_type) or None if unrecognized.
    """
    if len(data) < 12:
        return None

    # 1. Check RIFF header (WAV)
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WAVE":
        return ("audio/wav", "wav", "audio")

    # 2. Check MP4 / M4A / MOV (ISO Base Media File Format: ftyp or moov atom)
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in [b"M4A ", b"M4B ", b"M4P "]:
            return ("audio/x-m4a", "m4a", "audio")
        elif brand in [b"qt  "]:
            return ("video/quicktime", "mov", "video")
        else:
            return ("video/mp4", "mp4", "video")

    # Check moov atom in first 32 bytes
    if b"moov" in data[:32] or b"mdat" in data[:32]:
        ext_lower = original_filename.lower().split(".")[-1] if "." in original_filename else "mp4"
        if ext_lower in ["m4a", "aac"]:
            return ("audio/x-m4a", "m4a", "audio")
        return ("video/mp4", "mp4", "video")

    # 3. Check Matroska (MKV) vs WEBM via filename hint if EBML header matched
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        ext_lower = original_filename.lower().split(".")[-1] if "." in original_filename else "webm"
        if ext_lower in ["mkv", "matroska"]:
            return ("video/x-matroska", "mkv", "video")
        return ("video/webm", "webm", "video")

    # 4. Check AAC ADTS syncword (0xFFF)
    if len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xF6) == 0xF0:
        return ("audio/aac", "aac", "audio")

    # 5. Check direct byte prefixes
    for prefix, mime, ext, mtype in MEDIA_MAGIC_SIGNATURES:
        if data.startswith(prefix):
            return (mime, ext, mtype)

    # 6. Fallback detection for raw MP3 files without ID3 tags
    if len(data) >= 4 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return ("audio/mpeg", "mp3", "audio")

    return None


def validate_media_security(data: bytes, original_filename: str) -> Tuple[str, str, str]:
    """
    Validates uploaded audio or video file:
    - Size limits (MAX_AUDIO_SIZE_BYTES / MAX_VIDEO_SIZE_BYTES)
    - Magic byte signatures (prevents disguised executables / scripts)
    - MIME whitelist

    Returns:
        (mime_type, extension, media_type)
    """
    file_size = len(data)
    if file_size == 0:
        raise ValueError("Uploaded media file is empty (INVALID_FILE).")

    # Detect container and media type
    detected = detect_media_container(data, original_filename)
    if not detected:
        raise SecurityRiskException(
            "INVALID_FILE: Media failed container header verification. "
            "The file header does not match any supported audio or video format (MP3, WAV, M4A, OGG, MP4, MOV, WEBM, MKV)."
        )

    mime_type, ext, media_type = detected

    # Validate against allowed MIME lists
    if media_type == "audio":
        if mime_type not in settings.ALLOWED_AUDIO_MIME_TYPES:
            raise SecurityRiskException(f"UNSUPPORTED_FORMAT: Audio MIME type '{mime_type}' is not permitted.")
        if file_size > settings.MAX_AUDIO_SIZE_BYTES:
            max_mb = settings.MAX_AUDIO_SIZE_BYTES / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            raise SecurityRiskException(
                f"FILE_TOO_LARGE: Audio file ({actual_mb:.1f} MB) exceeds maximum allowed limit of {max_mb:.0f} MB."
            )
    else:  # video
        if mime_type not in settings.ALLOWED_VIDEO_MIME_TYPES:
            raise SecurityRiskException(f"UNSUPPORTED_FORMAT: Video MIME type '{mime_type}' is not permitted.")
        if file_size > settings.MAX_VIDEO_SIZE_BYTES:
            max_mb = settings.MAX_VIDEO_SIZE_BYTES / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            raise SecurityRiskException(
                f"FILE_TOO_LARGE: Video file ({actual_mb:.1f} MB) exceeds maximum allowed limit of {max_mb:.0f} MB."
            )

    return (mime_type, ext, media_type)


def save_media_file(data: bytes, original_filename: str, mime_type: str, ext: str) -> Dict[str, Any]:
    """
    Saves validated media bytes under a collision-resistant UUID filename in local storage.
    Computes cryptographic SHA-256 fingerprint.
    """
    sha256 = hashlib.sha256(data).hexdigest()
    stored_filename = f"{uuid.uuid4().hex}.{ext}"

    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    full_path = os.path.join(settings.STORAGE_PATH, stored_filename)

    with open(full_path, "wb") as f:
        f.write(data)

    clean_original_filename = sanitize_filename(original_filename, default_name=f"media.{ext}")

    return {
        "original_filename": clean_original_filename,
        "stored_filename": stored_filename,
        "file_path": full_path,
        "file_size_bytes": len(data),
        "mime_type": mime_type,
        "file_hash_sha256": sha256,
        "storage_provider": settings.STORAGE_PROVIDER,
    }
