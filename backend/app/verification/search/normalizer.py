import re
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from app.core.config import settings
from app.utils.security_helpers import validate_url_for_ssrf
from app.verification.search.models import SourceType

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "ocid", "ncid", "mc_cid", "mc_eid",
    "_hsenc", "_hsmi", "ysclid", "yclid", "igshid", "si"
}

PRIMARY_DOMAINS = {
    "rbi.org.in", "isro.gov.in", "drdo.gov.in", "who.int", "un.org",
    "unicef.org", "eci.gov.in", "supremecourtofindia.nic.in", "finmin.nic.in",
    "mohfw.gov.in", "nasa.gov", "cdc.gov", "whitehouse.gov", "fda.gov",
    "worldbank.org", "imf.org", "wto.org", "pib.gov.in", "india.gov.in"
}

FACT_CHECK_DOMAINS = {
    "snopes.com", "politifact.com", "factcheck.org", "altnews.in",
    "boomlive.in", "vishvasnews.com", "fullfact.org", "checkyourfact.com",
    "factly.in", "leadstories.com", "climatefeedback.org", "healthfeedback.org"
}

RELIABLE_NEWS_DOMAINS = {
    "reuters.com", "apnews.com", "afp.com", "bloomberg.com", "bbc.com",
    "bbc.co.uk", "thehindu.com", "indianexpress.com", "ndtv.com",
    "hindustantimes.com", "timesofindia.indiatimes.com", "nytimes.com",
    "wsj.com", "washingtonpost.com", "theguardian.com", "economist.com",
    "ft.com", "cnbc.com", "aljazeera.com", "nature.com", "sciencedirect.com",
    "ptinews.com"
}

SOCIAL_DOMAINS = {
    "twitter.com", "x.com", "facebook.com", "instagram.com", "reddit.com",
    "t.me", "telegram.org", "tiktok.com", "youtube.com", "threads.net", "linkedin.com"
}

BLOG_DOMAINS = {
    "medium.com", "substack.com", "wordpress.com", "blogspot.com", "blogger.com", "tumblr.com"
}

KNOWN_PUBLISHERS = {
    "rbi.org.in": "Reserve Bank of India",
    "isro.gov.in": "Indian Space Research Organisation (ISRO)",
    "who.int": "World Health Organization",
    "un.org": "United Nations",
    "nasa.gov": "NASA",
    "pib.gov.in": "Press Information Bureau (Govt. of India)",
    "reuters.com": "Reuters",
    "apnews.com": "Associated Press",
    "afp.com": "Agence France-Presse",
    "bloomberg.com": "Bloomberg",
    "bbc.com": "BBC News",
    "bbc.co.uk": "BBC News",
    "thehindu.com": "The Hindu",
    "indianexpress.com": "The Indian Express",
    "timesofindia.indiatimes.com": "The Times of India",
    "ptinews.com": "Press Trust of India (PTI)",
    "ndtv.com": "NDTV",
    "nytimes.com": "The New York Times",
    "wsj.com": "The Wall Street Journal",
    "theguardian.com": "The Guardian",
    "snopes.com": "Snopes",
    "politifact.com": "PolitiFact",
    "factcheck.org": "FactCheck.org",
    "altnews.in": "Alt News",
    "boomlive.in": "BOOM Live",
    "fullfact.org": "Full Fact"
}

SYNDICATION_PATTERNS = [
    (re.compile(r"\b(?:reuters|thomson\s+reuters)\b", re.IGNORECASE), "Reuters Wire"),
    (re.compile(r"\b(?:associated\s+press|ap\s+news)\b", re.IGNORECASE), "Associated Press (AP) Wire"),
    (re.compile(r"\b(?:press\s+trust\s+of\s+india|pti)\b", re.IGNORECASE), "Press Trust of India (PTI)"),
    (re.compile(r"\b(?:ians|indo-asian\s+news\s+service)\b", re.IGNORECASE), "Indo-Asian News Service (IANS)"),
    (re.compile(r"\b(?:afp|agence\s+france-presse)\b", re.IGNORECASE), "Agence France-Presse (AFP)"),
    (re.compile(r"\b(?:ani|asian\s+news\s+international)\b", re.IGNORECASE), "Asian News International (ANI)")
]


