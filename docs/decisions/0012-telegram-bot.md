# ADR 0012: Telegram Bot Integration

## Status
Accepted

## Context
SocialFetch needs a Telegram interface so users can send URLs and receive
downloaded media directly in chat. The existing `@ew_insta_bot` handles
Instagram only — SocialFetch should support all platforms.

## Decision
Create a `telegram/` module that:
1. Uses `python-telegram-bot` (same as the existing bot)
2. Registers URL handlers that call `DownloadOrchestrator`
3. Supports multiple platforms out of the box
4. Sends media back with captions

## Architecture
```
telegram/
├── __init__.py
├── bot.py          ← Application builder
└── handlers.py     ← Message handlers
```

## Usage
```python
from socialfetch.telegram.bot import create_bot

app = create_bot(token="YOUR_TOKEN")
app.run_polling()
```

## Consequences
- Clean separation between download logic and Telegram
- Reuses DownloadOrchestrator for all platforms
- Easy to deploy as a standalone service
- Users interact via simple URL messages
