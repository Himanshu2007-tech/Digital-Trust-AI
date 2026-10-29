import re
from typing import List, Dict, Any

# Standard URL pattern for text and OCR output
URL_PATTERN = re.compile(
    r'(?:https?://|www\.)[^\s<>"\'{}|\\^`]+',
    re.IGNORECASE
)

# Social media handle pattern
HANDLE_PATTERN = re.compile(r'(?<!\w)@([A-Za-z0-9_]{2,30})\b')

# Engagement metrics pattern (e.g., "12.4K Likes", "450 Retweets")
METRICS_PATTERN = re.compile(
    r'\b(\d+(?:\.\d+)?[KMBkmb]?)\s*(reposts?|retweets?|likes?|views?|shares?|quotes?|replies?)\b',
    re.IGNORECASE
)

# Date/time patterns in screenshot headers/footers
DATETIME_PATTERNS = [
    re.compile(r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\s*(?:·|-|•)?\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b', re.IGNORECASE),
    re.compile(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b', re.IGNORECASE),
    re.compile(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b'),
    re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),
]


def extract_detected_urls(text: str) -> List[str]:
    """
    Extracts all valid web URLs found inside OCR recognized text.
    Strips trailing punctuation commonly attached by OCR.
    """
    matches = URL_PATTERN.findall(text)
    clean_urls = []
    for match in matches:
        # Strip trailing OCR artifacts like dots, brackets, colons
        cleaned = re.sub(r'[\.,;:!?\)\>\]]+$', '', match)
        if cleaned.startswith("www."):
            cleaned = "https://" + cleaned
        if cleaned and cleaned not in clean_urls:
            clean_urls.append(cleaned)
    return clean_urls


def extract_social_handles(text: str) -> List[str]:
    """Extracts @user handles from social media screenshots."""
    handles = []
    for match in HANDLE_PATTERN.finditer(text):
        handle = f"@{match.group(1)}"
        if handle not in handles:
            handles.append(handle)
    return handles


def extract_metrics(text: str) -> Dict[str, str]:
    """Extracts social media engagement counts (likes, reposts, views)."""
    metrics: Dict[str, str] = {}
    for match in METRICS_PATTERN.finditer(text):
        count = match.group(1).upper()
        metric_name = match.group(2).lower()
        metrics[metric_name] = count
    return metrics


def extract_dates(text: str) -> List[str]:
    """Extracts timestamp strings found in screenshot headers."""
    dates: List[str] = []
    for pattern in DATETIME_PATTERNS:
        for match in pattern.finditer(text):
            found = match.group(0).strip()
            if found and found not in dates:
                dates.append(found)
    return dates


# Aliases for consistent naming
extract_ocr_urls = extract_detected_urls
extract_ocr_handles = extract_social_handles
extract_ocr_metrics = extract_metrics
extract_ocr_dates = extract_dates

