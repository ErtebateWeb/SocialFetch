# ADR 0006: Error Handling Strategy

## Status
Accepted

## Context
Download operations can fail in many ways: network errors, authentication failures,
rate limiting, invalid URLs, deleted content. Error handling must be consistent
and actionable.

## Decision
A custom exception hierarchy rooted at `SocialFetchError`:
- `DownloadError` (base for download failures)
  - `NetworkError` (connection timeouts, DNS failures)
  - `AuthError` (invalid/expired credentials)
  - `RateLimitError` (too many requests)
  - `MediaNotFoundError` (deleted/unavailable content)
  - `InvalidURLError` (unrecognized format)

## Consequences
- Callers can catch specific errors
- Consistent error messages for end users
- Easy to add new error types
