"""YouTube downloader implementation using yt-dlp."""

import asyncio
import logging
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, cast

import yt_dlp

from socialfetch.config.settings import settings
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

YT_PATTERN = re.compile(
    r"https?://"
    r"(?:(?:www\.)?youtube\.com/(?:watch\?v=|shorts/|playlist\?list=|live/|embed/|v/))?"
    r"|https?://youtu\.be/"
)


@DownloaderRegistry.register(
    "youtube",
    r"(?:www\.)?youtu(?:be\.com|\.be)/(?:watch\?v=|shorts/|playlist\?list=|live/|embed/|v/|[\w-]{11})",
)
class YouTubeDownloader(BaseDownloader):
    """Downloader for YouTube content using yt-dlp.

    Supports:
    - Single videos
    - Shorts
    - Playlists (as CAROUSEL)
    - Live streams
    - Subtitles (optional)
    - Quality selection via request.extra["quality"]
    """

    @property
    def platform(self) -> PlatformName:
        return "youtube"

    async def download(self, request: DownloadRequest) -> MediaInfo:
        video_id = self._extract_video_id(request.url)
        if not video_id:
            msg = f"Could not extract video ID from URL: {request.url}"
            raise InvalidURLError(msg)

        output_dir = request.output_dir or Path("downloads") / "youtube" / video_id
        output_dir.mkdir(parents=True, exist_ok=True)

        temp_dir = Path(tempfile.mkdtemp(prefix="yt_"))
        try:
            info = await asyncio.to_thread(
                self._download_video, request.url, temp_dir, request
            )

            # Check for playlist
            entries = cast("list[dict[str, Any]]", info.get("entries"))
            if info.get("_type") == "playlist" and entries:
                return self._handle_playlist(
                    entries, info, video_id, request.url, output_dir, temp_dir, request
                )

            files = self._move_files(temp_dir, output_dir)
            if not files:
                msg = "No files downloaded from YouTube"
                raise DownloadError(msg)

            return self._build_media_info(
                info, files, video_id, request.url, MediaType.VIDEO
            )

        except yt_dlp.utils.DownloadError as e:
            error_text = str(e).lower()
            if "private" in error_text:
                raise MediaNotFoundError("Video is private or deleted") from e
            if "age" in error_text or "restricted" in error_text:
                msg = "Age-restricted video. Use cookies_file in DownloadRequest."
                raise DownloadError(msg) from e
            raise DownloadError(str(e)) from e
        except OSError as e:
            raise DownloadError(str(e)) from e
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _get_format(self, quality: str) -> str:
        """Map quality option to yt-dlp format string."""
        formats = {
            "audio-only": "bestaudio/best",
            "best+480": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "best+1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        }
        return formats.get(quality, "bestvideo+bestaudio/best")

    def _download_video(
        self, url: str, temp_dir: Path, request: DownloadRequest
    ) -> dict[str, object]:
        """Execute yt-dlp and return extracted info."""
        quality: str = request.extra.get("quality", "best")  # type: ignore[assignment]
        fmt = self._get_format(quality)

        ydl_opts: dict[str, object] = {
            "format": fmt,
            "outtmpl": str(temp_dir / "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "proxy": settings.proxy_url or "",
            "merge_output_format": "mp4",
        }

        # Auto-downgrade quality if file would exceed 45MB
        if quality == "best":
            try:
                peek_opts: dict[str, object] = {
                    "format": fmt,
                    "quiet": True,
                    "no_warnings": True,
                    "proxy": settings.proxy_url or "",
                }
                with yt_dlp.YoutubeDL(peek_opts) as ydl:
                    peek = ydl.extract_info(url, download=False)
                if peek:
                    est_mb: float = 0
                    for f in peek.get("formats") or []:
                        if f.get("filesize"):
                            est_mb += f["filesize"]
                        elif f.get("filesize_approx"):
                            est_mb += f["filesize_approx"]
                    est_mb = est_mb / (1024 * 1024)
                    if est_mb > 45:
                        logger.info("Estimated %sMB, downgrading to 480p", est_mb)
                        fmt = "bestvideo[height<=480]+bestaudio/best[height<=480]"
                        ydl_opts["format"] = fmt
            except Exception:
                pass

        # Audio-only postprocessing
        if quality == "audio-only":
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                }
            ]

        # Subtitles
        if request.extra.get("subtitles"):
            ydl_opts["writesubtitles"] = True
            ydl_opts["writeautomaticsub"] = True
            ydl_opts["subtitleslangs"] = ["en"]
            ydl_opts["subtitlesformat"] = "vtt"

        # Cookie file for age-restricted content
        if request.cookies_file and request.cookies_file.exists():
            ydl_opts["cookiefile"] = str(request.cookies_file)

        # ffmpeg check
        if quality != "best" and shutil.which("ffmpeg") is None:
            logger.warning("ffmpeg not found — video+audio merge may fail")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise DownloadError("yt-dlp returned no info")
            return info  # type: ignore[no-any-return,unused-ignore]

    def _handle_playlist(
        self,
        entries: list[Any],
        playlist_info: dict[str, Any],
        video_id: str,
        url: str,
        output_dir: Path,
        temp_dir: Path,
        request: DownloadRequest,
    ) -> MediaInfo:
        """Handle playlist downloads — return as CAROUSEL."""
        max_items: Any = request.extra.get("max_playlist", 10)
        files: list[Path] = []
        count = 0
        for entry in entries:
            if count >= max_items:
                break
            if entry and entry.get("id"):
                entry_url = f"https://www.youtube.com/watch?v={entry['id']}"
                try:
                    self._download_video(entry_url, temp_dir, request)  # noqa: F841
                    moved = self._move_files(temp_dir, output_dir)
                    files.extend(moved)
                except Exception as exc:
                    logger.debug("Skipping playlist entry %s: %s", entry.get("id"), exc)
                    continue

        caption = playlist_info.get("title") or ""
        author = playlist_info.get("uploader") or ""

        return MediaInfo(
            platform="youtube",
            media_type=MediaType.CAROUSEL,
            shortcode=video_id,
            url=url,
            files=files,
            caption=caption,
            author=author,
            metadata=MediaMetadata(
                views=0,
                likes=0,
                comments=0,
                duration_seconds=None,
                raw={"source": "youtube_playlist", "entries": len(entries)},
            ),
        )

    def _move_files(self, temp_dir: Path, output_dir: Path) -> list[Path]:
        """Move downloaded files to permanent directory."""
        files: list[Path] = []
        valid_extensions = {
            ".mp4",
            ".webm",
            ".mkv",
            ".avi",
            ".mp3",
            ".m4a",
            ".ogg",
            ".wav",
            ".vtt",
            ".srt",
            ".ass",
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }

        for fpath in temp_dir.iterdir():
            if fpath.suffix.lower() in valid_extensions:
                dest = output_dir / fpath.name
                if not dest.exists():
                    shutil.move(str(fpath), str(dest))
                files.append(dest)

        return files

    def _build_media_info(
        self,
        info: dict[str, Any],
        files: list[Path],
        video_id: str,
        url: str,
        media_type: MediaType = MediaType.VIDEO,
    ) -> MediaInfo:
        """Build MediaInfo from yt-dlp extracted data."""
        return MediaInfo(
            platform="youtube",
            media_type=media_type,
            shortcode=video_id,
            url=url,
            files=files,
            caption=info.get("title") or "",
            author=info.get("uploader") or "",
            metadata=MediaMetadata(
                likes=info.get("like_count", 0) or 0,
                comments=info.get("comment_count", 0) or 0,
                views=info.get("view_count", 0) or 0,
                duration_seconds=(
                    float(info["duration"]) if info.get("duration") else None
                ),
                raw={
                    "title": info.get("title"),
                    "description": info.get("description"),
                    "upload_date": info.get("upload_date"),
                    "channel_url": info.get("channel_url"),
                },
            ),
        )

    @staticmethod
    def _extract_video_id(url: str) -> str | None:
        """Extract YouTube video ID from various URL formats."""
        patterns = [
            r"v=([\w-]{11})",
            r"youtu\.be/([\w-]{11})",
            r"shorts/([\w-]{11})",
            r"live/([\w-]{11})",
            r"embed/([\w-]{11})",
            r"v/([\w-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
