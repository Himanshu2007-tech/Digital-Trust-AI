import logging
from urllib.parse import urlparse, urljoin
from typing import Tuple, Optional
import httpx

from app.core.config import settings
from app.core.exceptions import SecurityRiskException
from app.utils.security_helpers import validate_url_for_ssrf, is_forbidden_ip

logger = logging.getLogger(__name__)


class SafeArticleFetcher:
    """
    Hardened HTTP article fetcher with SSRF prevention, per-hop redirect validation,
    strict Content-Type verification, streaming payload limits, and connection timeouts.
    """

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 "
        "TruthLens/1.0"
    )

    def __init__(
        self,
        connect_timeout: Optional[float] = None,
        read_timeout: Optional[float] = None,
        total_timeout: Optional[float] = None,
        max_redirects: Optional[int] = None,
        max_size_bytes: Optional[int] = None,
        user_agent: Optional[str] = None
    ):
        self.connect_timeout = connect_timeout or float(settings.ARTICLE_CONNECT_TIMEOUT_SECONDS)
        self.read_timeout = read_timeout or 10.0
        self.total_timeout = total_timeout or float(settings.ARTICLE_REQUEST_TIMEOUT_SECONDS)
        self.max_redirects = max_redirects or settings.MAX_ARTICLE_REDIRECTS
        self.max_size_bytes = max_size_bytes or (settings.MAX_ARTICLE_RESPONSE_MB * 1024 * 1024)
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT

    def fetch(self, initial_url: str) -> Tuple[str, str, int]:
        """
        Safely fetches an article HTML string from a URL.
        Returns: (html_content: str, final_url: str, status_code: int)
        Raises:
            SecurityRiskException: For SSRF or unauthorized address access.
            ValueError: For non-HTML MIME types, oversized payloads, or empty bodies.
            httpx.HTTPError: For network or HTTP protocol failures.
        """
        current_url = validate_url_for_ssrf(initial_url)
        if urlparse(current_url).path.lower().endswith(".pdf"):
            raise ValueError(
                "PDF verification is not supported in this version. "
                "Please provide a standard web/HTML news article URL."
            )
        redirect_count = 0

        timeout_config = httpx.Timeout(
            timeout=self.total_timeout,
            connect=self.connect_timeout,
            read=self.read_timeout,
            write=5.0
        )

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }

        with httpx.Client(timeout=timeout_config, follow_redirects=False) as client:
            while True:
                # Validate URL before every HTTP request
                validated_url = validate_url_for_ssrf(current_url)

                try:
                    with client.stream("GET", validated_url, headers=headers) as response:
                        # Verify the connected remote socket peer IP to mitigate DNS rebinding attacks
                        network_stream = response.extensions.get("network_stream")
                        if network_stream and hasattr(network_stream, "_sock"):
                            try:
                                peer = network_stream._sock.getpeername()
                                if peer and isinstance(peer, tuple) and len(peer) > 0:
                                    peer_ip = peer[0]
                                    forbidden, reason = is_forbidden_ip(str(peer_ip))
                                    if forbidden:
                                        raise SecurityRiskException(
                                            f"Security violation: Connection resolved to forbidden destination: {reason}."
                                        )
                            except SecurityRiskException:
                                raise
                            except Exception as sock_err:
                                logger.debug(f"Could not inspect peer socket for {validated_url}: {sock_err}")

                        # Handle HTTP Redirects manually
                        if response.status_code in (301, 302, 303, 307, 308):
                            redirect_count += 1
                            if redirect_count > self.max_redirects:
                                raise ValueError(
                                    f"Too many redirects ({redirect_count}). Maximum allowed is {self.max_redirects}."
                                )

                            location = response.headers.get("Location")
                            if not location:
                                raise ValueError(f"HTTP {response.status_code} redirect with missing Location header.")

                            current_url = urljoin(validated_url, location)
                            logger.info(f"SafeArticleFetcher: following redirect hop {redirect_count} to {current_url}")
                            continue

                        # Check HTTP error status
                        if response.status_code >= 400:
                            raise ValueError(
                                f"Failed to fetch article from '{validated_url}'. "
                                f"Server returned HTTP {response.status_code} {response.reason_phrase}."
                            )

                        # Validate Content-Type
                        content_type_raw = response.headers.get("content-type", "")
                        mime_type = content_type_raw.split(";")[0].strip().lower()

                        if "application/pdf" in mime_type or validated_url.lower().endswith(".pdf"):
                            raise ValueError(
                                "PDF verification is not supported in this version. "
                                "Please provide a standard web/HTML news article URL."
                            )

                        if mime_type and mime_type not in settings.ALLOWED_ARTICLE_CONTENT_TYPES:
                            raise ValueError(
                                f"Unsupported content type '{mime_type}'. "
                                f"TruthLens currently supports HTML news and article webpages."
                            )

                        # Stream content body with strict byte cap
                        raw_bytes = bytearray()
                        for chunk in response.iter_bytes():
                            raw_bytes.extend(chunk)
                            if len(raw_bytes) > self.max_size_bytes:
                                raise ValueError(
                                    f"Article payload exceeds maximum allowed size ({settings.MAX_ARTICLE_RESPONSE_MB}MB)."
                                )

                        # Determine encoding and decode
                        encoding = response.encoding or "utf-8"
                        try:
                            html_text = raw_bytes.decode(encoding, errors="replace")
                        except Exception:
                            html_text = raw_bytes.decode("utf-8", errors="replace")

                        if not html_text.strip():
                            raise ValueError("The requested webpage returned an empty response body.")

                        return html_text, validated_url, response.status_code

                except httpx.ConnectTimeout:
                    raise ValueError(f"Connection timed out while trying to reach '{validated_url}'.")
                except httpx.ReadTimeout:
                    raise ValueError(f"Read timed out while downloading article from '{validated_url}'.")
                except httpx.ConnectError as ce:
                    raise ValueError(f"Could not connect to host at '{validated_url}': {str(ce)}")
                except SecurityRiskException:
                    raise
                except ValueError:
                    raise
                except Exception as exc:
                    raise ValueError(f"Error fetching URL '{validated_url}': {str(exc)}")
