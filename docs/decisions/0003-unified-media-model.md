# ADR 0003: Unified Media Model

## Status
Accepted

## Context
Different platforms return different media types (single image, carousel, video, reels, stories).
The system needs a consistent representation regardless of source platform.

## Decision
A single `MediaInfo` dataclass represents all download results:
- media_type: enum (PHOTO, VIDEO, CAROUSEL, STORY, REEL)
- files: list of downloaded file paths
- caption, author, shortcode, url, metadata (dict for platform-specific extras)

## Consequences
- Uniform API for consumers (Telegram bot, REST API)
- Platform-specific data preserved in metadata dict
- Simple serialization for future API responses
