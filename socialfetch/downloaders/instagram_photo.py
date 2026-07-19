"""Instagram photo fallback helpers (no yt-dlp).

Implements ADR 0013 + carousel support: resolve public image URLs via
oEmbed (metadata) + embed page (image URLs), then download with stdlib urllib.
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


def parse_oembed_metadata(oembed_json: dict[str, object]) -> dict[str, str]:
    """Extract metadata from Instagram oEmbed payload."""
    meta: dict[str, str] = {}
    author = oembed_json.get("author_name")
    title = oembed_json.get("title")
    if isinstance(author, str) and author:
        meta["author"] = author
    if isinstance(title, str) and title:
        meta["caption"] = title
    return meta


def _file_id_from_url(url: str) -> str:
    """Extract the unique file identifier from a CDN URL."""
    m = re.search(r"/(\d{6,}_[^/]+?)_n\.jpg", url)
    return m.group(1) if m else url


def _parse_embed_image_urls(html: str) -> list[str]:
    """Extract unique post image URLs from Instagram embed HTML.

    Strategy:
    1. Find the embedded JSON containing graphql data
    2. Parse it to extract all display_url values from carousel children
    3. Falls back to raw scontent URL extraction if JSON parsing fails
    """
    urls: list[str] = []

    # Try to extract from embedded JSON data
    for marker in ("edge_sidecar_to_children", "shortcode_media", "display_url"):
        idx = html.find(marker)
        if idx < 0:
            continue

        if marker == "edge_sidecar_to_children":
            idx = html.find(":", idx) + 1
            # Find the matching } or ] for this JSON value
            data = _extract_json_value(html, idx)
            if data:
                decoded = _decode_escaped_json(data)
                children = _get_carousel_urls(decoded)
                if children:
                    urls = children
                    break

    # Fallback: raw scontent URLs
    if not urls:
        raw = re.findall(
            r'(https://scontent[^"\\\\]+\.(?:jpg|png|webp)[^"\\\\]*)', html
        )
        seen: set[str] = set()
        for img in raw:
            if "/v/t51.82787-19/" in img or "/v/t51.2885-19/" in img:
                continue
            fid_match = re.search(r"/(\d{6,}_[^/]+?)_n\.", img)
            fid = fid_match.group(1) if fid_match else img.split("?")[0]
            if fid and fid not in seen:
                seen.add(fid)
                url = img.split("  ")[0].strip().rstrip(",").replace("&amp;", "&")
                urls.append(url)

    # Deduplicate
    seen_urls: set[str] = set()
    deduped: list[str] = []
    for u in urls:
        if u and u not in seen_urls:
            seen_urls.add(u)
            deduped.append(u)
    return deduped


def _extract_json_value(html: str, start: int) -> str | None:
    """Extract a JSON value starting at *start*, handling escaped strings."""
    # Skip whitespace
    while start < len(html) and html[start] in " \t\r\n":
        start += 1
    if start >= len(html):
        return None

    first = html[start]
    if first not in ("{", "["):
        return None

    depth = 0
    in_str = False
    escape = False
    end = start
    for i in range(start, min(start + 200000, len(html))):
        ch = html[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and not escape:
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch in ("{", "["):
            depth += 1
        elif ch in ("}", "]"):
            depth -= 1
            if depth <= 0:
                end = i + 1
                return html[start:end]
    return None


def _decode_escaped_json(raw: str) -> str:
    """Decode Instagram's escaped JSON format.

    Handles:
    - \\\" -> \"
    - \\\\ -> \\
    - \\/ -> /
    - \\uXXXX -> unicode char
    """
    # First pass: common patterns
    raw = raw.replace('\\\\"', '\\"')  # \\\" -> \"
    raw = raw.replace('\\"', '"')  # \" -> "
    raw = raw.replace("\\/", "/")  # \/ -> /
    raw = raw.replace("\\\\", "\\")  # \\ -> \

    with contextlib.suppress(UnicodeEncodeError, UnicodeDecodeError):
        raw = raw.encode("utf-8").decode("unicode_escape")

    return raw


def _get_carousel_urls(decoded_json: str) -> list[str]:
    """Parse decoded JSON and extract all display_url values from carousel edges."""
    try:
        data = json.loads(decoded_json)
    except json.JSONDecodeError:
        return []

    # The JSON might be the edges array or contain edges
    edges = None
    if isinstance(data, dict):
        edges = data.get("edges")
    if not edges and isinstance(data, list):
        edges = data

    if not edges:
        return []

    urls: list[str] = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        node = edge.get("node", {})
        if not isinstance(node, dict):
            continue
        url = node.get("display_url", "")
        if url and isinstance(url, str):
            # Clean up the URL
            url = url.replace("\\/", "/").replace("\\u0026", "&")
            urls.append(url)
    return urls


def _fetch_embed_page(url: str) -> str:
    """Fetch Instagram embed page with minimal headers (no User-Agent).

    Chrome User-Agent causes Instagram to return a JS-heavy page
    without static image URLs. No User-Agent gives the simple page.
    """
    req = urllib.request.Request(url)
    req.add_header("Accept", "text/html")
    with urllib.request.urlopen(req, timeout=15) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        body: str = resp.read().decode(charset, errors="replace")
        return body


def resolve_image_urls(post_url: str) -> tuple[list[str], dict[str, str]]:
    """Resolve all image URLs for a post (including carousel).

    Order:
    1. Embed page (all carousel images)
    2. oEmbed thumbnail (single-image fallback)
    3. og:image / display_url (last resort)

    Returns (urls, metadata).
    """
    metadata: dict[str, str] = {}
    urls: list[str] = []

    # 1) oEmbed for metadata + fallback thumbnail
    oembed_url = "https://www.instagram.com/api/v1/oembed/?url=" + urllib.parse.quote(
        post_url, safe=""
    )
    oembed_thumb = ""
    try:
        body = fetch_text(oembed_url, headers={"Accept": "application/json"})
        data = json.loads(body)
        if isinstance(data, dict):
            metadata.update(parse_oembed_metadata(data))
            thumb = data.get("thumbnail_url")
            if isinstance(thumb, str) and thumb.strip():
                oembed_thumb = thumb.strip()
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        logger.debug("oEmbed failed for %s: %s", post_url, exc)

    # 2) Embed page — best source for carousel images
    base_post = post_url.split("?")[0].rstrip("/") + "/embed/"
    embed_url = base_post
    try:
        # Fetch embed with minimal headers — Chrome UA triggers JS-only page
        # without embedded image URLs
        embed_html = _fetch_embed_page(embed_url)
        embed_imgs = _parse_embed_image_urls(embed_html)
        if embed_imgs:
            urls = embed_imgs
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        OSError,
    ) as exc:
        logger.debug("Embed page failed for %s: %s", post_url, exc)

    # 3) Fallback to oEmbed thumbnail if embed had nothing
    if not urls and oembed_thumb:
        urls = [oembed_thumb]

    # 4) Last resort: HTML og:image / display_url
    if not urls:
        try:
            html = fetch_text(post_url, headers={"Accept": "text/html"})
            for pat in [
                r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
                r'content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
            ]:
                for m in re.finditer(pat, html, flags=re.IGNORECASE):
                    val = m.group(1).strip()
                    if val:
                        urls.append(_unescape_url(val))
            for key in ("display_url", "display_src"):
                for m in re.finditer(rf'"{key}"\s*:\s*"([^"]+)"', html):
                    val = _unescape_url(m.group(1).strip())
                    if val:
                        urls.append(val)
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            OSError,
        ) as exc:
            logger.debug("HTML resolve failed for %s: %s", post_url, exc)

    return _dedupe(urls), metadata


def _unescape_url(value: str) -> str:
    """Decode common Instagram JSON URL escapes."""
    with contextlib.suppress(UnicodeDecodeError):
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
    """Resolve image URLs (including carousel) and download them."""
    urls, metadata = resolve_image_urls(post_url)
    if not urls:
        return [], metadata
    files = download_images(urls, dest_dir, shortcode, referer=post_url)
    return files, metadata
