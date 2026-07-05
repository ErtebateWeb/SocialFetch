"""Custom exceptions for SocialFetch."""


class SocialFetchError(Exception):
    """Base exception for all SocialFetch errors."""


class InvalidUrlError(SocialFetchError):
    """Raised when a URL is invalid or unsupported."""


class DownloaderNotFoundError(SocialFetchError):
    """Raised when no downloader is registered for a given URL."""


class DownloadFailedError(SocialFetchError):
    """Raised when a download operation fails."""
