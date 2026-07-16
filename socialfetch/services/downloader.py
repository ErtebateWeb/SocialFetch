"""Download orchestrator — the main entry point for all downloads."""

from dataclasses import dataclass, field

from socialfetch.core.errors import SocialFetchError
from socialfetch.core.models import DownloadRequest, MediaInfo, MediaType
from socialfetch.services.url_parser import URLParser
from socialfetch.storage.interfaces import StorageBackend
from socialfetch.storage.local import LocalStorage


@dataclass
class DownloadResult:
    """Final result returned by the orchestrator after download + save."""

    url: str
    platform: str
    media: MediaInfo
    saved_paths: list[str] = field(default_factory=list)
    error: str | None = None


class DownloadOrchestrator:
    """Coordinates URL detection, downloading, and storage.

    Usage::

        orch = DownloadOrchestrator()
        result = await orch.download("https://instagram.com/p/ABC123/")
    """

    def __init__(self, storage: StorageBackend | None = None) -> None:
        self.storage = storage or LocalStorage()

    async def download(
        self,
        url: str,
        cookies_file: str | None = None,
        output_dir: str | None = None,
    ) -> DownloadResult:
        """Detect platform, download, save, and return the result."""
        try:
            parsed = URLParser.parse(url)
            downloader_type = parsed.downloader_class
            downloader = downloader_type()

            request = DownloadRequest(url=url)
            if cookies_file:
                request.extra["cookies_file"] = cookies_file
            if output_dir:
                request.extra["output_dir"] = output_dir

            media = await downloader.download(request)
            saved = self.storage.save(media)

            return DownloadResult(
                url=url,
                platform=parsed.platform,
                media=media,
                saved_paths=[str(p) for p in saved],
            )

        except SocialFetchError as e:
            return DownloadResult(
                url=url,
                platform="unknown",
                media=MediaInfo(
                    platform="", media_type=MediaType.UNKNOWN, shortcode="", url=""
                ),
                saved_paths=[],
                error=str(e),
            )
