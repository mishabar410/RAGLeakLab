"""SSRF validation utilities for HTTP targets.

Validates URLs to prevent Server-Side Request Forgery attacks by:
- Blocking private/internal IP ranges
- Restricting URL schemes to http/https only
- Supporting optional domain allowlists
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# Only allow HTTP and HTTPS schemes
ALLOWED_SCHEMES = frozenset({"http", "https"})

# Private/internal IP networks to block
PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),  # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),  # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]


class SSRFValidationError(ValueError):
    """Raised when URL fails SSRF validation."""


def is_private_ip(ip_string: str) -> bool:
    """Check if IP address is in a private/internal range.

    Args:
        ip_string: IP address as string (IPv4 or IPv6).

    Returns:
        True if IP is private/internal, False otherwise.
    """
    try:
        ip = ipaddress.ip_address(ip_string)
        return any(ip in network for network in PRIVATE_NETWORKS)
    except ValueError:
        # Not a valid IP, treat as hostname
        return False


def validate_url(
    url: str,
    allowed_domains: list[str] | None = None,
) -> None:
    """Validate URL for SSRF safety.

    Args:
        url: URL to validate.
        allowed_domains: Optional list of allowed domain names.
            If provided, only these domains are permitted.

    Raises:
        SSRFValidationError: If URL fails validation.
    """
    parsed = urlparse(url)

    # Check scheme
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise SSRFValidationError(f"Invalid URL scheme '{parsed.scheme}'. Only http/https allowed.")

    # Extract hostname
    hostname = parsed.hostname
    if not hostname:
        raise SSRFValidationError("URL must have a hostname.")

    # Check domain allowlist if provided
    if allowed_domains:
        if hostname.lower() not in [d.lower() for d in allowed_domains]:
            raise SSRFValidationError(f"Domain '{hostname}' not in allowed domains list.")

    # Resolve hostname to IP and check for private ranges
    try:
        # Get all IPs for hostname (handles DNS round-robin)
        _, _, ip_list = socket.gethostbyname_ex(hostname)
        for ip in ip_list:
            if is_private_ip(ip):
                raise SSRFValidationError(f"URL resolves to private/internal IP: {ip}")
    except socket.gaierror:
        # DNS resolution failed - could be invalid hostname
        # Allow it through - requests will fail naturally
        pass
