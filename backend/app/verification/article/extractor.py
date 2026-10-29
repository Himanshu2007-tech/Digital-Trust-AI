import hashlib
import logging
import re
from urllib.parse import urlparse, urljoin
from typing import Optional, List, Tuple
from bs4 import BeautifulSoup, Comment

from app.verification.article.base import ArticleExtractor, ExtractedArticle

logger = logging.getLogger(__name__)

# Common paywall & bot-blocker phrases
JS_BLOCKER_PHRASES = [
    "please enable javascript",
    "javascript is required",
    "enable javascript to run this app",
    "turn on javascript",
    "browser does not support javascript",
    "security check to access",
    "checking your browser before accessing",
    "cloudflare ray id",
    "ddos protection by cloudflare",
]

PAYWALL_PHRASES = [
    "subscribe to continue reading",
    "subscribe to read full article",
    "to read the full article, subscribe",
    "you have reached your limit of free articles",
    "sign in or subscribe",
    "this content is exclusive to subscribers",
    "members-only story",
]

# Tags to strip entirely
STRIP_TAGS = [
    "script", "style", "noscript", "svg", "canvas", "form",
    "iframe", "nav", "footer", "header", "aside", "select", "button"
]

# Patterns for non-editorial elements
BOILERPLATE_CLASSES_OR_IDS = re.compile(
    r"\b(ads?|advertisement|banner|cookie|consent|popup|modal|share|social|sidebar|newsletter|comments?|related|promo)\b",
    re.IGNORECASE
)


