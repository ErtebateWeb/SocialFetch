"""Abstract storage backends for SocialFetch."""

from abc import ABC, abstractmethod
from pathlib import Path

from socialfetch.core.models import MediaInfo
from socialfetch.core.types import JSONDict, PathLike


class StorageBackend(ABC):
    """Abstract storage backend for downloaded media."""

    @abstractmethod
    def save(self, media: MediaInfo, base_dir: PathLike | None = None) -> list[Path]:
        """Persist *media* files and return the final paths."""

    @abstractmethod
    def load_metadata(self, media_id: str, platform: str) -> JSONDict | None:
        """Load the metadata sidecar for a previously downloaded item."""


class StorageError(Exception):
    """Raised when a storage operation fails."""
