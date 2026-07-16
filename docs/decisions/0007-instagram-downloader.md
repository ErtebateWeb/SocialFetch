# ADR 0007: Instagram Downloader Design

## Status
Accepted

## Context
Instagram is the first platform to implement. It supports:
- Single image posts
- Carousel (multi-image) posts
- Video reels
- IGTV videos
- Stories (with auth)

The downloader must handle:
- Public posts (no auth required for basic access)
- Cookie-based authentication for private/restricted content
- Rate limiting and error recovery

## Decision
### Strategy
Use **yt-dlp** as the primary download backend:
- Proven, maintained, handles Instagram's frequently changing API
- Supports cookies for authenticated downloads
- Handles both video and image extraction

### Cookie Support
- Optional cookie file path in DownloadRequest.extra
- Can also use `--cookies-from-browser` on desktop

### Output
All outputs normalized to `MediaInfo` with:
- Caption from post description
- Author extracted from metadata
- Files saved to platform/shortcode/ layout

## Consequences
- yt-dlp is a heavy dependency (~50MB)
- But it saves us from reverse-engineering Instagram's API
- Easy to swap implementation later if needed

## Implementation Plan
1. Add yt-dlp to project dependencies
2. Create InstagramDownloader(BaseDownloader)
3. Implement download() method using yt-dlp
4. Parse yt-dlp output into MediaInfo
5. Write unit + integration tests
