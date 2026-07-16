"""Core data models for SocialFetch."""

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

from socialfetch.core.types import JSONDict, PlatformName


class MediaType(Enum):
    """The high-level category of downloaded media."""

    PHOTO = auto()
    VIDEO = auto()
    CAROUSEL = auto()
    STORY = auto()
    REEL = auto()
    UNKNOWN = auto()


@dataclass
class MediaMetadata:
    """Normalised representation of platform-specific metadata."""

    likes: int = 0
    comments: int = 0
    views: int = 0
    duration_seconds: float | None = None
    resolution: tuple[int, int] | None = None
    raw: JSONDict = field(default_factory=dict)


@dataclass
class MediaInfo:
    """Canonical download result returned by every downloader."""

    platform: PlatformName
    media_type: MediaType
    shortcode: str
    url: str
    files: list[Path] = field(default_factory=list)
    caption: str = ""
    author: str = ""
    metadata: MediaMetadata = field(default_factory=MediaMetadata)


@dataclass
class DownloadRequest:
    """Encapsulates a request to download media from a platform URL."""

    url: str
    platform: PlatformName = ""
    output_dir: Path | None = None
    cookies_file: Path | None = None
    extra: JSONDict = field(default_factory=dict)
