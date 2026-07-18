"""Tests for the Spotify downloader."""
from pathlib import Path

import pytest

from socialfetch.core.errors import InvalidURLError
from socialfetch.core.models import DownloadRequest
from socialfetch.downloaders.spotify import SpotifyDownloader

_BASE = "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"


class TestSpotifyDownloader:
    @pytest.fixture
    def downloader(self) -> SpotifyDownloader:
        return SpotifyDownloader()

    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            (_BASE, "4cOdK2wGLETKBW3PvgPWqT"),
            (_BASE.replace("track", "album"), "4cOdK2wGLETKBW3PvgPWqT"),
            ("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
             "37i9dQZF1DXcBWIGoYBM5M"),
            ("https://open.spotify.com/episode/abc123", "abc123"),
            ("https://spotify.com/track/abc123", "abc123"),
            ("https://open.spotify.com/show/xyz789", "xyz789"),
        ],
    )
    def test_extract_id(
        self, downloader: SpotifyDownloader, url: str, expected: str
    ) -> None:
        assert downloader._extract_id(url) == expected

    @pytest.mark.parametrize(
        "bad_url",
        [
            "https://youtube.com/watch?v=abc",
            "https://instagram.com/p/abc",
            "https://open.spotify.com",
            "not-a-url",
            "",
        ],
    )
    async def test_invalid_urls(
        self, downloader: SpotifyDownloader, bad_url: str
    ) -> None:
        req = DownloadRequest(url=bad_url)
        with pytest.raises(InvalidURLError):
            await downloader.download(req)

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("Artist - Song", "🎵 Artist — Song"),
            ("NoDash", "🎵 NoDash"),
        ],
    )
    def test_format_caption(
        self, downloader: SpotifyDownloader, name: str, expected: str
    ) -> None:
        f = downloader._format_caption
        assert f(Path(f"/tmp/{name}.opus")) == expected

    def test_platform(self, downloader: SpotifyDownloader) -> None:
        assert downloader.platform == "spotify"
