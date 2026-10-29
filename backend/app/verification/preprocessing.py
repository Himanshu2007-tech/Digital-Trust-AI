import re
import unicodedata
from typing import List, Tuple
from app.core.exceptions import ValidationException

# Honorific titles that precede names and should NEVER terminate a sentence
HONORIFIC_TITLES = [
    r"mr\.", r"mrs\.", r"ms\.", r"dr\.", r"prof\.", r"govt\.", r"rep\.", r"sen\.",
    r"rev\.", r"gen\.", r"col\.", r"capt\.", r"lt\.", r"st\."
]

# Common abbreviations
ABBREVIATIONS = [
    r"u\.s\.", r"u\.k\.", r"u\.n\.", r"e\.u\.", r"r\.b\.i\.", r"i\.m\.f\.",
    r"jan\.", r"feb\.", r"mar\.", r"apr\.", r"jun\.", r"jul\.", r"aug\.", r"sep\.", r"sept\.", r"oct\.", r"nov\.", r"dec\.",
    r"vs\.", r"etc\.", r"inc\.", r"corp\.", r"ltd\.", r"co\.", r"no\.", r"approx\.",
    r"rs\.", r"a\.m\.", r"p\.m\."
]

TITLE_PATTERN = re.compile(r"\b(" + "|".join(HONORIFIC_TITLES) + r")", re.IGNORECASE)
ABBREV_END_PATTERN = re.compile(r"\b(" + "|".join(ABBREVIATIONS) + r")(?=\s+[A-Z0-9\"'‘“])", re.IGNORECASE)
ABBREV_MID_PATTERN = re.compile(r"\b(" + "|".join(ABBREVIATIONS) + r")", re.IGNORECASE)


def clean_text(text: str) -> Tuple[str, str]:
    """
    Validates and cleans input text while preserving original text integrity.

    Returns:
        Tuple[str, str]: (original_text, normalized_text)

    Raises:
        ValidationException: If input is empty, whitespace-only, or exceeds length limits.
    """
    if text is None:
        raise ValidationException("Input text cannot be empty.")

    original_text = text.strip()
    if not original_text:
        raise ValidationException("Input text cannot be empty or whitespace-only.")

    if len(original_text) < 5:
        raise ValidationException("Input text must contain at least 5 characters.")

    if len(original_text) > 20000:
        raise ValidationException(f"Input text length ({len(original_text)} characters) exceeds maximum allowed limit of 20,000 characters.")

    # Unicode normalization (NFKC decomposes compatibility chars and recomposes canonically)
    normalized = unicodedata.normalize("NFKC", original_text)

    # Normalize carriage returns and line feeds
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

    # Replace multiple continuous whitespace/tabs with single space, preserve single paragraph breaks
    paragraphs = [re.sub(r"[ \t]+", " ", p).strip() for p in normalized.split("\n")]
    normalized_text = "\n".join([p for p in paragraphs if p])

    return original_text, normalized_text


def segment_sentences(text: str) -> List[str]:
    """
    Splits text into separate sentences while reliably avoiding false splits on
    honorifics, abbreviations, initials, decimal numbers, and currency values.
    """
    if not text or not text.strip():
        return []

    # 1. Mask honorific titles unconditionally (e.g. Dr., Prof., Mr.)
    masked = TITLE_PATTERN.sub(lambda m: m.group(0).replace(".", "§DOT§"), text)

    # 2. Mask periods between digits (e.g. 7.2% or $1.5 billion)
    masked = re.sub(r"(\d)\.(\d)", r"\1§DOT§\2", masked)

    # 3. Mask periods in single-letter initials (e.g. "A. B. Sharma")
    masked = re.sub(r"\b([A-Z])\.", r"\1§DOT§", masked)

    # 4. Handle abbreviations followed by sentence boundaries (keep final period)
    def mask_abbrev_end(match):
        val = match.group(1)
        last_dot_idx = val.rfind(".")
        if last_dot_idx != -1:
            return val[:last_dot_idx].replace(".", "§DOT§") + "."
        return val

    masked = ABBREV_END_PATTERN.sub(mask_abbrev_end, masked)

    # 5. Handle remaining abbreviations (mask all periods)
    masked = ABBREV_MID_PATTERN.sub(lambda m: m.group(1).replace(".", "§DOT§"), masked)

    # 6. Sentence boundary: matching sentence ending punctuation followed by space or newline
    raw_sentences = re.split(r"(?<=[.?!])\s+(?=[A-Z0-9\"'‘“])", masked)

    cleaned_sentences = []
    for s in raw_sentences:
        unmasked = s.replace("§DOT§", ".").strip()
        # Discard empty strings or isolated punctuation
        if unmasked and len(unmasked) > 3 and any(c.isalnum() for c in unmasked):
            cleaned_sentences.append(unmasked)

    # Fallback if splitting produced nothing
    if not cleaned_sentences and text.strip():
        cleaned_sentences = [text.strip()]

    return cleaned_sentences
