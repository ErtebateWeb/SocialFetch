# SocialFetch

> **Open-source self-hosted Social Media Downloader Framework**
> دانلودر متن‌باز و قابل میزبانی شخصی برای شبکه‌های اجتماعی

[![CI](https://github.com/ErtebateWeb/SocialFetch/actions/workflows/ci.yml/badge.svg)](https://github.com/ErtebateWeb/SocialFetch/actions/workflows/ci.yml)

---

## Features / قابلیت‌ها

| Platform | Status | Download Type |
|---|---|---|
| **Instagram** | ✅ | Reels, Videos, Photos, Carousels, Captions |
| **YouTube** | ✅ | Videos, Shorts, Playlists, Audio-only |
| **Spotify** | ✅ | Tracks, Albums, Playlists (opus/mp3) |
| **TikTok** | 🚧 | Planned |
| **X / Twitter** | 🚧 | Planned |

### Instagram
- Photos via embed page + oEmbed fallback
- Reels & videos via yt-dlp
- **Full carousel** (all images) via mobile API + **cookies** + WARP proxy
- Author, caption, like count included as caption

### YouTube
- Single videos, Shorts, Live streams
- Playlists (as carousel, max 10 items by default)
- Quality: `best`, `best+1080`, `best+480`, `audio-only`
- Subtitles (optional, English)
- **WARP proxy** to bypass bot detection
- Auto-fallback: android client if bot check triggered
- Forced **mp4** output for Telegram inline playback

### Spotify
- **Tracks, Albums, Playlists, Episodes, Shows** via spotdl
- Finds matching YouTube Music video → downloads as **opus** audio
- Full metadata: artist, title, album art embedded
- Requires **Deno** runtime (auto-downloaded on first use)

### Telegram Bot
- `@EW_SocialFetcher_bot` — paste a link, get media
- Local `telegram-bot-api` server (Docker) — **2GB upload limit**
- Multi-file carousels sent as album with caption on first (batched 10 per group)
- Large files sent inline as mp4 video

---

## Architecture / معماری

```
SocialFetch/
├── socialfetch/
│   ├── core/           # BaseDownloader, MediaInfo, errors
│   ├── downloaders/    # Platform implementations (instagram, youtube, spotify)
│   ├── services/       # DownloadOrchestrator, URL parser
│   ├── storage/        # Local file storage with dedup
│   └── telegram/       # Telegram bot (handlers, bot)
├── tests/              # pytest suite (84+ tests)
├── docs/decisions/     # ADRs (Architecture Decision Records)
└── run_bot.py          # Entry point
```

**Pattern:** Adapter pattern — each platform implements `BaseDownloader`, registered via `@DownloaderRegistry.register(platform, url_pattern)`.

---

## Quick Start / راه‌اندازی سریع

### Prerequisites / پیش‌نیازها

```bash
# System
python 3.11+
pip/uv
git
ffmpeg              # for video merging
docker              # for local telegram-bot-api (optional, for 2GB uploads)

# Python packages (installed automatically)
yt-dlp              # video extraction
spotdl              # Spotify download (includes Deno runtime)
python-telegram-bot # Telegram bot framework
pydantic-settings   # configuration
requests            # HTTP (for Instagram API)
```

### 1. Clone

```bash
git clone https://github.com/ErtebateWeb/SocialFetch.git
cd SocialFetch
```

### 2. Install / نصب

```bash
# Create virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Install package
pip install -e .
```

### 3. Configure / تنظیمات

Create `.env` in project root or set environment variables:

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_from_@BotFather

# Optional: Instagram cookies (for full carousel download)
# Export cookies from browser (Netscape format) to instagram_cookies.txt
# Get cookies.txt extension for Chrome: https://chrome.google.com/webstore/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid

# Optional: Local telegram-bot-api (for 2GB uploads)
# See "Local API Server" section below
```

### 4. Run / اجرا

```bash
# Start bot (polling mode)
python run_bot.py
```

---

## Instagram Cookies / کوکی اینستاگرام

Instagram mobile API requires **valid session cookies** for full carousel downloads.

### Setup

1. Install browser extension: [Get cookies.txt](https://chrome.google.com/webstore/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid) (Chrome) or similar
2. Log in to **instagram.com** in your browser
3. Click the extension icon → "Export" → save as `instagram_cookies.txt`
4. Place the file in the project root

**Security:** This file is in `.gitignore` and will **never** be committed.

### How it works
- Bot checks if `instagram_cookies.txt` exists with valid `sessionid`
- **With cookies:** mobile API → full carousel (all images) + WARP proxy
- **Without cookies:** embed page → 3-4 images, or oEmbed → 1 thumbnail

---

## YouTube / یوتیوب

### Bot Detection / جلوگیری از بلاک

YouTube blocks this VPS IP for bot downloads. Traffic is routed through **WARP SOCKS5 proxy** (`socks5h://127.0.0.1:40000`).

**No additional setup needed** — WARP is pre-configured on the deployment server.

### Auto-Fallback Quality

When "Sign in" / "not a bot" is detected, downloader auto-fallsback to android client for reliable download (may get lower quality on some videos).

---

## Spotify / اسپاتیفای

### How it works

1. Receive Spotify link (track, album, playlist, episode, show)
2. spotdl finds matching song on YouTube Music
3. Downloads as **opus** audio (≈3-4MB per track, good quality)
4. Sends as voice/audio file to Telegram

### Requirements

- **Deno** runtime — auto-downloaded on first `spotdl` use to `~/.config/spotdl/deno`
- No Spotify API credentials needed (uses YouTube Music metadata)

### Usage

Just paste any Spotify link:

- `https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT`
- `https://open.spotify.com/album/...`
- `https://open.spotify.com/playlist/...`

---

## Local Telegram Bot API Server / سرور API لوکال تلگرام

By default, Telegram Bot API limits uploads to **50MB**. Running a local API server increases this to **2000MB (2GB)**.

### Setup

```bash
# 1. Get API credentials from https://my.telegram.org/apps
#    You need: API_ID + API_HASH (different from bot token)

# 2. Run Docker container
docker run --name tba -d --restart=always \
  -p 127.0.0.1:8081:8081 \
  -e TELEGRAM_API_ID=YOUR_API_ID \
  -e TELEGRAM_API_HASH=YOUR_API_HASH \
  -v /var/lib/telegram-bot-api:/var/lib/telegram-bot-api \
  aiogram/telegram-bot-api:latest

# 3. Bot automatically detects and uses the local API
#    (configured in socialfetch/telegram/bot.py)
```

---

## WARP Proxy / پروکسی WARP

Instagram and YouTube are blocked from this VPS IP. **Cloudflare WARP** (via WireProxy) provides an unblocked tunnel.

Pre-configured on the deployment server:
- SOCKS5 endpoint: `socks5h://127.0.0.1:40000`
- Used automatically by Instagram API downloader, yt-dlp, and spotdl

---

## Rate Limit & Referral / محدودیت و معرفی

Built-in rate limiting per user:
- **5 downloads/day** (free tier)
- **75 downloads/month** (free tier)
- **Referral system:** `/ref` gives a code, each invite = 7 days Premium

### Commands
- `/plan` — your current download usage
- `/ref` — get/generate referral code
- `/ref YOUR_CODE` — accept a referral

---

## Testing / تست

```bash
# Run all tests
pytest tests/

# Run specific
pytest tests/test_youtube.py -v
pytest tests/test_instagram.py -v
pytest tests/test_spotify.py -v

# Lint & type check
ruff check socialfetch/ tests/
mypy socialfetch/
```

**Current: 84+ tests** — all pass. ✅

---

## Development Workflow / روش توسعه

This project follows a **multi-agent development workflow**:

| Role | Tool | Responsibility |
|---|---|---|
| 👤 **Product Owner** | (User) | Approves features, feedback |
| 🏛 **Architect** | `gcli/grok-4.5-high` | ADRs, architecture decisions |
| 🐍 **Developer** | `openrouter/qwen3-coder:free` | Implementation |
| 🧪 **QA** | `gcli/grok-4.5-medium` | Tests |
| 👁 **Reviewer** | `gcli/grok-4.5` | Code review |

1. ADR-first design → `docs/decisions/`
2. Role-specific commits with git identity
3. Sprint-based: develop → PR → squash merge to main
4. CI: format → lint → test → typecheck

---

## Architecture Decisions / تصمیمات معماری

See [docs/decisions/](docs/decisions/) for all ADRs.

| # | Title | Status |
|---|---|---|
| 0013 | Instagram Photo Fallback | ✅ |
| 0014 | YouTube Downloader (yt-dlp adapter) | ✅ |

---

## Roadmap / نقشه راه

- [x] Instagram downloader (video, photo, carousel)
- [x] YouTube downloader (video, shorts, playlists)
- [x] Spotify downloader (tracks, albums, playlists)
- [ ] TikTok downloader
- [ ] X/Twitter downloader
- [ ] REST API
- [ ] Docker Compose deployment
- [ ] Web UI

---

## License / مجوز

MIT License. See [LICENSE](LICENSE).

---

## Support / پشتیبانی

- Telegram: [@EW_SocialFetcher_bot](https://t.me/EW_SocialFetcher_bot)
- GitHub Issues: [ErtebateWeb/SocialFetch](https://github.com/ErtebateWeb/SocialFetch/issues)
