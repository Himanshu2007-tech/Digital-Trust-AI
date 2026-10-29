import re
from typing import List, Dict, Any

# Standard URL pattern for transcribed text
URL_REGEX = re.compile(
    r'(?:https?://|www\.)[^\s<>"\'{}|\\^`]+',
    re.IGNORECASE
)

# Common quote patterns in spoken transcripts
QUOTE_PATTERNS = [
    # "Statement" said Speaker / stated Speaker
    re.compile(r'["“\']([^"”\']{10,250})["”\']\s*(?:said|stated|announced|claimed|declared|remarked|tweeted)\s+([A-Z][a-zA-Z\s]{2,40})', re.IGNORECASE),
    # Speaker said/stated "Statement"
    re.compile(r'([A-Z][a-zA-Z\s]{2,40})\s+(?:said|stated|announced|claimed|declared|remarked|tweeted)\s*(?:that|:)?\s*["“\']([^"”\']{10,250})["”\']', re.IGNORECASE),
    # According to Speaker, "Statement"
    re.compile(r'(?:according to|as per)\s+([A-Z][a-zA-Z\s]{2,40})[,:\s]+["“\']([^"”\']{10,250})["”\']', re.IGNORECASE),
]


def extract_transcript_urls(text: str) -> List[str]:
    """Extracts web URLs found inside transcribed speech."""
    matches = URL_REGEX.findall(text)
    clean_urls = []
    for match in matches:
        cleaned = re.sub(r'[\.,;:!?\)\>\]]+$', '', match)
        if cleaned.startswith("www."):
            cleaned = "https://" + cleaned
        if cleaned and cleaned not in clean_urls:
            clean_urls.append(cleaned)
    return clean_urls


def extract_transcript_quotes(text: str) -> List[Dict[str, Any]]:
    """Extracts direct quotations and speaker attributions from transcribed speech."""
    quotes: List[Dict[str, Any]] = []

    for pattern in QUOTE_PATTERNS:
        for match in pattern.finditer(text):
            groups = match.groups()
            if len(groups) == 2:
                # Group ordering depends on pattern
                if any(kw in match.group(0).lower() for kw in ["said", "stated", "announced", "claimed"]) and not match.group(0).startswith('"'):
                    speaker = groups[0].strip()
                    quote_text = groups[1].strip()
                else:
                    quote_text = groups[0].strip()
                    speaker = groups[1].strip()

                if quote_text and not any(q["quote"] == quote_text for q in quotes):
                    quotes.append({
                        "speaker": speaker,
                        "quote": quote_text,
                        "raw_match": match.group(0).strip(),
                    })

    return quotes


# Aliases for consistent naming
extract_spoken_urls = extract_transcript_urls
extract_direct_quotes = extract_transcript_quotes
