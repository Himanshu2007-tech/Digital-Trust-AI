import os
import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple, Optional
from app.core.config import settings
from app.core.exceptions import SecurityRiskException


# Disallowed private and restricted IP blocks for SSRF prevention
PRIVATE_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("10.0.0.0/8"),         # RFC 1918 Class A
    ipaddress.ip_network("172.16.0.0/12"),      # RFC 1918 Class B
    ipaddress.ip_network("192.168.0.0/16"),     # RFC 1918 Class C
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local / AWS & cloud metadata (169.254.169.254)
    ipaddress.ip_network("100.64.0.0/10"),      # Shared address space / CGNAT
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1 documentation
    ipaddress.ip_network("198.18.0.0/15"),      # Network benchmark tests
    ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2 documentation
    ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3 documentation
    ipaddress.ip_network("224.0.0.0/4"),        # IPv4 Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved (former Class E)
    ipaddress.ip_network("255.255.255.255/32"), # IPv4 Broadcast
    ipaddress.ip_network("::1/128"),            # IPv6 loopback
    ipaddress.ip_network("::/128"),             # IPv6 unspecified
    ipaddress.ip_network("fc00::/7"),           # IPv6 unique local (ULA)
    ipaddress.ip_network("fe80::/10"),          # IPv6 link-local
    ipaddress.ip_network("ff00::/8"),           # IPv6 multicast
    ipaddress.ip_network("2001:db8::/32"),      # IPv6 documentation
    ipaddress.ip_network("2002::/16"),          # 6to4 relay (potential private IPv4 encapsulation)
    ipaddress.ip_network("::ffff:0:0/96"),      # IPv4-mapped IPv6
    ipaddress.ip_network("100.100.100.200/32"), # Alibaba Cloud metadata IP
]

FORBIDDEN_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "metadata.google.internal",
    "metadata",
    "instance-data",
    "kubernetes.default.svc",
    "vault.local",
    "consul.local",
}

FORBIDDEN_TLDS_AND_SUFFIXES = (
    ".internal",
    ".local",
    ".localhost",
    ".test",
    ".example",
    ".invalid",
    ".onion",
    ".arpa",
)


def is_forbidden_ip(ip_str: str) -> Tuple[bool, str]:
    """
    Checks if an IP address string belongs to a loopback, private, link-local,
    multicast, reserved, or cloud metadata network.
    Supports standard IPv4, IPv6, and IPv4-mapped IPv6 representations.
    """
    try:
        ip_obj = ipaddress.ip_address(ip_str.strip())
    except ValueError:
        return True, f"Invalid IP address format '{ip_str}'."

    # If IPv4-mapped IPv6 (e.g., ::ffff:127.0.0.1), unwrap to inspect the underlying IPv4 address
    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
        ip_obj = ip_obj.ipv4_mapped
    # If NAT64 well-known prefix (64:ff9b::/96), unwrap the embedded IPv4 address
    elif isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj in ipaddress.ip_network("64:ff9b::/96"):
        ip_obj = ipaddress.IPv4Address(ip_obj.packed[-4:])

    if ip_obj.is_private:
        return True, f"Private IP address ({ip_str})"
    if ip_obj.is_loopback:
        return True, f"Loopback IP address ({ip_str})"
    if ip_obj.is_link_local:
        return True, f"Link-local IP address ({ip_str})"
    if ip_obj.is_multicast:
        return True, f"Multicast IP address ({ip_str})"
    if ip_obj.is_reserved:
        return True, f"Reserved IP address ({ip_str})"
    if ip_obj.is_unspecified:
        return True, f"Unspecified IP address ({ip_str})"

    for forbidden_net in PRIVATE_NETWORKS:
        if ip_obj in forbidden_net:
            return True, f"Restricted IP network ({ip_str})"

    return False, ""


