"""Data models for SocialFetch."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class MediaType(Enum):
    """Supported media types."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"


@dataclass
class DownloadRequest:
    """Represents a request to download media from a URL."""

    url: str
    media_type: MediaType | None = None
    filename: str | None = None


@dataclass
class DownloadedMedia:
    """Represents a successfully downloaded media file."""

    url: str
    media_type: MediaType
    file_path: Path
    filename: str
    size: int | None = None


@dataclass
class DownloadResult:
    """Result of a download operation."""

    success: bool
    media: DownloadedMedia | None = None
    error: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
