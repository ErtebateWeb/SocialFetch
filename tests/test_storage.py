"""Tests for the storage layer."""

import json
import tempfile
from pathlib import Path

from socialfetch.core.models import MediaInfo, MediaMetadata, MediaType
from socialfetch.storage.local import LocalStorage


class TestLocalStorage:
    """Verify local filesystem storage behaviour."""

    def setup_method(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.storage = LocalStorage(base_dir=self.tmp_dir)
        self.sample_media = MediaInfo(
            platform="instagram",
            media_type=MediaType.PHOTO,
            shortcode="TEST123",
            url="https://instagram.com/p/TEST123/",
            author="test_user",
            caption="Test caption",
            files=[],
            metadata=MediaMetadata(likes=10, comments=2, views=100),
        )

    def teardown_method(self) -> None:
        import shutil

        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _create_dummy_file(self, name: str = "photo.jpg") -> Path:
        fpath = self.tmp_dir / name
        fpath.write_text("dummy content")
        return fpath

    def test_save_single_file(self) -> None:
        dummy = self._create_dummy_file()
        media = self.sample_media
        media.files = [dummy]

        saved = self.storage.save(media)
        assert len(saved) == 1
        assert saved[0].exists()
        assert saved[0].parent.name == "TEST123"
        assert saved[0].parent.parent.name == "instagram"

    def test_metadata_sidecar_created(self) -> None:
        dummy = self._create_dummy_file()
        media = self.sample_media
        media.files = [dummy]

        self.storage.save(media)
        meta_path = self.tmp_dir / "instagram" / "TEST123" / ".meta.json"
        assert meta_path.exists()

        meta = json.loads(meta_path.read_text())
        assert meta["platform"] == "instagram"
        assert meta["shortcode"] == "TEST123"
        assert meta["metadata"]["likes"] == 10

    def test_load_metadata(self) -> None:
        dummy = self._create_dummy_file()
        media = self.sample_media
        media.files = [dummy]
        self.storage.save(media)

        loaded = self.storage.load_metadata("TEST123", "instagram")
        assert loaded is not None
        assert loaded["author"] == "test_user"
        assert loaded["caption"] == "Test caption"

    def test_load_metadata_not_found(self) -> None:
        loaded = self.storage.load_metadata("NONEXISTENT", "instagram")
        assert loaded is None

    def test_save_multiple_files(self) -> None:
        files = [self._create_dummy_file(f"img_{i}.jpg") for i in range(3)]
        media = self.sample_media
        media.files = files
        media.media_type = MediaType.CAROUSEL

        saved = self.storage.save(media)
        assert len(saved) == 3
        for f in saved:
            assert f.exists()
