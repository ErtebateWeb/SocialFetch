"""Spotify downloader using spotdl CLI."""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from socialfetch.config.settings import settings
from socialfetch.core.errors import DownloadError, InvalidURLError, MediaNotFoundError
from socialfetch.core.interfaces import BaseDownloader
from socialfetch.core.models import DownloadRequest, MediaInfo, MediaMetadata, MediaType
from socialfetch.downloaders.registry import DownloaderRegistry

if TYPE_CHECKING:
    from socialfetch.core.types import PlatformName

logger = logging.getLogger(__name__)

SPOTIFY_PATTERN = r"https?://(?:open\.)?spotify\.com/(?:track|album|playlist|episode|show)/[a-zA-Z0-9]+"
_TYPES: dict[str, MediaType] = {
    "track": MediaType.UNKNOWN,
    "album": MediaType.UNKNOWN,
    "playlist": MediaType.UNKNOWN,
    "episode": MediaType.UNKNOWN,
    "show": MediaType.UNKNOWN,
}


@DownloaderRegistry.register("spotify", SPOTIFY_PATTERN)
class SpotifyDownloader(BaseDownloader):
    @property
    def platform(self) -> PlatformName:
        return "spotify"

    async def download(self, request: DownloadRequest) -> MediaInfo:
        url = request.url.strip()
        if not re.search(SPOTIFY_PATTERN, url, re.IGNORECASE):
            msg = "Not a valid Spotify URL"
            raise InvalidURLError(msg)

        temp_dir = tempfile.mkdtemp(prefix="spotdl_")
        try:
            await self._download_audio(url, temp_dir)
            files = sorted(Path(temp_dir).iterdir())
            if not files:
                msg = "No audio downloaded"
                raise DownloadError(msg)
            return MediaInfo(
                platform=self.platform,
                media_type=MediaType.UNKNOWN,
                shortcode=self._extract_id(url),
                url=url,
                files=files,
                caption=self._format_caption(files[0]),
                author="",
                metadata=MediaMetadata(raw={"spotify_url": url}),
            )
        except (DownloadError, MediaNotFoundError):
            raise
        except Exception as exc:
            msg = f"Spotify download failed: {exc}"
            raise DownloadError(msg) from exc

    async def _download_audio(self, url: str, output_dir: str) -> None:
        """Run spotdl as subprocess. Uses HTTP proxy from settings if available."""
        http_proxy = None
        raw = settings.proxy_url
        if raw and ("socks5" not in raw):
            http_proxy = raw

        spotdl_bin = shutil.which("spotdl") or "/usr/local/lib/hermes-agent/venv/bin/spotdl"
        cmd = [
            spotdl_bin,
            url,
            "--output",
            f"{output_dir}/{{artists}} - {{title}}.{{output-ext}}",
            "--format",
            "opus",
            "--overwrite",
            "skip",
        ]
        if http_proxy:
            cmd.extend(["--proxy", http_proxy])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)

        if proc.returncode != 0:
            err = stderr.decode(errors="replace") or stdout.decode(errors="replace")
            if "Couldn't find" in err or "No results" in err:
                msg = "Track not found on Spotify"
                raise MediaNotFoundError(msg)
            msg = f"spotdl failed (exit={proc.returncode}): {err[:500]}"
            raise DownloadError(msg)

    @staticmethod
    def _extract_id(url: str) -> str:
        match = re.search(r"/(?:track|album|playlist|episode|show)/([a-zA-Z0-9]+)", url)
        return match.group(1) if match else "spotify"

    @staticmethod
    def _format_caption(file_path: Path) -> str:
        name = file_path.stem  # "Artist - Title"
        # spotdl outputs "Artist - Title.ext"
        parts = name.split(" - ", 1)
        if len(parts) == 2:
            return f"🎵 {parts[0]} — {parts[1]}"
        return f"🎵 {name}"


__all__ = ["SpotifyDownloader"]
