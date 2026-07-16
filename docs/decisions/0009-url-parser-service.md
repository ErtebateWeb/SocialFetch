# ADR 0009: URL Parser Service

## Status
Accepted

## Context
Users provide URLs from different platforms. The system must:
- Detect platform from URL
- Match to registered downloader
- Handle edge cases (query params, short URLs, mobile links)

## Decision
Create a `URLParser` service that:
- Uses the DownloaderRegistry's regex patterns
- Returns the matched downloader class + extracted identifier
- Provides `parse()` and `match()` methods

## Implementation
```python
class URLParser:
    @staticmethod
    def parse(url: str) -> ParseResult:
        """Returns platform name, downloader class, and identifier."""

    @staticmethod
    def match(url: str) -> bool:
        """Returns True if any registered platform matches."""
```

## Consequences
- Single source of URL detection logic
- Easy to test
- Automatic support for new platforms (via registry)
