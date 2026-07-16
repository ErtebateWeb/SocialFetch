"""Unit tests for Instagram photo fallback helpers (ADR 0013)."""

import json
from pathlib import Path
from typing import Any

import pytest

from socialfetch.downloaders import instagram_photo as photo


class TestParsers:
    def test_parse_oembed_image_urls(self) -> None:
        data = {
            "thumbnail_url": "https://cdn.example/a.jpg",
            "author_name": "alice",
            "title": "hello",
        }
        assert photo.parse_oembed_image_urls(data) == ["https://cdn.example/a.jpg"]
        assert photo.parse_oembed_image_urls({}) == []

    def test_parse_og_image_urls(self) -> None:
        html = """
        <html><head>
        <meta property="og:image" content="https://cdn.example/og.jpg" />
        </head></html>
        """
        assert photo.parse_og_image_urls(html) == ["https://cdn.example/og.jpg"]

    def test_parse_display_urls_unescapes(self) -> None:
        html = r'{"display_url":"https://cdn.example/x.jpg?a=1\u0026b=2"}'
        urls = photo.parse_display_urls(html)
        assert len(urls) == 1
        assert "a=1&b=2" in urls[0]


class TestResolveImageUrls:
    def test_oembed_first(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        def fake_fetch_text(
            url: str, headers: dict[str, str] | None = None, timeout: float = 15.0
        ) -> str:
            if "oembed" in url:
                return json.dumps(
                    {
                        "thumbnail_url": "https://cdn.example/thumb.jpg",
                        "author_name": "bob",
                        "title": "caption text",
                    }
                )
            raise AssertionError("HTML should not be fetched when oEmbed works")

        monkeypatch.setattr(photo, "fetch_text", fake_fetch_text)
        urls, meta = photo.resolve_image_urls("https://www.instagram.com/p/ABC/")
        assert urls == ["https://cdn.example/thumb.jpg"]
        assert meta["author"] == "bob"
        assert meta["caption"] == "caption text"

    def test_fallback_to_og_image(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_fetch_text(
            url: str, headers: dict[str, str] | None = None, timeout: float = 15.0
        ) -> str:
            if "oembed" in url:
                raise photo.urllib.error.URLError("oembed down")
            return '<meta property="og:image" content="https://cdn.example/og2.jpg" />'

        monkeypatch.setattr(photo, "fetch_text", fake_fetch_text)
        urls, meta = photo.resolve_image_urls("https://www.instagram.com/p/ABC/")
        assert urls == ["https://cdn.example/og2.jpg"]
        assert meta == {}


class TestDownloadImages:
    def test_download_images_writes_files(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        jpeg = b"\xff\xd8\xff" + b"fakejpeg"

        def fake_fetch_bytes(
            url: str,
            headers: dict[str, str] | None = None,
            referer: str | None = None,
            timeout: float = 20.0,
        ) -> tuple[bytes, str]:
            return jpeg, "image/jpeg"

        monkeypatch.setattr(photo, "fetch_bytes", fake_fetch_bytes)
        paths = photo.download_images(["https://cdn.example/a.jpg"], tmp_path, "SHORT")
        assert len(paths) == 1
        assert paths[0].name == "SHORT_0.jpg"
        assert paths[0].read_bytes() == jpeg


class TestPhotoFallbackIntegration:
    @pytest.mark.asyncio
    async def test_downloader_uses_photo_fallback(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from socialfetch.core.models import DownloadRequest, MediaType
        from socialfetch.downloaders.instagram import InstagramDownloader

        def boom(*args: Any, **kwargs: Any) -> dict[str, object]:
            import yt_dlp

            raise yt_dlp.utils.DownloadError(
                "ERROR: [Instagram] X: No video formats found!"
            )

        def fake_resolve(
            post_url: str, dest_dir: Path, shortcode: str
        ) -> tuple[list[Path], dict[str, str]]:
            path = dest_dir / f"{shortcode}_0.jpg"
            path.write_bytes(b"\xff\xd8\xffdata")
            return [path], {"author": "user1", "caption": "cap"}

        monkeypatch.setattr(InstagramDownloader, "_download_with_ytdlp", boom)
        monkeypatch.setattr(
            "socialfetch.downloaders.instagram.resolve_and_download_photos",
            fake_resolve,
        )

        dl = InstagramDownloader()
        result = await dl.download(
            DownloadRequest(
                url="https://www.instagram.com/p/AbC123xy/",
                output_dir=tmp_path,
            )
        )
        assert result.media_type == MediaType.PHOTO
        assert result.author == "user1"
        assert result.caption == "cap"
        assert len(result.files) == 1
