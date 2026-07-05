"""Abstract base class for downloaders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from socialfetch.core.models import DownloadRequest, DownloadResult


class BaseDownloader(ABC):
    """Abstract base class that all downloaders must implement."""

    @abstractmethod
    def supports(self, url: str) -> bool:
        """Check if this downloader can handle the given URL."""

    @abstractmethod
    def download(self, request: DownloadRequest) -> DownloadResult:
        """Download media from the given URL."""
