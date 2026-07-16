# ADR 0002: URL-based Platform Detection

## Status
Accepted

## Context
The system must automatically detect which downloader to use based on a user-provided URL.
Platform detection must be reliable and extensible.

## Decision
Each platform registers a URL pattern (regex) alongside its downloader class.
The URL parser tests patterns in registration order and returns the first match.

## Consequences
- Simple, predictable resolution
- No external API calls needed for detection
- Patterns are co-located with downloader implementations
