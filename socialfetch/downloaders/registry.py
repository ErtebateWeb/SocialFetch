"""Central registry that maps platform identifiers to downloader classes."""

import re
from typing import ClassVar

from socialfetch.core.types import PlatformName
from socialfetch.core.errors import InvalidURLError
from socialfetch.core.interfaces import BaseDownloader


class DownloaderRegistry:
    """Registry of platform-specific downloaders.

    Usage::

        @DownloaderRegistry.register("instagram", r"instagram[.]com/(?:p|reel|tv)/")
        class InstagramDownloader(BaseDownloader):
            ...
    """

    _entries: ClassVar[list[tuple[PlatformName, "re.Pattern", type[BaseDownloader]]]] = []

    @classmethod
    def register(
        cls, platform: PlatformName, url_pattern: str
    ) -> callable:
        """Register a downloader class for *platform*."""
        compiled = re.compile(url_pattern, re.IGNORECASE)

        def wrapper(downloader_cls: type[BaseDownloader]) -> type[BaseDownloader]:
            if not issubclass(downloader_cls, BaseDownloader):
                msg = f"{downloader_cls.__name__} must inherit from BaseDownloader"
                raise TypeError(msg)
            cls._entries.append((platform, compiled, downloader_cls))
            return downloader_cls

        return wrapper

    @classmethod
    def resolve(cls, url: str) -> type[BaseDownloader]:
        """Return the downloader class that matches *url*."""
        for _platform, pattern, downloader_cls in cls._entries:
            if pattern.search(url):
                return downloader_cls
        msg = f"No downloader found for URL: {url}"
        raise InvalidURLError(msg)

    @classmethod
    def list_platforms(cls) -> list[PlatformName]:
        """Return sorted platform identifiers."""
        return sorted(pid for pid, _, _ in cls._entries)
