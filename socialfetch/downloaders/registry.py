"""Registry for managing downloader implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from socialfetch.downloaders.base import BaseDownloader


class DownloaderRegistry:
    """Manages registration and lookup of downloader classes.

    The registry stores downloader classes (not instances) and provides
    methods to find the appropriate downloader for a given URL.
    """

    def __init__(self) -> None:
        self._downloaders: list[type[BaseDownloader]] = []

    def register(self, downloader: type[BaseDownloader]) -> None:
        """Register a downloader class."""
        if downloader not in self._downloaders:
            self._downloaders.append(downloader)

    def unregister(self, downloader: type[BaseDownloader]) -> None:
        """Unregister a downloader class."""
        self._downloaders.remove(downloader)

    def get_downloader(self, url: str) -> type[BaseDownloader] | None:
        """Find the first registered downloader that supports the URL."""
        for downloader in self._downloaders:
            instance = downloader()
            if instance.supports(url):
                return downloader
        return None

    def all_downloaders(self) -> list[type[BaseDownloader]]:
        """Return all registered downloader classes."""
        return list(self._downloaders)