class ReadabilityArticleExtractor(ArticleExtractor):
    """
    DOM sanitizing readability article extractor.
    Extracts article body, metadata, author, publication date,
    filters ads/boilerplates, and computes SHA-256 content hashes.
    """

    MIN_WORD_COUNT = 40
    MIN_CHAR_COUNT = 150

    def extract_article(self, html: str, url: str) -> ExtractedArticle:
        """
        Parses raw HTML string and extracts article text and metadata.
        Raises ValueError if content is insufficient, paywalled, or JS-blocked.
        """
        if not html or not html.strip():
            raise ValueError("HTML content is empty.")

        soup = BeautifulSoup(html, "html.parser")

        # 1. Check for whole-page JS or anti-bot block early
        page_raw_text = soup.get_text(" ", strip=True).lower()
        for phrase in JS_BLOCKER_PHRASES:
            if phrase in page_raw_text and len(page_raw_text) < 1000:
                raise ValueError(
                    f"Page requires JavaScript rendering or anti-bot verification ({phrase}). "
                    "TruthLens is unable to extract article content directly."
                )

        # 2. Extract Metadata
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower().replace("www.", "")

        # Canonical URL
        canonical_link = soup.find("link", rel=lambda r: r and "canonical" in r.lower())
        canonical_url = None
        if canonical_link and canonical_link.get("href"):
            canonical_url = urljoin(url, canonical_link["href"].strip())

        # Title
        title = self._extract_title(soup)

        # Publisher / Site Name
        publisher = self._extract_publisher(soup, domain)

        # Author
        author = self._extract_author(soup)

        # Published Date
        published_at = self._extract_date(soup)

        # Description
        description = self._extract_description(soup)

        # Language
        html_tag = soup.find("html")
        language = "en"
        if html_tag and getattr(html_tag, "attrs", None):
            language = str(html_tag.attrs.get("lang") or "en")[:20]

        # Featured Image
        featured_image_url = self._extract_image(soup, url)

        # 3. Sanitize DOM for content extraction
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Remove irrelevant tags
        for tag_name in STRIP_TAGS:
            for el in soup.find_all(tag_name):
                el.decompose()

        # Remove elements with advertising / cookie / widget classes or IDs
        for el in soup.find_all(True):
            if not el or getattr(el, "attrs", None) is None:
                continue
            if el.name in ("html", "body", "main", "article"):
                continue
            el_id = str(el.attrs.get("id") or "")
            raw_cls = el.attrs.get("class", [])
            el_cls = " ".join(raw_cls) if isinstance(raw_cls, list) else str(raw_cls or "")
            if BOILERPLATE_CLASSES_OR_IDS.search(el_id) or BOILERPLATE_CLASSES_OR_IDS.search(el_cls):
                try:
                    el.decompose()
                except Exception:
                    pass

        # 4. Extract Main Article Body
        article_text = self._extract_body(soup)

        # 5. Quality, Length, and Paywall Checks
        words = re.findall(r"\b[a-zA-Z0-9_\-']+\b", article_text)
        word_count = len(words)
        content_length = len(article_text)

        # Check for paywall indicators in the extracted body or page
        for phrase in PAYWALL_PHRASES:
            if phrase in article_text.lower():
                raise ValueError(
                    f"Article appears to be behind a paywall or subscription requirement ('{phrase}'). "
                    "Insufficient full text available for objective verification."
                )

        if word_count < self.MIN_WORD_COUNT or content_length < self.MIN_CHAR_COUNT:
            # Check if there is paywall or JS text on page
            for phrase in PAYWALL_PHRASES:
                if phrase in page_raw_text:
                    raise ValueError(
                        f"Article is behind a paywall or login gate ('{phrase}'). "
                        "Full text could not be extracted."
                    )
            raise ValueError(
                f"Insufficient article text extracted ({word_count} words, {content_length} characters). "
                f"Minimum required is {self.MIN_WORD_COUNT} words. "
                "The URL may be a media page, video, home page, or require client-side JavaScript."
            )

        # 6. Deduplication Hash
        content_hash = hashlib.sha256(article_text.strip().encode("utf-8")).hexdigest()

        return ExtractedArticle(
            original_url=url,
            canonical_url=canonical_url or url,
            domain=domain,
            title=title,
            publisher=publisher,
            author=author,
            published_at=published_at,
            description=description,
            language=language,
            featured_image_url=featured_image_url,
            article_text=article_text,
            content_hash=content_hash,
            content_length=content_length,
            word_count=word_count,
            extraction_method="readability_bs4",
            retrieval_status="success"
        )

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        # 1. OpenGraph title
        og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "og:title"})
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        # 2. Twitter title
        tw_title = soup.find("meta", attrs={"name": "twitter:title"})
        if tw_title and tw_title.get("content"):
            return tw_title["content"].strip()

        # 3. Standard title tag
        if soup.title and soup.title.string:
            t = soup.title.string.strip()
            # Clean common publisher suffixes (e.g., "RBI increases repo rate | Reuters")
            t_cleaned = re.sub(r"\s*[-|–—]\s*[^–—|-]+$", "", t)
            return t_cleaned if len(t_cleaned) > 10 else t

        # 4. First H1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(" ", strip=True)

        return None

    def _extract_publisher(self, soup: BeautifulSoup, domain: str) -> Optional[str]:
        og_site = soup.find("meta", property="og:site_name")
        if og_site and og_site.get("content"):
            return og_site["content"].strip()

        pub_meta = soup.find("meta", attrs={"name": "publisher"})
        if pub_meta and pub_meta.get("content"):
            return pub_meta["content"].strip()

        # Fallback to domain name formatting (e.g. bbc.co.uk -> bbc, reuters.com -> Reuters)
        parts = domain.split(".")
        if len(parts) >= 2:
            return parts[-2].capitalize() if parts[-2] not in ("co", "com", "org", "gov") else parts[0].capitalize()
        return domain.capitalize()

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        # Meta author
        author_meta = (
            soup.find("meta", attrs={"name": "author"}) or
            soup.find("meta", property="article:author") or
            soup.find("meta", attrs={"name": "twitter:creator"})
        )
        if author_meta and author_meta.get("content"):
            return author_meta["content"].strip()[:255]

        # Common byline elements
        byline = soup.find(attrs={"class": re.compile(r"(byline|author|writer)", re.I)})
        if byline:
            txt = byline.get_text(" ", strip=True)
            txt = re.sub(r"^(by|written by)\s+", "", txt, flags=re.I).strip()
            if 0 < len(txt) <= 100:
                return txt

        return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        date_meta = (
            soup.find("meta", property="article:published_time") or
            soup.find("meta", attrs={"name": "publication_date"}) or
            soup.find("meta", attrs={"name": "date"}) or
            soup.find("meta", attrs={"name": "pubdate"}) or
            soup.find("meta", attrs={"name": "sailthru.date"})
        )
        if date_meta and date_meta.get("content"):
            return date_meta["content"].strip()[:100]

        # Check time tag
        time_tag = soup.find("time")
        if time_tag and time_tag.get("datetime"):
            return time_tag["datetime"].strip()[:100]

        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        desc = (
            soup.find("meta", property="og:description") or
            soup.find("meta", attrs={"name": "description"}) or
            soup.find("meta", attrs={"name": "twitter:description"})
        )
        if desc and desc.get("content"):
            return desc["content"].strip()
        return None

    def _extract_image(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if img and img.get("content"):
            return urljoin(base_url, img["content"].strip())
        return None

    def _extract_body(self, soup: BeautifulSoup) -> str:
        """
        Locates the primary article container using semantic selectors
        and gathers paragraphs.
        """
        candidate_containers = (
            soup.find_all("article") +
            soup.find_all("main") +
            soup.find_all(attrs={"role": "main"}) +
            soup.find_all(attrs={"itemprop": "articleBody"}) +
            soup.find_all(attrs={"class": re.compile(r"(article[-_]?body|story[-_]?content|entry[-_]?content|post[-_]?content)", re.I)})
        )

        paragraphs: List[str] = []

        if candidate_containers:
            # Use the candidate container with the longest text
            best_container = max(candidate_containers, key=lambda c: len(c.get_text()))
            paragraphs = self._get_clean_paragraphs(best_container)

        # Fallback to searching all paragraphs in body if container was empty or too small
        if sum(len(p) for p in paragraphs) < 150:
            body = soup.find("body") or soup
            paragraphs = self._get_clean_paragraphs(body)

        return "\n\n".join(paragraphs).strip()

    def _get_clean_paragraphs(self, root) -> List[str]:
        paras: List[str] = []
        for p in root.find_all("p"):
            text = p.get_text(" ", strip=True)
            # Filter boilerplate sentences or trivial short lines
            if len(text) < 25:
                continue
            if re.match(r"^(follow us|sign up|subscribe|read more|advertisement|share this|copyright|click here)", text, re.I):
                continue
            paras.append(text)
        return paras
