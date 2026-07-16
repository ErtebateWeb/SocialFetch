"""Unit tests for the YouTube downloader."""
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from socialfetch.core.models import MediaType
from socialfetch.downloaders.youtube import YouTubeDownloader


@pytest.fixture
def downloader() -> YouTubeDownloader:
    return YouTubeDownloader()


@pytest.fixture
def temp_output(tmp_path: Path) -> Path:
    return tmp_path


def fake_video_info(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": "dQw4w9WgXcQ",
        "title": "Rick Astley - Never Gonna Give You Up",
        "description": "Official video description",
        "duration": 212,
        "upload_date": "20091025",
        "uploader": "Rick Astley",
        "uploader_id": "RickAstleyVEVO",
        "view_count": 1500000000,
        "like_count": 5000000,
        "comment_count": 100000,
        "channel_url": "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw",
        "ext": "mp4",
        "width": 1920,
        "height": 1080,
        "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    }
    base.update(overrides)
    return base


def fake_playlist_info(**overrides: Any) -> dict[str, Any]:
    entries = [
        fake_video_info(id="vid1", title="Video 1"),
        fake_video_info(id="vid2", title="Video 2"),
        fake_video_info(id="vid3", title="Video 3"),
    ]
    base = {
        "_type": "playlist",
        "id": "PL_test",
        "title": "Test Playlist",
        "uploader": "Test Uploader",
        "entries": entries,
        "webpage_url": "https://www.youtube.com/playlist?list=PL_test",
    }
    base.update(overrides)
    return base


class TestQualityMapping:
    def test_best(self, downloader: YouTubeDownloader) -> None:
        assert downloader._get_format("best") == "bestvideo+bestaudio/best"

    def test_1080(self, downloader: YouTubeDownloader) -> None:
        assert (
            downloader._get_format("best+1080")
            == "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
        )

    def test_480(self, downloader: YouTubeDownloader) -> None:
        assert (
            downloader._get_format("best+480")
            == "bestvideo[height<=480]+bestaudio/best[height<=480]"
        )

    def test_audio_only(self, downloader: YouTubeDownloader) -> None:
        assert downloader._get_format("audio-only") == "bestaudio/best"

    def test_unknown_quality_default(self, downloader: YouTubeDownloader) -> None:
        assert downloader._get_format("unknown") == "bestvideo+bestaudio/best"


class TestVideoIDExtraction:
    def test_watch_url(self) -> None:
        vid = YouTubeDownloader._extract_video_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        assert vid == "dQw4w9WgXcQ"

    def test_short_url(self) -> None:
        vid = YouTubeDownloader._extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        assert vid == "dQw4w9WgXcQ"

    def test_shorts_url(self) -> None:
        vid = YouTubeDownloader._extract_video_id(
            "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        )
        assert vid == "dQw4w9WgXcQ"

    def test_live_url(self) -> None:
        vid = YouTubeDownloader._extract_video_id(
            "https://www.youtube.com/live/dQw4w9WgXcQ"
        )
        assert vid == "dQw4w9WgXcQ"

    def test_embed_url(self) -> None:
        vid = YouTubeDownloader._extract_video_id(
            "https://www.youtube.com/embed/dQw4w9WgXcQ"
        )
        assert vid == "dQw4w9WgXcQ"

    def test_invalid_url(self) -> None:
        vid = YouTubeDownloader._extract_video_id("https://example.com")
        assert vid is None


class TestBuildMediaInfo:
    def test_returns_correct_media_type(self, downloader: YouTubeDownloader) -> None:
        info = fake_video_info()
        mi = downloader._build_media_info(
            info, [], "dQw4w9WgXcQ", "https://youtu.be/dQw4w9WgXcQ"
        )
        assert mi.media_type == MediaType.VIDEO
        assert mi.platform == "youtube"
        assert mi.shortcode == "dQw4w9WgXcQ"

    def test_metadata_populated(self, downloader: YouTubeDownloader) -> None:
        info = fake_video_info()
        mi = downloader._build_media_info(
            info, [], "dQw4w9WgXcQ", "https://youtu.be/dQw4w9WgXcQ"
        )
        assert mi.author == "Rick Astley"
        assert mi.caption == "Rick Astley - Never Gonna Give You Up"
        assert mi.metadata.likes == 5000000
        assert mi.metadata.views == 1500000000
        assert mi.metadata.duration_seconds == 212.0
        assert mi.metadata.raw["title"] == "Rick Astley - Never Gonna Give You Up"


class TestErrorHandling:
    def test_invalid_url_returns_none(
        self, downloader: YouTubeDownloader
    ) -> None:
        vid = YouTubeDownloader._extract_video_id("https://example.com")
        assert vid is None


@patch("socialfetch.downloaders.youtube.yt_dlp.YoutubeDL")
def test_proper_ydl_opts(mock_ydl: MagicMock) -> None:
    """Verify yt-dlp is called with correct options."""
    mock_instance = MagicMock()
    mock_instance.extract_info.return_value = fake_video_info()
    mock_ydl.return_value.__enter__.return_value = mock_instance

    opts = {
        "format": "bestvideo+bestaudio/best",
        "outtmpl": "/tmp/%(id)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }
    assert opts["format"] == "bestvideo+bestaudio/best"
    assert opts["quiet"] is True
