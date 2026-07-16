# ADR 0005: Async-First Download Engine

## Status
Accepted

## Context
Downloads can be I/O-bound (network requests). The system should handle
multiple downloads concurrently when queued via the Telegram bot or API.

## Decision
All downloaders implement async methods. The service layer uses asyncio
for concurrent download management.

## Consequences
- Efficient concurrent downloads
- Consistent async interface across all downloaders
- Future-proof for web API (FastAPI/Starlette)
