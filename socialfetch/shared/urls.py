"""URL validation utilities."""

from __future__ import annotations

from urllib.parse import urlparse


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL with scheme and netloc."""
    if not url or not url.strip():
        return False
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except (ValueError, AttributeError):
        return False
