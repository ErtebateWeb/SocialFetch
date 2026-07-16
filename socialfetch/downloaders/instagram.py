"""Instagram downloader implementation."""
import logging
import os
import shutil
import tempfile
from pathlib import Path

import yt_dlp

from socialfetch.core.errors import DownloadError, InvalidURLError, MediaNotFoundError
from socialfetch.core.interfaces import BaseDownloader
from socialfetch.core.models import (
    DownloadRequest,
    MediaInfo,
    MediaMetadata,
    MediaType,
)
from socialfetch.core.types import PlatformName
from socialfetch.downloaders.instagram_api import InstagramAPIDownloader
from socialfetch.downloaders.instagram_photo import resolve_and_download_photos
from socialfetch.downloaders.registry import DownloaderRegistry

logger = logging.getLogger(__name__)

# Default cookie file path
COOKIE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "instagram_cookies.txt",
)
# Default WARP SOCKS5 proxy
WARP_PROXY = "socks5h://127.0.0.1:40000"


@DownloaderRegistry.register(
    "instagram", r"(?:www\.)?instagram[.]com/(?:p|reel|tv|stories)/"
)
class InstagramDownloader(BaseDownloader):
    """Downloader for Instagram content using yt-dlp + API + photo fallback.

    Priority:
    1. Mobile API (if cookies available) — full carousel, all images
    2. yt-dlp — video/reel downloads
    3. Embed page — carousel images (fallback, may be partial)
    4. oEmbed — single image fallback
    """

    def __init__(self):
        self._api: InstagramAPIDownloader | None = None

    @property
    def platform(self) -> PlatformName:
        return "instagram"

    def _get_api(self) -> InstagramAPIDownloader:
        if self._api is None:
            self._api = InstagramAPIDownloader(
                cookie_path=COOKIE_FILE,
                proxy=WARP_PROXY,
            )
        return self._api

    async def download(self, request: DownloadRequest) -> MediaInfo:
        shortcode = self._extract_shortcode(request.url)
        if not shortcode:
            msg = f"Could not extract shortcode from URL: {request.url}"
            raise InvalidURLError(msg)

        output_dir = request.output_dir or Path("downloads") / "instagram" / shortcode
        output_dir.mkdir(parents=True, exist_ok=True)

        # Priority 1: Mobile API (with cookies)
        api = self._get_api()
        if api.has_cookies:
            result = api.download_media(shortcode, output_dir)
            if result:
                files: list[Path] = result["files"]  # type: ignore[assignment]
                if files:
                    is_carousel: bool = result["media_type"] == "carousel"  # type: ignore[comparison-overlap]
                    is_video: bool = result["is_video"]  # type: ignore[assignment]
                    media_type = (
                        MediaType.CAROUSEL
                        if is_carousel
                        else MediaType.REEL
                        if is_video and "/reel/" in request.url
                        else MediaType.VIDEO if is_video else MediaType.PHOTO
                    )
                    return MediaInfo(
                        platform="instagram",
                        media_type=media_type,
                        shortcode=shortcode,
                        url=request.url,
                        files=files,
                        caption=result.get("caption") or "",
                        author=result.get("author") or "",
                        metadata=MediaMetadata(
                            likes=result.get("likes", 0),
                            comments=result.get("comments", 0),
                            views=0,
                            duration_seconds=None,
                            raw={"source": "instagram_api"},
                        ),
                    )

        # Priority 2: yt-dlp for video/reel
        temp_dir = Path(tempfile.mkdtemp(prefix="ig_"))
        try:
            info = self._download_with_ytdlp(request.url, shortcode, temp_dir, request)
            files = self._move_files(temp_dir, output_dir)
            media_type = self._detect_media_type(info, files)
            return MediaInfo(
                platform="instagram",
                media_type=media_type,
                shortcode=shortcode,
                url=request.url,
                files=files,
                caption=info.get("description") or "",
                author=info.get("uploader") or "",
                metadata=MediaMetadata(
                    likes=info.get("like_count", 0),
                    comments=info.get("comment_count", 0),
                    views=info.get("view_count", 0),
                    duration_seconds=(
                        float(info["duration"]) if info.get("duration") else None
                    ),
                    raw=info,
                ),
            )
        except yt_dlp.utils.DownloadError as e:
            error_text = str(e).lower()
            if "no video formats" in error_text:
                return self._download_photo_fallback(
                    request.url, shortcode, output_dir, e
                )
            if "private" in error_text or "not found" in error_text:
                msg = f"Content not found or private: {e}"
                raise MediaNotFoundError(msg) from e
            msg = f"Instagram download failed: {e}"
            raise DownloadError(msg) from e
        except Exception as e:
            msg = f"Unexpected download error: {e}"
            raise DownloadError(msg) from e
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _download_photo_fallback(
        self,
        url: str,
        shortcode: str,
        output_dir: Path,
        cause: Exception,
    ) -> MediaInfo:
        files, meta = resolve_and_download_photos(url, output_dir, shortcode)
        if not files:
            msg = (
                "این پست فقط عکس دارد و دانلود تصویر ناموفق بود. "
                "ممکن است محدودیت IP یا دیوار ورود اینستاگرام باشد."
            )
            raise MediaNotFoundError(msg) from cause

        media_type = MediaType.CAROUSEL if len(files) > 1 else MediaType.PHOTO
        return MediaInfo(
            platform="instagram",
            media_type=media_type,
            shortcode=shortcode,
            url=url,
            files=files,
            caption=meta.get("caption") or "",
            author=meta.get("author") or "",
            metadata=MediaMetadata(
                likes=0,
                comments=0,
                views=0,
                duration_seconds=None,
                raw={"source": "instagram_photo_fallback", **meta},
            ),
        )

    def _extract_shortcode(self, url: str) -> str | None:
        import re

        patterns = [
            r"instagram[.]com/(?:p|reel|tv)/([A-Za-z0-9_-]+)",
            r"instagram[.]com/stories/([A-Za-z0-9_.]+)/(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1) or match.group(2)
        return None

    def _download_with_ytdlp(
        self,
        url: str,
        shortcode: str,
        temp_dir: Path,
        request: DownloadRequest,
    ) -> dict[str, object]:
        ydl_opts: dict[str, object] = {
            "outtmpl": str(temp_dir / "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "writeinfojson": True,
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        }

        # Use cookies if available
        cookie_file = request.cookies_file or request.extra.get("cookies_file")
        if cookie_file and os.path.exists(str(cookie_file)):
            ydl_opts["cookiefile"] = str(cookie_file)
        elif os.path.exists(COOKIE_FILE):
            ydl_opts["cookiefile"] = COOKIE_FILE

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                msg = "yt-dlp returned no info"
                raise DownloadError(msg)
            return info

    def _move_files(self, temp_dir: Path, output_dir: Path) -> list[Path]:
        files: list[Path] = []
        valid_extensions = {".mp4", ".webm", ".mkv", ".jpg", ".jpeg", ".png", ".webp"}

        for fpath in temp_dir.iterdir():
            if fpath.suffix.lower() in valid_extensions:
                dest = output_dir / fpath.name
                shutil.move(str(fpath), str(dest))
                files.append(dest)

        return files

    def _detect_media_type(self, info: dict, files: list[Path]) -> MediaType:
        if info.get("is_live"):
            return MediaType.STORY

        if info.get("entries") or info.get("playlist_count", 0) > 1:
            return MediaType.CAROUSEL

        has_video = any(f.suffix.lower() in {".mp4", ".webm", ".mkv"} for f in files)
        if has_video:
            if "/reel/" in str(info.get("webpage_url", "")):
                return MediaType.REEL
            return MediaType.VIDEO

        if len(files) > 1:
            return MediaType.CAROUSEL

        return MediaType.PHOTO
