"""Tests for the DownloaderRegistry."""

from __future__ import annotations

from socialfetch.core.models import DownloadRequest, DownloadResult
from socialfetch.downloaders.base import BaseDownloader
from socialfetch.downloaders.registry import DownloaderRegistry


class FakeDownloader(BaseDownloader):
    """Test downloader that supports example.com URLs."""

    def supports(self, url: str) -> bool:
        return "example.com" in url

    def download(self, request: DownloadRequest) -> DownloadResult:
        return DownloadResult(success=True)


class AnotherFakeDownloader(BaseDownloader):
    """Test downloader that supports test.org URLs."""

    def supports(self, url: str) -> bool:
        return "test.org" in url

    def download(self, request: DownloadRequest) -> DownloadResult:
        return DownloadResult(success=True)


def test_register_downloader() -> None:
    registry = DownloaderRegistry()
    registry.register(FakeDownloader)
    assert FakeDownloader in registry.all_downloaders()


def test_unregister_downloader() -> None:
    registry = DownloaderRegistry()
    registry.register(FakeDownloader)
    registry.unregister(FakeDownloader)
    assert FakeDownloader not in registry.all_downloaders()


def test_get_downloader_found() -> None:
    registry = DownloaderRegistry()
    registry.register(FakeDownloader)
    result = registry.get_downloader("https://example.com/video.mp4")
    assert result is FakeDownloader


def test_get_downloader_not_found() -> None:
    registry = DownloaderRegistry()
    registry.register(FakeDownloader)
    result = registry.get_downloader("https://unknown.com/video.mp4")
    assert result is None


def test_all_downloaders_empty() -> None:
    registry = DownloaderRegistry()
    assert registry.all_downloaders() == []


def test_all_downloaders_multiple() -> None:
    registry = DownloaderRegistry()
    registry.register(FakeDownloader)
    registry.register(AnotherFakeDownloader)
    downloaders = registry.all_downloaders()
    assert len(downloaders) == 2
    assert FakeDownloader in downloaders
    assert AnotherFakeDownloader in downloaders


def test_register_duplicate() -> None:
    registry = DownloaderRegistry()
    registry.register(FakeDownloader)
    registry.register(FakeDownloader)
    assert len(registry.all_downloaders()) == 1


def test_unregister_nonexistent_raises() -> None:
    registry = DownloaderRegistry()
    try:
        registry.unregister(FakeDownloader)
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass
