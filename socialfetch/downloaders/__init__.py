"""Downloader package — all downloaders are registered here."""

# Import all downloader modules to trigger registry registration
from socialfetch.downloaders import instagram  # noqa: F401
from socialfetch.downloaders.registry import DownloaderRegistry as DownloaderRegistry  # noqa: F401