def validate_url_for_ssrf(url: str) -> str:
    """
    Validates a URL to prevent Server-Side Request Forgery (SSRF).
    - Blocks embedded authentication credentials (user:pass@host)
    - Rejects control characters and null bytes
    - Enforces http/https schemes only
    - Blocks forbidden ports (only standard HTTP/HTTPS ports 80, 443, 8080, 8443 allowed)
    - Detects and evaluates integer/hexadecimal IP representations
    - Blocks known cloud metadata hostnames and internal TLDs (.internal, .local, etc.)
    - Resolves DNS and blocks all loopback, private, and reserved network destinations
    """
    if not url or not isinstance(url, str):
        raise SecurityRiskException("Invalid URL: Empty or not a string.")

    url_clean = url.strip()

    # Reject ASCII control characters and null bytes
    if any(ord(c) < 32 or ord(c) == 127 for c in url_clean):
        raise SecurityRiskException("Invalid URL: Contains forbidden control characters.")

    parsed = urlparse(url_clean)
    if parsed.scheme.lower() not in ("http", "https"):
        raise SecurityRiskException(f"Invalid URL scheme '{parsed.scheme}'. Only http and https are allowed.")

    # Reject URLs containing embedded credentials / userinfo
    if parsed.username or parsed.password:
        raise SecurityRiskException("URLs containing embedded authentication credentials are not permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SecurityRiskException("Invalid URL: Missing hostname.")

    hostname_lower = hostname.lower().strip("[]")

    # Disallow known cloud metadata, localhost names, and internal TLDs
    if hostname_lower in FORBIDDEN_HOSTNAMES or any(hostname_lower.endswith(suf) for suf in FORBIDDEN_TLDS_AND_SUFFIXES):
        raise SecurityRiskException(f"Access to '{hostname}' is prohibited for security reasons.")

    # Check port if provided
    if parsed.port and parsed.port not in (80, 443, 8080, 8443):
        raise SecurityRiskException(f"Access to port {parsed.port} is not permitted for news URL verification.")

    # Check for direct decimal or hex IP representations (e.g., 2130706433 or 0x7f000001)
    direct_ip_candidates = []
    if hostname_lower.isdigit():
        try:
            direct_ip_candidates.append(ipaddress.ip_address(int(hostname_lower)))
        except (ValueError, OverflowError):
            pass
    elif hostname_lower.startswith(("0x", "0X")):
        try:
            direct_ip_candidates.append(ipaddress.ip_address(int(hostname_lower, 16)))
        except (ValueError, OverflowError):
            pass

    for candidate in direct_ip_candidates:
        forbidden, reason = is_forbidden_ip(str(candidate))
        if forbidden:
            raise SecurityRiskException(f"URL points to a forbidden destination: {reason}.")

    # Resolve IP address to check if it points to private or restricted network
    try:
        ip_addresses = socket.getaddrinfo(hostname_lower, None)
        if not ip_addresses:
            raise SecurityRiskException(f"Could not resolve hostname '{hostname}'.")
        for family, _, _, _, sockaddr in ip_addresses:
            ip_str = sockaddr[0]
            forbidden, reason = is_forbidden_ip(ip_str)
            if forbidden:
                raise SecurityRiskException(f"URL points to a forbidden private IP network ({reason}).")
    except socket.gaierror:
        raise SecurityRiskException(f"Could not resolve hostname '{hostname}'.")

    return url_clean


def sanitize_filename(filename: Optional[str], default_name: str = "file") -> str:
    """
    Sanitizes an untrusted uploaded filename:
    - Strips directory components and path traversal sequences
    - Strips null bytes and non-printable control characters
    - Normalizes leading/trailing spaces and dots
    - Neutralizes CSV formula triggers (=, +, -, @)
    """
    if not filename or not isinstance(filename, str):
        return default_name

    # Strip path components across Windows and POSIX separators
    clean_name = os.path.basename(filename.replace("\\", "/"))

    # Remove null bytes and non-printable control characters
    clean_name = "".join(c for c in clean_name if c.isprintable() and c not in '\x00\r\n\t')

    # Strip leading/trailing whitespace and dots
    clean_name = clean_name.strip(" .")

    # Neutralize CSV formula execution triggers
    if clean_name.startswith(("=", "+", "-", "@")):
        clean_name = f"'{clean_name}"

    return clean_name if clean_name else default_name


def validate_file_upload(filename: str, content_type: str, file_size: int) -> Tuple[bool, Optional[str]]:
    """
    Validates uploaded file against size limits and allowed MIME types.
    """
    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        return False, f"File size exceeds maximum allowed limit ({settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB)"

    allowed_types = (
        settings.ALLOWED_IMAGE_MIME_TYPES +
        settings.ALLOWED_AUDIO_MIME_TYPES +
        settings.ALLOWED_VIDEO_MIME_TYPES
    )

    if content_type not in allowed_types:
        return False, f"Unsupported MIME type '{content_type}'."

    return True, None
