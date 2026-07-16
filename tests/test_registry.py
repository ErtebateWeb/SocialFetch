"""Tests for the DownloaderRegistry."""

import pytest
from socialfetch.downloaders.registry import DownloaderRegistry
from socialfetch.core.interfaces import BaseDownloader
from socialfetch.core.errors import InvalidURLError
from socialfetch.core.models import DownloadRequest, MediaInfo


class DummyDownloader(BaseDownloader):
    """Minimal downloader used for registry tests."""

    @property
    def platform(self) -> str:
        return "dummy"

    async def download(self, request: DownloadRequest) -> MediaInfo:
        msg = "Not implemented in tests"
        raise NotImplementedError(msg)


class TestDownloaderRegistry:
    """Suite of unit tests for the registry pattern."""

    def setup_method(self) -> None:
        DownloaderRegistry._entries.clear()

    def test_register_and_resolve(self) -> None:
        @DownloaderRegistry.register("dummy", r"example\.com/test")
        class _(BaseDownloader):
            @property
            def platform(self) -> str:
                return "dummy"

            async def download(self, request: DownloadRequest) -> MediaInfo:
                msg = "Not implemented"
                raise NotImplementedError(msg)

        cls = DownloaderRegistry.resolve("https://example.com/test/123")
        assert cls is _

    def test_register_via_decorator(self) -> None:
        @DownloaderRegistry.register("instagram", r"instagram\.com/(p|reel|tv)/")
        class _(BaseDownloader):
            @property
            def platform(self) -> str:
                return "instagram"

            async def download(self, request: DownloadRequest) -> MediaInfo:
                msg = "Not implemented"
                raise NotImplementedError(msg)

        cls = DownloaderRegistry.resolve("https://instagram.com/p/ABC123/")
        assert cls is _

    def test_resolve_no_match_raises(self) -> None:
        with pytest.raises(InvalidURLError):
            DownloaderRegistry.resolve("https://unknown.example.com")

    def test_list_platforms(self) -> None:
        @DownloaderRegistry.register("alpha", r"alpha\.com")
        class _(BaseDownloader):
            @property
            def platform(self) -> str:
                return "alpha"

            async def download(self, request: DownloadRequest) -> MediaInfo:
                raise NotImplementedError

        @DownloaderRegistry.register("beta", r"beta\.com")
        class __(BaseDownloader):
            @property
            def platform(self) -> str:
                return "beta"

            async def download(self, request: DownloadRequest) -> MediaInfo:
                raise NotImplementedError

        assert DownloaderRegistry.list_platforms() == ["alpha", "beta"]
