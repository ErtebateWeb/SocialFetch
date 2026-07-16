"""Unit tests for Instagram photo fallback helpers (ADR 0013 + carousel)."""

import json
from pathlib import Path
from typing import Any

import pytest

from socialfetch.downloaders import instagram_photo as photo

# --- Embed HTML fixture for carousel (3 images) ---
CAROUSEL_EMBED_HTML = """<html><body>
<img src="https://scontent-prg1-1.cdninstagram.com/v/t51.82787-19/448484964_profile_pic_n.jpg"/>
<img src="https://scontent-prg1-1.cdninstagram.com/v/t51.82787-19/448484964_profile_pic_n.jpg"/>
<img src="https://scontent-prg1-1.cdninstagram.com/v/t51.82787-15/747099071_18449479354143527_4879027591393916808_n.jpg?stp=dst-jpg_e35_tt6&_nc_cat=107"/>
<img src="https://scontent-prg1-1.cdninstagram.com/v/t51.82787-15/747324722_18449843065143527_5432983132883574853_n.jpg?stp=dst-jpg_e35_tt6&_nc_cat=106"/>
<img src="https://scontent-prg1-1.cdninstagram.com/v/t51.82787-15/747439930_18449664532143527_3047040225247893622_n.jpg?stp=dst-jpg_e15_tt6&_nc_cat=109"/>
</body></html>"""

SINGLE_EMBED_HTML = """<html><body>
<img src="https://scontent-prg1-1.cdninstagram.com/v/t51.82787-19/448484964_profile_pic_n.jpg"/>
<img src="https://scontent-prg1-1.cdninstagram.com/v/t51.82787-15/post_image_n.jpg?stp=dst-jpg"/>
</body></html>"""


class TestEmbedParser:
    def test_carousel_returns_post_images(self) -> None:
        urls = photo._parse_embed_image_urls(CAROUSEL_EMBED_HTML)
        # Should skip profile pic (appears 2x), return 3 carousel images
        assert len(urls) == 3
        assert "747099071" in urls[0]
        assert "747324722" in urls[1]
        assert "747439930" in urls[2]

    def test_single_image(self) -> None:
        urls = photo._parse_embed_image_urls(SINGLE_EMBED_HTML)
        # Profile pic (path /v/t51.82787-19/) skipped, only post image remains
        assert len(urls) == 1
        assert "post_image_n.jpg" in urls[0]

    def test_empty_html(self) -> None:
        urls = photo._parse_embed_image_urls("<html></html>")
        assert urls == []


class TestResolveCarousel:
    def test_uses_embed_for_carousel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_fetch_text(
            url: str, headers: dict[str, str] | None = None, timeout: float = 15.0
        ) -> str:
            if "oembed" in url:
                return json.dumps({"thumbnail_url": "https://cdn.example/thumb.jpg"})
            return ""

        def fake_fetch_embed(url: str) -> str:
            return CAROUSEL_EMBED_HTML

        monkeypatch.setattr(photo, "fetch_text", fake_fetch_text)
        monkeypatch.setattr(photo, "_fetch_embed_page", fake_fetch_embed)
        urls, meta = photo.resolve_image_urls("https://www.instagram.com/p/ABC/")
        assert len(urls) == 3  # 3 carousel images from embed
        assert "author" not in meta

    def test_fallback_to_oembed_thumbnail(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_fetch_text(
            url: str, headers: dict[str, str] | None = None, timeout: float = 15.0
        ) -> str:
            if "oembed" in url:
                return json.dumps(
                    {
                        "thumbnail_url": "https://cdn.example/thumb.jpg",
                        "author_name": "alice",
                    }
                )
            return ""

        def fake_fetch_embed(url: str) -> str:
            return "<html></html>"

        monkeypatch.setattr(photo, "fetch_text", fake_fetch_text)
        monkeypatch.setattr(photo, "_fetch_embed_page", fake_fetch_embed)
        urls, meta = photo.resolve_image_urls("https://www.instagram.com/p/ABC/")
        assert urls == ["https://cdn.example/thumb.jpg"]
        assert meta["author"] == "alice"


class TestParsers:
    def test_parse_oembed_metadata(self) -> None:
        data = {
            "thumbnail_url": "https://cdn.example/a.jpg",
            "author_name": "alice",
            "title": "hello",
        }
        meta = photo.parse_oembed_metadata(data)
        assert meta["author"] == "alice"
        assert meta["caption"] == "hello"

    def test_parse_display_urls_unescapes(self) -> None:
        val = photo._unescape_url(r"https://cdn.example/x.jpg?a=1\u0026b=2")
        assert "a=1&b=2" in val


class TestDownloadImages:
    def test_download_writes_files(
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
        paths = photo.download_images(
            [
                "https://cdn.example/img1.jpg",
                "https://cdn.example/img2.jpg",
            ],
            tmp_path,
            "SHORT",
        )
        assert len(paths) == 2
        assert paths[0].name == "SHORT_0.jpg"
        assert paths[1].name == "SHORT_1.jpg"


class TestCarouselIntegration:
    @pytest.mark.asyncio
    async def test_downloader_returns_all_carousel_images(
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
            saved = []
            for i in range(3):
                path = dest_dir / f"{shortcode}_{i}.jpg"
                path.write_bytes(b"\xff\xd8\xffdata")
                saved.append(path)
            return saved, {"author": "user1", "caption": "carousel post"}

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
        assert result.media_type == MediaType.CAROUSEL
        assert len(result.files) == 3
        assert result.author == "user1"
