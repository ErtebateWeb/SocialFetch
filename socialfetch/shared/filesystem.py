"""Filesystem utilities."""

from __future__ import annotations

from pathlib import Path


def ensure_directory(path: Path | str) -> Path:
    """Create directory if it does not exist and return the Path."""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path
