"""Custom exception hierarchy for SocialFetch."""


class SocialFetchError(Exception):
    """Base exception for all SocialFetch errors."""


class DownloadError(SocialFetchError):
    """Base exception for download failures."""


class NetworkError(DownloadError):
    """Raised when a network request fails (timeout, DNS, connection)."""


class AuthError(DownloadError):
    """Raised when platform credentials are invalid or expired."""


class RateLimitError(DownloadError):
    """Raised when the platform enforces rate limiting."""


class MediaNotFoundError(DownloadError):
    """Raised when the requested media is deleted or unavailable."""


class InvalidURLError(SocialFetchError):
    """Raised when a URL cannot be parsed or does not match any platform."""