def normalize_url(raw_url: str) -> str:
    """
    Sanitizes and canonicalizes a URL:
    - Enforces http/https
    - Lowercases scheme and hostname
    - Strips marketing/tracking parameters (utm_*, fbclid, etc.)
    - Removes default ports
    - Normalizes trailing slashes on non-root paths
    """
    if not raw_url or not isinstance(raw_url, str):
        raise ValueError("URL must be a non-empty string.")

    cleaned = raw_url.strip()
    parsed = urlparse(cleaned)

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: '{scheme}'. Only HTTP/HTTPS allowed.")

    netloc = parsed.netloc.lower()
    # Strip default ports
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    # Clean query parameters
    filtered_queries = []
    if parsed.query:
        query_pairs = parse_qsl(parsed.query, keep_blank_values=False)
        for key, val in query_pairs:
            if key.lower() not in TRACKING_PARAMS:
                filtered_queries.append((key, val))

    new_query = urlencode(filtered_queries)

    # Normalize path
    path = parsed.path
    if path and path != "/" and path.endswith("/"):
        path = path[:-1]
    elif not path:
        path = "/"

    canonical = urlunparse((scheme, netloc, path, parsed.params, new_query, ""))
    return canonical


def extract_domain(url: str) -> str:
    """Extracts root host domain from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def classify_source(domain: str, url: str = "") -> Tuple[SourceType, Optional[str], Optional[str]]:
    """
    Categorizes the source domain into standardized SourceType.
    Returns: (SourceType, publisher_name, country)
    """
    clean_domain = domain.lower()
    if clean_domain.startswith("www."):
        clean_domain = clean_domain[4:]

    country = None
    if clean_domain.endswith(".in") or clean_domain.endswith(".gov.in") or clean_domain.endswith(".nic.in"):
        country = "India"
    elif clean_domain.endswith(".uk") or clean_domain.endswith(".co.uk"):
        country = "United Kingdom"
    elif clean_domain.endswith(".us") or clean_domain.endswith(".gov") or clean_domain.endswith(".mil"):
        country = "United States"

    publisher = KNOWN_PUBLISHERS.get(clean_domain)

    # 1. Primary official sources
    if (
        clean_domain in PRIMARY_DOMAINS or
        clean_domain.endswith(".gov") or
        clean_domain.endswith(".gov.in") or
        clean_domain.endswith(".nic.in") or
        clean_domain.endswith(".mil") or
        clean_domain.endswith(".int")
    ):
        return SourceType.PRIMARY, publisher or clean_domain, country

    # 2. Fact checkers
    if clean_domain in FACT_CHECK_DOMAINS or "fact-check" in url.lower() or "factcheck" in clean_domain:
        return SourceType.FACT_CHECK, publisher or clean_domain, country

    # 3. Established wire & reputable news
    if clean_domain in RELIABLE_NEWS_DOMAINS or clean_domain in settings.RELIABLE_SOURCE_DOMAINS:
        return SourceType.RELIABLE_NEWS, publisher or clean_domain, country

    # 4. Social media
    if clean_domain in SOCIAL_DOMAINS:
        return SourceType.SOCIAL_MEDIA, publisher or clean_domain, country

    # 5. Blogs
    if clean_domain in BLOG_DOMAINS:
        return SourceType.BLOG, publisher or clean_domain, country

    # 6. Secondary / General
    if clean_domain.endswith(".org") or clean_domain.endswith(".edu") or "news" in clean_domain:
        return SourceType.SECONDARY, publisher or clean_domain, country

    return SourceType.UNKNOWN, publisher or clean_domain, country


def detect_syndication(title: str, snippet: str) -> Optional[str]:
    """Detects wire agency syndication indicators within result snippet or headline."""
    text = f"{title} {snippet}"
    for pattern, agency in SYNDICATION_PATTERNS:
        if pattern.search(text):
            return agency
    return None


def validate_and_normalize_result(
    title: str,
    url: str,
    snippet: str,
    query: str,
    provider: str,
    published_at: Optional[str] = None
) -> Optional[dict]:
    """
    Validates, canonicalizes, and enriches a raw search result.
    Applies SSRF safety validation.
    Returns normalized dictionary or None if invalid/unsupported/unsafe.
    """
    if not url or not isinstance(url, str):
        return None

    # Enforce safe schemes
    clean_url = url.strip()
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        return None

    try:
        # SSRF check: prevents loopback, link-local, and private RFC-1918 addresses
        validate_url_for_ssrf(clean_url)
        canonical = normalize_url(clean_url)
    except Exception:
        # Reject SSRF risks or unparseable URLs
        return None

    domain = extract_domain(canonical)
    if not domain or "." not in domain:
        return None

    source_type, publisher, country = classify_source(domain, canonical)
    syndication = detect_syndication(title, snippet)

    clean_title = (title or domain).strip()
    clean_snippet = (snippet or "").strip()

    return {
        "title": clean_title,
        "url": clean_url,
        "canonical_url": canonical,
        "domain": domain,
        "snippet": clean_snippet,
        "published_at": published_at,
        "publisher": publisher,
        "author": None,
        "country": country,
        "source_type": source_type,
        "query": query,
        "provider": provider,
        "syndication_source": syndication
    }
