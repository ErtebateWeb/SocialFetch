# ADR-0014: YouTube Downloader

**Status**: Draft

## Context

SocialFetch supports image platforms (Instagram). Users require video downloads from YouTube.
yt-dlp is already a project dependency and provides a robust, maintained extraction layer.

## Decision

Implement a YouTube downloader using the **adapter pattern**: wrap yt-dlp's `YoutubeDL` Python
API inside a class that implements `BaseDownloader`. Register it with `DownloaderRegistry`
using regex URL patterns for YouTube domains.

Media type mapping:
- Single video → `MediaType.VIDEO`
- Playlist → `MediaType.CAROUSEL` with individual videos as items
- Shorts → `MediaType.VIDEO` (same as standard video)
- Livestream → `MediaType.VIDEO`

Quality options map to yt-dlp format strings:
- `best` → `"bestvideo+bestaudio/best"`
- `best+1080` → `"bestvideo[height<=1080]+bestaudio/best[height<=1080]"`
- `best+480` → `"bestvideo[height<=480]+bestaudio/best[height<=480]"`
- `audio-only` → `"bestaudio/best"`

Subtitles (if `extra.subtitles` True) download via `writesubtitles`, `writeautomaticsub`.
Age-restricted content handled by `cookies_file` in `DownloadRequest`.
Playlist detection via yt-dlp playlist info dict, convert to CAROUSEL.

## URL Patterns

```python
r"https?://(www\\.)?youtube\\.com/watch\\?v="
r"https?://(www\\.)?youtube\\.com/shorts/"
r"https?://(www\\.)?youtube\\.com/playlist\\?list="
r"https?://(www\\.)?youtube\\.com/live/"
r"https?://youtu\\.be/[\\w-]+"
```

## File Changes

- `socialfetch/downloaders/youtube.py` — main downloader class
- `tests/test_youtube.py` — unit/integration tests (mocked yt-dlp responses)

## Consequences

**Positive**:
- Leverages yt-dlp's proven extraction and format handling
- No new runtime dependencies (yt-dlp already installed)
- Supports playlist, subtitles, multiple quality levels, age-restricted via cookies
- Uniform interface with other downloaders

**Negative**:
- `ffmpeg` required for video+audio merging (document in setup)
- YouTube ToS compliance — user responsibility
- Playlist downloads can be heavy — rate limiting considered
