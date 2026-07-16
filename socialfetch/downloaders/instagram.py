"""Instagram downloader implementation."""

import json
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
from socialfetch.downloaders.registry import DownloaderRegistry

logger = logging.getLogger(__name__)


@DownloaderRegistry.register("instagram", r"instagram[.]com/(?:p|reel|tv|stories)/")
class InstagramDownloader(BaseDownloader):
    """Downloader for Instagram content using yt-dlp backend.

    Supports:
    - Single image posts
    - Carousel (multi-image) posts
    - Video reels
    - IGTV
    - Stories (with cookie authentication)

    Usage::

        downloader = InstagramDownloader()
        result = await downloader.download(
            DownloadRequest(url="https://instagram.com/p/ABC123/")
        )
    """

    @property
    def platform(self) -> PlatformName:
        return "instagram"

    async def download(self, request: DownloadRequest) -> MediaInfo:
        """Download media from an Instagram URL.

        Args:
            request: Contains the URL and optional settings.

        Returns:
            MediaInfo with downloaded file paths and metadata.

        Raises:
            InvalidURLError: If the URL is not a valid Instagram post.
            MediaNotFoundError: If the content is unavailable.
            DownloadError: For other download failures.
        """
        shortcode = self._extract_shortcode(request.url)
        if not shortcode:
            msg = f"Could not extract shortcode from URL: {request.url}"
            raise InvalidURLError(msg)

        output_dir = request.output_dir or Path("downloads") / "instagram" / shortcode
        output_dir.mkdir(parents=True, exist_ok=True)

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
                    duration_seconds=info.get("duration"),
                    raw=info,
                ),
            )

        except yt_dlp.utils.DownloadError as e:
            error_text = str(e).lower()
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

    def _extract_shortcode(self, url: str) -> str | None:
        """Extract the Instagram shortcode from a URL."""
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
    ) -> dict:
        """Execute yt-dlp download and return extracted info."""
        ydl_opts: dict = {
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

        # Optional cookie file support
        cookie_file = request.cookies_file or request.extra.get("cookies_file")
        if cookie_file and os.path.exists(str(cookie_file)):
            ydl_opts["cookiefile"] = str(cookie_file)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                msg = "yt-dlp returned no info"
                raise DownloadError(msg)
            return info

    def _move_files(self, temp_dir: Path, output_dir: Path) -> list[Path]:
        """Move downloaded files from temp to permanent directory."""
        files: list[Path] = []
        valid_extensions = {".mp4", ".webm", ".mkv", ".jpg", ".jpeg", ".png", ".webp"}

        for fpath in temp_dir.iterdir():
            if fpath.suffix.lower() in valid_extensions:
                dest = output_dir / fpath.name
                shutil.move(str(fpath), str(dest))
                files.append(dest)

        return files

    def _detect_media_type(
        self, info: dict, files: list[Path]
    ) -> MediaType:
        """Determine the MediaType from yt-dlp info and downloaded files."""
        if info.get("is_live"):
            return MediaType.STORY

        # Check for carousel in info
        if info.get("entries") or info.get("playlist_count", 0) > 1:
            return MediaType.CAROUSEL

        has_video = any(f.suffix.lower() in {".mp4", ".webm", ".mkv"} for f in files)
        if has_video:
            # Reels are a specific type of video
            if "/reel/" in str(info.get("webpage_url", "")):
                return MediaType.REEL
            return MediaType.VIDEO

        if len(files) > 1:
            return MediaType.CAROUSEL

        return MediaType.PHOTO
