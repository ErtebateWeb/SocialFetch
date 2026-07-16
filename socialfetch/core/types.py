"""Type aliases and constants shared across the SocialFetch codebase."""

from pathlib import Path
from typing import TypeAlias

JSONDict: TypeAlias = dict[str, object]
"""Represents a generic JSON-serializable dictionary."""

PathLike: TypeAlias = str | Path
"""Any type that can be treated as a file-system path."""

PlatformName: TypeAlias = str
"""Canonical platform identifier (e.g. 'instagram', 'tiktok')."""
