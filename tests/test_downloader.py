"""Tests for the download orchestrator."""

import pytest

from socialfetch.core.models import MediaInfo
from socialfetch.services.downloader import DownloadOrchestrator, DownloadResult


class TestDownloadOrchestrator:
    """Verify orchestrator coordinates URL parsing, download, and storage."""

    @pytest.mark.asyncio
    async def test_download_invalid_url(self) -> None:
        orch = DownloadOrchestrator()
        result = await orch.download("https://unknown.example.com/xyz")
        assert isinstance(result, DownloadResult)
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_download_instagram_graceful_error(self) -> None:
        orch = DownloadOrchestrator()
        result = await orch.download("https://instagram.com/p/SHORTCODE/")
        assert isinstance(result, DownloadResult)
        assert result.url is not None

    def test_download_result_dataclass(self) -> None:
        result = DownloadResult(
            url="https://example.com",
            platform="test",
            media=MediaInfo(platform="test", media_type="", shortcode="", url=""),
            saved_paths=["/tmp/file.jpg"],
        )
        assert result.url == "https://example.com"
        assert result.platform == "test"
        assert len(result.saved_paths) == 1
        assert result.error is None

    @pytest.mark.asyncio
    async def test_orchestrator_invalid_platform(self) -> None:
        orch = DownloadOrchestrator()
        result = await orch.download("https://not-a-real-platform.com/video")
        assert isinstance(result, DownloadResult)
        assert result.error is not None
