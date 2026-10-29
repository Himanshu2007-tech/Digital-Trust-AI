import io
import os
import uuid
import hashlib
import logging
from typing import Tuple, Dict, Any, Optional
from PIL import Image, ExifTags, ImageOps

from app.core.config import settings
from app.core.exceptions import SecurityRiskException
from app.utils.security_helpers import sanitize_filename

logger = logging.getLogger(__name__)

# Enforce Decompression Bomb Protection in Pillow globally
Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_PIXELS

# Known magic byte signatures
MAGIC_SIGNATURES = {
    b"\xFF\xD8\xFF": ("image/jpeg", "jpg"),
    b"\x89PNG\r\n\x1a\n": ("image/png", "png"),
    b"GIF87a": ("image/gif", "gif"),
    b"GIF89a": ("image/gif", "gif"),
}

# EXIF tag names to completely strip for user privacy protection
SENSITIVE_EXIF_TAGS = {
    "GPSInfo",
    "GPS",
    "Latitude",
    "Longitude",
    "CameraOwnerName",
    "BodySerialNumber",
    "LensSerialNumber",
    "InternalSerialNumber",
    "OwnerName",
    "SerialNumber",
}


def detect_image_magic_bytes(data: bytes) -> Optional[Tuple[str, str]]:
    """
    Validates binary header magic bytes.
    Returns (mime_type, extension) if matched, otherwise None.
    """
    if len(data) < 12:
        return None

    # Check WEBP signature: RIFF....WEBP
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ("image/webp", "webp")

    # Check direct byte prefixes
    for signature, (mime, ext) in MAGIC_SIGNATURES.items():
        if data.startswith(signature):
            return (mime, ext)

    return None


def validate_image_security(data: bytes, filename: str) -> Tuple[str, str, int, int]:
    """
    Performs comprehensive security and integrity checks on uploaded image bytes:
    1. File size limit
    2. Magic byte validation (prevents disguised executable / script uploads)
    3. Decompression bomb and extreme dimension defense
    4. Image structure validation

    Returns:
        (mime_type, extension, width, height)
    """
    # 1. Check file size
    file_size = len(data)
    if file_size == 0:
        raise ValueError("Uploaded image file is empty.")
    if file_size > settings.MAX_IMAGE_FILE_SIZE_BYTES:
        raise SecurityRiskException(
            f"Image file size ({file_size / (1024*1024):.2f} MB) exceeds maximum allowed "
            f"limit of {settings.MAX_IMAGE_FILE_SIZE_BYTES / (1024*1024):.1f} MB."
        )

    # 2. Magic byte check
    detected = detect_image_magic_bytes(data)
    if not detected:
        raise SecurityRiskException(
            "Image failed magic byte validation. The file header does not match any valid "
            "JPEG, PNG, WEBP, or GIF image format."
        )

    mime_type, ext = detected
    if mime_type not in settings.ALLOWED_IMAGE_MIME_TYPES:
        raise SecurityRiskException(f"Image MIME type '{mime_type}' is not supported.")

    # 3. Pillow integrity & dimension verification
    try:
        # First pass: verify structural integrity
        with Image.open(io.BytesIO(data)) as img_verify:
            img_verify.verify()

        # Second pass: read dimensions and format
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
            total_pixels = width * height

            if total_pixels > settings.MAX_IMAGE_PIXELS:
                raise SecurityRiskException(
                    f"Image total pixels ({total_pixels:,}) exceeds decompression bomb threshold "
                    f"({settings.MAX_IMAGE_PIXELS:,} pixels)."
                )

            if width > settings.MAX_IMAGE_DIMENSION or height > settings.MAX_IMAGE_DIMENSION:
                raise SecurityRiskException(
                    f"Image dimension ({width}x{height}) exceeds maximum allowed dimension "
                    f"({settings.MAX_IMAGE_DIMENSION}px)."
                )

            return (mime_type, ext, width, height)

    except SecurityRiskException:
        raise
    except Exception as exc:
        logger.warning(f"Image integrity validation failed for {filename}: {exc}")
        raise ValueError(f"Corrupt or unreadable image file: {str(exc)}")


def extract_and_sanitize_exif(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extracts benign technical camera / image metadata while strictly stripping
    GPS coordinates, device serial numbers, and personal identifiers to preserve privacy.
    """
    sanitized: Dict[str, Any] = {
        "has_exif": False,
        "gps_removed": False,
        "technical_tags": {}
    }

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            exif = img.getexif()
            if not exif:
                return sanitized

            sanitized["has_exif"] = True
            for tag_id, value in exif.items():
                tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                
                # Check for sensitive GPS or serial tags
                if any(sensitive in tag_name for sensitive in SENSITIVE_EXIF_TAGS):
                    sanitized["gps_removed"] = True
                    continue

                # Only include benign tags
                if tag_name in ["Make", "Model", "DateTime", "DateTimeOriginal", "Software", "Orientation", "XResolution", "YResolution"]:
                    # Sanitize value to string
                    sanitized["technical_tags"][tag_name] = str(value).strip()

    except Exception as exc:
        logger.debug(f"EXIF extraction error (non-fatal): {exc}")

    return sanitized


def save_image_file(data: bytes, original_filename: str, mime_type: str, ext: str) -> Dict[str, Any]:
    """
    Saves validated image data to disk under a collision-resistant UUID filename.
    Computes SHA-256 fingerprint.
    """
    sha256 = hashlib.sha256(data).hexdigest()
    stored_filename = f"{uuid.uuid4().hex}.{ext}"
    
    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    full_path = os.path.join(settings.STORAGE_PATH, stored_filename)

    with open(full_path, "wb") as f:
        f.write(data)

    clean_original_filename = sanitize_filename(original_filename, default_name=f"image.{ext}")

    return {
        "original_filename": clean_original_filename,
        "stored_filename": stored_filename,
        "file_path": full_path,
        "file_size_bytes": len(data),
        "mime_type": mime_type,
        "file_hash_sha256": sha256,
        "storage_provider": settings.STORAGE_PROVIDER
    }
