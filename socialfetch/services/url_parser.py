"""URL parsing and platform detection service."""

from dataclasses import dataclass

from socialfetch.core.errors import InvalidURLError
from socialfetch.core.interfaces import BaseDownloader
from socialfetch.downloaders.registry import DownloaderRegistry


@dataclass
class ParseResult:
    """Result of parsing a URL."""

    platform: str
    downloader_class: type[BaseDownloader]
    url: str
    identifier: str | None = None


class URLParser:
    """Detects the target platform from a URL using the downloader registry.

    Usage::

        result = URLParser.parse("https://instagram.com/p/ABC123/")
        # ParseResult(platform="instagram", downloader_class=InstagramDownloader, ...)
    """

    @staticmethod
    def parse(url: str) -> ParseResult:
        """Parse *url* and return a ``ParseResult`` with platform info.

        Raises ``InvalidURLError`` when no registered platform matches.
        """
        for platform, pattern, downloader_cls in DownloaderRegistry._entries:
            match = pattern.search(url)
            if match:
                identifier = match.group(1) if match.lastindex else None
                return ParseResult(
                    platform=platform,
                    downloader_class=downloader_cls,
                    url=url,
                    identifier=identifier,
                )
        msg = f"No platform matches URL: {url}"
        raise InvalidURLError(msg)

    @staticmethod
    def match(url: str) -> bool:
        """Return ``True`` if *url* matches any registered platform."""
        try:
            URLParser.parse(url)
            return True
        except InvalidURLError:
            return False
