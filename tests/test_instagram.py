"""Tests for the Instagram downloader."""

from pathlib import Path

import pytest

from socialfetch.core.errors import InvalidURLError
from socialfetch.core.models import DownloadRequest, MediaType
from socialfetch.downloaders.instagram import InstagramDownloader


class TestInstagramShortcodeExtraction:
    """Verify URL parsing works for various Instagram URL formats."""

    def setup_method(self) -> None:
        self.downloader = InstagramDownloader()

    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://instagram.com/p/ABC123/", "ABC123"),
            ("https://www.instagram.com/p/ABC123/", "ABC123"),
            ("https://instagram.com/reel/DEF456/", "DEF456"),
            ("https://www.instagram.com/reel/DEF456/", "DEF456"),
            ("https://instagram.com/tv/GHI789/", "GHI789"),
            ("https://instagram.com/p/ABC123/?utm_source=share", "ABC123"),
            ("https://instagr.am/p/ABC123/", None),  # short domain not supported
        ],
    )
    def test_extract_shortcode_valid(self, url: str, expected: str | None) -> None:
        result = self.downloader._extract_shortcode(url)
        assert result == expected

    @pytest.mark.parametrize(
        "url",
        [
            "https://youtube.com/watch?v=123",
            "https://google.com",
            "not-a-url",
            "",
        ],
    )
    def test_extract_shortcode_invalid(self, url: str) -> None:
        assert self.downloader._extract_shortcode(url) is None

    def test_download_invalid_url_raises(self) -> None:
        """download() should raise InvalidURLError for bad URLs."""
        with pytest.raises(InvalidURLError):
            request = DownloadRequest(url="https://example.com/not-instagram")
            # Create event loop for async call
            import asyncio
            asyncio.run(self.downloader.download(request))


class TestInstagramMediaTypeDetection:
    """Verify media type classification."""

    def setup_method(self) -> None:
        self.downloader = InstagramDownloader()

    def test_photo_detected(self) -> None:
        info = {"is_live": False}
        files = [Path("photo.jpg")]
        result = self.downloader._detect_media_type(info, files)
        assert result == MediaType.PHOTO

    def test_video_detected(self) -> None:
        info = {"is_live": False}
        files = [Path("video.mp4")]
        result = self.downloader._detect_media_type(info, files)
        assert result == MediaType.VIDEO

    def test_reel_detected(self) -> None:
        info = {"is_live": False, "webpage_url": "https://instagram.com/reel/ABC/"}
        files = [Path("reel.mp4")]
        result = self.downloader._detect_media_type(info, files)
        assert result == MediaType.REEL

    def test_carousel_detected(self) -> None:
        info = {"is_live": False}
        files = [Path("img1.jpg"), Path("img2.jpg")]
        result = self.downloader._detect_media_type(info, files)
        assert result == MediaType.CAROUSEL
