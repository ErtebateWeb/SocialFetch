"""Instagram photo fallback helpers (no yt-dlp).

Implements ADR 0013: resolve public image URLs via oEmbed / og:image /
display_url scrape, then download bytes with stdlib urllib.
"""

import contextlib
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": DEFAULT_UA,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/json,*/*;q=0.8",
}


def fetch_text(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
) -> str:
    """Fetch a URL and return decoded text body."""
    req_headers = dict(DEFAULT_HEADERS)
    if headers:
        req_headers.update(headers)
    request = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        text: str = response.read().decode(charset, errors="replace")
        return text


def fetch_bytes(
    url: str,
    headers: dict[str, str] | None = None,
    referer: str | None = None,
    timeout: float = 20.0,
) -> tuple[bytes, str]:
    """Fetch binary content; return (body, content_type)."""
    req_headers = dict(DEFAULT_HEADERS)
    req_headers["Accept"] = "image/avif,image/webp,image/*,*/*;q=0.8"
    if referer:
        req_headers["Referer"] = referer
    if headers:
        req_headers.update(headers)
    request = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get_content_type() or "application/octet-stream"
        body: bytes = response.read()
        return body, content_type


def parse_oembed_image_urls(oembed_json: dict[str, object]) -> list[str]:
    """Extract image URLs from an Instagram oEmbed payload."""
    urls: list[str] = []
    thumb = oembed_json.get("thumbnail_url")
    if isinstance(thumb, str) and thumb.strip():
        urls.append(thumb.strip())
    return urls


def parse_og_image_urls(html: str) -> list[str]:
    """Extract og:image meta content values from HTML."""
    patterns = [
        r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
        r'content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
        r'name=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
    ]
    found: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, html, flags=re.IGNORECASE):
            value = match.group(1).strip()
            if value:
                found.append(_unescape_url(value))
    return found


def parse_display_urls(html: str) -> list[str]:
    """Extract display_url / display_src values embedded in page JSON."""
    found: list[str] = []
    for key in ("display_url", "display_src"):
        pattern = rf'"{key}"\s*:\s*"([^"]+)"'
        for match in re.finditer(pattern, html):
            value = _unescape_url(match.group(1).strip())
            if value:
                found.append(value)
    return found


def _unescape_url(value: str) -> str:
    """Decode common Instagram JSON URL escapes."""
    with contextlib.suppress(UnicodeDecodeError):
        # Handles \u0026 etc. when present as unicode escapes
        value = value.encode("utf-8").decode("unicode_escape")
    return (
        value.replace("\\u0026", "&").replace("\\/", "/").replace("&amp;", "&").strip()
    )


def _dedupe(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            out.append(url)
    return out


def resolve_image_urls(post_url: str) -> tuple[list[str], dict[str, str]]:
    """Resolve public image URLs for a post.

    Order: oEmbed → og:image HTML → display_url scrape.
    Returns (urls, metadata) where metadata may include author/caption.
    """
    metadata: dict[str, str] = {}
    urls: list[str] = []

    # 1) oEmbed
    oembed_url = "https://www.instagram.com/api/v1/oembed/?url=" + urllib.parse.quote(
        post_url, safe=""
    )
    try:
        body = fetch_text(
            oembed_url,
            headers={"Accept": "application/json"},
        )
        data = json.loads(body)
        if isinstance(data, dict):
            urls.extend(parse_oembed_image_urls(data))
            author = data.get("author_name")
            title = data.get("title")
            if isinstance(author, str) and author:
                metadata["author"] = author
            if isinstance(title, str) and title:
                metadata["caption"] = title
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        logger.debug("oEmbed resolve failed for %s: %s", post_url, exc)

    # 2-3) HTML meta + display_url if still empty or for carousel extras
    if not urls:
        try:
            html = fetch_text(post_url, headers={"Accept": "text/html"})
            urls.extend(parse_og_image_urls(html))
            urls.extend(parse_display_urls(html))
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            OSError,
        ) as exc:
            logger.debug("HTML resolve failed for %s: %s", post_url, exc)

    return _dedupe(urls), metadata


def _extension_for_content_type(content_type: str) -> str:
    mapping = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    return mapping.get(content_type.lower(), ".jpg")


def download_images(
    urls: list[str],
    dest_dir: Path,
    shortcode: str,
    referer: str = "https://www.instagram.com/",
) -> list[Path]:
    """Download image URLs into dest_dir as {shortcode}_{i}.ext."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for index, url in enumerate(urls):
        try:
            body, content_type = fetch_bytes(url, referer=referer)
            is_jpeg = body[:3] == b"\xff\xd8\xff"
            is_png = body[:8] == b"\x89PNG\r\n\x1a\n"
            if not content_type.startswith("image/") and not (is_jpeg or is_png):
                logger.debug("Skipping non-image URL: %s (%s)", url, content_type)
                continue
            if is_jpeg:
                ext = ".jpg"
            elif is_png:
                ext = ".png"
            else:
                ext = _extension_for_content_type(content_type)
            path = dest_dir / f"{shortcode}_{index}{ext}"
            path.write_bytes(body)
            saved.append(path)
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            OSError,
        ) as exc:
            logger.debug("Failed to download image %s: %s", url, exc)
    return saved


def resolve_and_download_photos(
    post_url: str,
    dest_dir: Path,
    shortcode: str,
) -> tuple[list[Path], dict[str, str]]:
    """Resolve image URLs and download them to dest_dir."""
    urls, metadata = resolve_image_urls(post_url)
    if not urls:
        return [], metadata
    files = download_images(urls, dest_dir, shortcode, referer=post_url)
    return files, metadata
