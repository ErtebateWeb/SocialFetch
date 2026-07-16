"""Instagram mobile API downloader (requires cookies)."""
import hashlib
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from socialfetch.core.errors import DownloadError

logger = logging.getLogger(__name__)

# Instagram mobile API credentials
IG_APP_ID = "936619743392459"
MOBILE_UA = (
    "Instagram 10.3.2 (iPhone9,3; iOS 10_0_1; en_US; en-US; "
    "scale=2.00; 750x1334) AppleWebKit/420+"
)
WEB_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def shortcode_to_id(shortcode: str) -> int:
    """Convert Instagram shortcode to media_id (base64-64 decoding)."""
    code = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    mid = 0
    for c in shortcode:
        mid = mid * 64 + code.index(c)
    return mid


def load_cookie_file(path: str) -> dict[str, str]:
    """Load Netscape-format cookie file into a dict."""
    cookies: dict[str, str] = {}
    if not os.path.exists(path):
        return cookies
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                cookies[parts[5]] = parts[6]
    return cookies


class InstagramAPIDownloader:
    """Download Instagram media via mobile API (requires cookies)."""

    def __init__(self, cookie_path: str = "", proxy: str = ""):
        self.cookie_path = cookie_path
        self.proxy = proxy
        self.cookies: dict[str, str] = {}
        if cookie_path:
            self.cookies = load_cookie_file(cookie_path)

    @property
    def has_cookies(self) -> bool:
        return bool(self.cookies.get("sessionid")) and bool(
            self.cookies.get("csrftoken")
        )

    def download_media(
        self,
        shortcode: str,
        output_dir: Path,
    ) -> dict[str, Any] | None:
        """Download media via Instagram mobile API.

        Returns metadata dict with keys:
          - files: list[Path]
          - author: str
          - caption: str
          - media_type: str (photo/video/carousel)
          - likes: int
          - comments: int
          - is_video: bool
        Or None if API fails.
        """
        if not self.has_cookies:
            logger.debug("No valid Instagram cookies, skipping API")
            return None

        try:
            return self._download_via_api(shortcode, output_dir)
        except Exception as e:
            logger.debug("Instagram API download failed: %s", e)
            return None

    def _make_request(self, url: str) -> Any:
        """Make an HTTP request through proxy with Instagram cookies."""
        import requests

        proxies: dict[str, str] = {}
        if self.proxy:
            proxies = {"https": self.proxy, "http": self.proxy}

        headers = {
            "User-Agent": MOBILE_UA,
            "Accept": "*/*",
            "X-IG-App-ID": IG_APP_ID,
            "X-IG-Capabilities": "3brTvx4=",
            "X-IG-Connection-Type": "WIFI",
            "X-CSRFToken": self.cookies.get("csrftoken", ""),
        }

        r = requests.get(
            url,
            headers=headers,
            cookies=self.cookies,
            proxies=proxies,
            timeout=30,
        )
        if r.status_code != 200:
            logger.debug("API returned %d: %s", r.status_code, r.text[:200])
            return None

        data = r.json()
        if data.get("status") != "ok":
            logger.debug("API status not ok: %s", data.get("message", "?"))
            return None

        return data

    def _download_via_api(
        self,
        shortcode: str,
        output_dir: Path,
    ) -> dict[str, Any]:
        """Download media using Instagram's internal mobile API."""

        media_id = shortcode_to_id(shortcode)
        api_url = f"https://i.instagram.com/api/v1/media/{media_id}/info/"

        data = self._make_request(api_url)
        if not data:
            raise DownloadError("API request failed")

        items = data.get("items", [])
        if not items:
            raise DownloadError("No items in API response")

        item = items[0]
        media_type_code = item.get("media_type", 1)  # 1=photo, 2=video, 8=carousel

        caption = ""
        if item.get("caption") and isinstance(item["caption"], dict):
            caption = item["caption"].get("text", "") or ""
        author = ""
        if item.get("user") and isinstance(item["user"], dict):
            author = item["user"].get("username", "") or ""
        likes = item.get("like_count", 0) or 0
        comments = item.get("comment_count", 0) or 0

        is_carousel = media_type_code == 8 or "carousel_media" in item

        temp_dir = Path(tempfile.mkdtemp(prefix="ig_api_"))
        downloaded_files: list[Path] = []
        seen_hashes: set[str] = set()

        try:
            if is_carousel:
                carousel_items = item.get("carousel_media", [])
                logger.debug("Found %d carousel items via API", len(carousel_items))

                for idx, child in enumerate(carousel_items):
                    child_type = child.get("media_type", 1)

                    if child_type == 2:
                        video_versions = child.get("video_versions", [])
                        if video_versions:
                            video_url: str = video_versions[0].get("url", "")
                            path = temp_dir / f"{shortcode}_{idx+1}.mp4"
                            self._download_file(video_url, str(path))
                            if path.stat().st_size > 1000:
                                downloaded_files.append(path)
                    else:
                        candidates = child.get("image_versions2", {}).get(
                            "candidates", []
                        )
                        if candidates:
                            best = max(
                                candidates,
                                key=lambda c: (c.get("width", 0) or 0)
                                * (c.get("height", 0) or 0),
                            )
                            img_url: str = best.get("url", "")
                            path = temp_dir / f"{shortcode}_{idx+1}.jpg"
                            self._download_file(img_url, str(path))
                            if path.stat().st_size > 1000:
                                file_hash = hashlib.md5(
                                    path.read_bytes()
                                ).hexdigest()
                                if file_hash not in seen_hashes:
                                    seen_hashes.add(file_hash)
                                    downloaded_files.append(path)
                                else:
                                    path.unlink()
            else:
                if media_type_code == 2:
                    video_versions = item.get("video_versions", [])
                    if video_versions:
                        vu: str = video_versions[0].get("url", "")
                        path = temp_dir / f"{shortcode}.mp4"
                        self._download_file(vu, str(path))
                        if path.stat().st_size > 1000:
                            downloaded_files.append(path)
                else:
                    candidates = item.get("image_versions2", {}).get(
                        "candidates", []
                    )
                    if candidates:
                        best = max(
                            candidates,
                            key=lambda c: (c.get("width", 0) or 0)
                            * (c.get("height", 0) or 0),
                        )
                        iu: str = best.get("url", "")
                        path = temp_dir / f"{shortcode}.jpg"
                        self._download_file(iu, str(path))
                        if path.stat().st_size > 1000:
                            downloaded_files.append(path)

            if not downloaded_files:
                raise DownloadError("Failed to download any media via API")

            # Move to permanent directory
            output_dir.mkdir(parents=True, exist_ok=True)
            permanent_files: list[Path] = []
            for fpath in downloaded_files:
                dest = output_dir / fpath.name
                shutil.move(str(fpath), str(dest))
                permanent_files.append(dest)

            is_video = any(
                f.suffix.lower() in {".mp4", ".webm", ".mkv", ".avi"}
                for f in permanent_files
            )
            media_type = (
                "carousel" if is_carousel else "video" if is_video else "photo"
            )

            return {
                "files": permanent_files,
                "author": author,
                "caption": caption,
                "media_type": media_type,
                "likes": likes,
                "comments": comments,
                "is_video": is_video,
            }

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _download_file(self, url: str, output_path: str) -> None:
        """Download a file from URL to the given path via proxy."""
        import requests

        proxies: dict[str, str] = {}
        if self.proxy:
            proxies = {"https": self.proxy, "http": self.proxy}

        r = requests.get(
            url,
            stream=True,
            timeout=30,
            proxies=proxies,
            headers={"User-Agent": WEB_UA, "Referer": "https://www.instagram.com/"},
        )
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
