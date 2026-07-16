"""Tests for the DownloaderRegistry."""

import re

import pytest

from socialfetch.core.errors import InvalidURLError
from socialfetch.core.interfaces import BaseDownloader
from socialfetch.core.models import DownloadRequest, MediaInfo
from socialfetch.downloaders.registry import DownloaderRegistry


class _DummyDl(BaseDownloader):
    @property
    def platform(self) -> str:
        return "dummy"

    async def download(self, request: DownloadRequest) -> MediaInfo:
        msg = "Not implemented in tests"
        raise NotImplementedError(msg)


class TestDownloaderRegistry:
    """Suite of unit tests for the registry pattern."""

    def test_register_and_resolve(self) -> None:
        DownloaderRegistry._entries.append(
            ("dummy", re.compile(r"mytest-app\.com/clip/"), _DummyDl),
        )
        cls = DownloaderRegistry.resolve("https://mytest-app.com/clip/123")
        assert cls is _DummyDl

    def test_register_via_decorator(self) -> None:
        @DownloaderRegistry.register("test-platform", r"my-test-platform\.io/(p|reel)/")
        class _TestDl(BaseDownloader):
            @property
            def platform(self) -> str:
                return "test-platform"

            async def download(self, request: DownloadRequest) -> MediaInfo:
                msg = "Not implemented"
                raise NotImplementedError(msg)

        cls = DownloaderRegistry.resolve("https://my-test-platform.io/p/ABC123/")
        assert cls is _TestDl

    def test_resolve_no_match_raises(self) -> None:
        with pytest.raises(InvalidURLError):
            DownloaderRegistry.resolve("https://unknown.example.com")

    def test_list_platforms(self) -> None:
        @DownloaderRegistry.register("test-alpha", r"test-alpha-app\.com")
        class _AlphaDl(BaseDownloader):
            @property
            def platform(self) -> str:
                return "test-alpha"

            async def download(self, request: DownloadRequest) -> MediaInfo:
                raise NotImplementedError

        @DownloaderRegistry.register("test-beta", r"test-beta-app\.com")
        class _BetaDl(BaseDownloader):
            @property
            def platform(self) -> str:
                return "test-beta"

            async def download(self, request: DownloadRequest) -> MediaInfo:
                raise NotImplementedError

        platforms = DownloaderRegistry.list_platforms()
        assert "test-alpha" in platforms
        assert "test-beta" in platforms
