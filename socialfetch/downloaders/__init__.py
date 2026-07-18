"""Downloader package — all downloaders are registered here."""

# Import all downloader modules to trigger registry registration
from socialfetch.downloaders import (
    instagram,  # noqa: F401
    spotify,  # noqa: F401
    youtube,  # noqa: F401
)
from socialfetch.downloaders.registry import DownloaderRegistry

__all__ = ["DownloaderRegistry"]
