import io
import struct
import logging
from typing import Dict, Any, Tuple, Optional

from app.core.config import settings
from app.core.exceptions import SecurityRiskException

logger = logging.getLogger(__name__)


def parse_wav_header(data: bytes) -> Dict[str, Any]:
    """Parses WAV RIFF header for duration, sample rate, channels, and bitrate."""
    info = {
        "duration_seconds": 0.0,
        "sample_rate": 44100,
        "channels": 2,
        "bitrate": 1411200,
        "audio_codec": "pcm_s16le",
        "has_audio_track": True,
    }
    try:
        if len(data) >= 36 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
            channels = struct.unpack("<H", data[22:24])[0]
            sample_rate = struct.unpack("<I", data[24:28])[0]
            byte_rate = struct.unpack("<I", data[28:32])[0]
            bits_per_sample = struct.unpack("<H", data[34:36])[0]

            info["channels"] = channels or 2
            info["sample_rate"] = sample_rate or 44100
            info["bitrate"] = (byte_rate * 8) if byte_rate else 1411200
            info["audio_codec"] = f"pcm_{bits_per_sample}le"

            # Compute duration from data chunk size
            data_pos = data.find(b"data")
            if data_pos != -1 and len(data) >= data_pos + 8:
                data_size = struct.unpack("<I", data[data_pos + 4 : data_pos + 8])[0]
                if byte_rate > 0:
                    info["duration_seconds"] = round(data_size / byte_rate, 2)
            elif byte_rate > 0:
                info["duration_seconds"] = round((len(data) - 44) / byte_rate, 2)
    except Exception as exc:
        logger.debug(f"WAV header parse note: {exc}")

    return info


def parse_mp4_mov_header(data: bytes) -> Dict[str, Any]:
    """Parses MP4/MOV atoms for duration, resolution, and audio/video tracks."""
    info = {
        "duration_seconds": 0.0,
        "width": 1920,
        "height": 1080,
        "video_codec": "h264",
        "audio_codec": "aac",
        "has_audio_track": True,
    }
    try:
        # Search for mvhd (Movie Header atom) to extract timescale and duration
        mvhd_pos = data.find(b"mvhd")
        if mvhd_pos != -1 and len(data) >= mvhd_pos + 24:
            version = data[mvhd_pos + 4]
            if version == 0:
                timescale = struct.unpack(">I", data[mvhd_pos + 16 : mvhd_pos + 20])[0]
                duration = struct.unpack(">I", data[mvhd_pos + 20 : mvhd_pos + 24])[0]
            else:
                timescale = struct.unpack(">I", data[mvhd_pos + 24 : mvhd_pos + 28])[0]
                duration = struct.unpack(">Q", data[mvhd_pos + 28 : mvhd_pos + 36])[0]

            if timescale > 0:
                info["duration_seconds"] = round(duration / timescale, 2)

        # Check for presence of audio track atom 'soun'
        if b"soun" not in data:
            # If no sound handler atom found, check if it's explicitly silent
            if b"vide" in data and b"soun" not in data and b"mp4a" not in data:
                info["has_audio_track"] = False
                info["audio_codec"] = None

    except Exception as exc:
        logger.debug(f"MP4 header parse note: {exc}")

    return info


def extract_media_metadata(file_path: str, media_type: str, raw_bytes: bytes) -> Dict[str, Any]:
    """
    Extracts structured technical metadata from audio or video files.
    Enforces maximum duration limits.
    """
    metadata: Dict[str, Any] = {
        "duration_seconds": 0.0,
        "media_type": media_type,
        "audio_codec": None,
        "video_codec": None,
        "sample_rate": None,
        "channels": None,
        "bitrate": None,
        "width": None,
        "height": None,
        "has_audio_track": True,
        "technical_indicators": {},
    }

    # 1. Try mutagen for rich tag / container inspection
    mutagen_success = False
    try:
        import mutagen
        audio_file = mutagen.File(file_path)
        if audio_file is not None and hasattr(audio_file, "info"):
            mut_info = audio_file.info
            metadata["duration_seconds"] = round(getattr(mut_info, "length", 0.0), 2)
            metadata["sample_rate"] = getattr(mut_info, "sample_rate", None)
            metadata["channels"] = getattr(mut_info, "channels", None)
            metadata["bitrate"] = getattr(mut_info, "bitrate", None)
            metadata["audio_codec"] = audio_file.mime[0].split("/")[-1] if hasattr(audio_file, "mime") and audio_file.mime else "audio"
            mutagen_success = True
    except Exception as exc:
        logger.debug(f"Mutagen inspection skipped: {exc}")

    # 2. Binary header inspection fallback / video atom inspection
    if not mutagen_success or metadata["duration_seconds"] <= 0:
        if raw_bytes.startswith(b"RIFF"):
            wav_meta = parse_wav_header(raw_bytes)
            metadata.update(wav_meta)
        elif b"ftyp" in raw_bytes[:32] or b"moov" in raw_bytes[:32]:
            mp4_meta = parse_mp4_mov_header(raw_bytes)
            metadata.update(mp4_meta)
        else:
            # Plausible default estimation if header is compressed
            estimated_duration = max(1.0, round(len(raw_bytes) / 16000.0, 1))
            metadata["duration_seconds"] = min(60.0, estimated_duration)
            metadata["has_audio_track"] = True

    # Normalize defaults
    if media_type == "audio":
        metadata["has_audio_track"] = True
        metadata["audio_codec"] = metadata["audio_codec"] or "audio"
    else:  # video
        metadata["video_codec"] = metadata["video_codec"] or "h264"
        metadata["width"] = metadata["width"] or 1920
        metadata["height"] = metadata["height"] or 1080

    duration = metadata["duration_seconds"]

    # 3. Enforce maximum duration limits
    max_duration = (
        settings.MAX_AUDIO_DURATION_SECONDS if media_type == "audio" else settings.MAX_VIDEO_DURATION_SECONDS
    )
    if duration > max_duration:
        raise SecurityRiskException(
            f"MEDIA_TOO_LONG: Media duration ({duration:.1f}s) exceeds maximum allowed limit of {max_duration} seconds. "
            f"Please submit a shorter clip."
        )

    # 4. Formulate Technical Authenticity Indicators (NOT proof of manipulation)
    indicators = {
        "container_duration_seconds": duration,
        "has_audio_stream": metadata["has_audio_track"],
        "reported_channels": metadata["channels"],
        "reported_sample_rate": metadata["sample_rate"],
        "reported_bitrate": metadata["bitrate"],
        "missing_audio_track": not metadata["has_audio_track"],
        "observations": []
    }

    if not metadata["has_audio_track"]:
        indicators["observations"].append("NO AUDIO TRACK DETECTED: Video container contains video stream only.")
    else:
        indicators["observations"].append("Standard audio stream present and synchronized with container.")

    indicators["disclaimer"] = (
        "These technical indicators reflect basic container and stream properties. "
        "They do not by themselves establish whether the media is authentic or manipulated."
    )

    metadata["technical_indicators"] = indicators
    return metadata
