# ADR 0001: Downloader Registry Pattern

## Status
Accepted

## Context
SocialFetch needs to support multiple social media platforms (Instagram, TikTok, YouTube, X, etc.).
Adding new platforms should not require modifying existing code.

## Decision
We use a **Registry Pattern** where each downloader class registers itself via a decorator.
The registry maps platform identifiers to downloader classes and selects the correct one
based on URL pattern matching.

## Consequences
### Positive
- New platforms = new file + decorator, no changes to registry
- URL-to-downloader resolution is centralized
- Easy to test in isolation

### Negative
- All downloaders are loaded at startup (acceptable for now)

## Implementation
```python
@DownloaderRegistry.register("instagram")
class InstagramDownloader(BaseDownloader):
    ...
```
