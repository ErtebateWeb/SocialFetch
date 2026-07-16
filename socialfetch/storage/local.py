"""Local filesystem storage backend."""

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from socialfetch.core.models import MediaInfo
from socialfetch.core.types import JSONDict, PathLike
from socialfetch.storage.interfaces import StorageBackend, StorageError


class LocalStorage(StorageBackend):
    """Stores downloaded media on the local filesystem.

    Directory layout::

        <base_dir>/<platform>/<shortcode>/
            ├── file_1.jpg
            ├── file_2.mp4
            └── .meta.json

    Usage::

        storage = LocalStorage()
        paths = storage.save(media_info)
    """

    def __init__(self, base_dir: PathLike = "downloads") -> None:
        self.base_dir = Path(base_dir)

    def save(self, media: MediaInfo, base_dir: PathLike | None = None) -> list[Path]:
        """Save media files to ``<base_dir>/<platform>/<shortcode>/``."""
        root = Path(base_dir) if base_dir else self.base_dir
        post_dir = root / media.platform / media.shortcode
        post_dir.mkdir(parents=True, exist_ok=True)

        saved: list[Path] = []
        for src in media.files:
            src_path = Path(src)
            if not src_path.exists():
                continue
            dest = post_dir / src_path.name
            shutil.copy2(str(src_path), str(dest))
            saved.append(dest)

        if not saved:
            raise StorageError(f"No files saved for {media.shortcode}")

        # Write metadata sidecar
        self._write_metadata(post_dir, media, saved)
        return saved

    def load_metadata(self, media_id: str, platform: str) -> JSONDict | None:
        """Load the ``.meta.json`` sidecar for a media ID."""
        meta_path = self.base_dir / platform / media_id / ".meta.json"
        if not meta_path.exists():
            return None
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
        return dict(raw) if isinstance(raw, dict) else None

    def _write_metadata(
        self, post_dir: Path, media: MediaInfo, files: list[Path]
    ) -> None:
        """Write a JSON sidecar with download metadata."""
        meta: JSONDict = {
            "platform": media.platform,
            "shortcode": media.shortcode,
            "url": media.url,
            "media_type": media.media_type.name,
            "author": media.author,
            "caption": media.caption,
            "downloaded_at": datetime.now(UTC).isoformat(),
            "files": [
                {
                    "path": str(f.relative_to(self.base_dir)),
                    "name": f.name,
                    "size_bytes": f.stat().st_size,
                }
                for f in files
            ],
            "metadata": {
                "likes": media.metadata.likes,
                "comments": media.metadata.comments,
                "views": media.metadata.views,
            },
        }
        meta_path = post_dir / ".meta.json"
        meta_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )
