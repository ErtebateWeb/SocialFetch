"""Abstract base classes for the SocialFetch downloader framework."""

from abc import ABC, abstractmethod

from socialfetch.core.models import DownloadRequest, MediaInfo
from socialfetch.core.types import PlatformName


class BaseDownloader(ABC):
    """Abstract downloader that every platform provider must implement."""

    @property
    @abstractmethod
    def platform(self) -> PlatformName:
        """Return the canonical platform identifier (e.g. 'instagram')."""

    @abstractmethod
    async def download(self, request: DownloadRequest) -> MediaInfo:
        """Download media from the given request and return the result."""
