# ADR 0013: Instagram Photo Fallback Without yt-dlp

## Status

Accepted

## Context

Instagram photo-only posts fail under the current `InstagramDownloader` path: yt-dlp raises effectively “No video formats found”, which is mapped to `MediaNotFoundError`. Reels and video posts succeed on the VPS. Users need photo support without forcing yt-dlp to extract non-video media.

Constraints and facts:

- Clean architecture, async-first; registry pattern; `MediaInfo` model; `LocalStorage`; Telegram bot delivery.
- Prefer stdlib or light deps already in the stack (`httpx` may be available via the Telegram stack).
- Prior bot `@ew_insta_bot` used non-yt-dlp Instagram approaches; VPS egress sometimes needs WARP for Instagram.
- Photo-only must not break the working video/reel path.

## Decision

Keep yt-dlp as the primary extractor for Instagram URLs (videos/reels). On a clear “no video formats” / photo-only failure, fall back to a lightweight HTTP image path that does **not** use yt-dlp.

**Fallback order (photo path):**

1. **yt-dlp** (existing) — success → video/reel as today.
2. On no-video-formats / photo-only signal → **Instagram oEmbed / embed** (public endpoint when available) for thumbnail / media URL.
3. Else → **HTML meta scrape** of `og:image` (and related Open Graph tags) from the public post URL.
4. Else → **mobile page scrape** for `display_url` (or equivalent JSON/embedded media URL) when present in the response body.
5. Download image bytes over HTTP(S); persist via existing output layout; populate `MediaInfo` as image (single photo first).
6. **Carousel:** best-effort only if multiple image URLs are already present in oEmbed/HTML/JSON; otherwise deliver the primary image only. No login, no Graph API, no session cookies as a hard requirement for v1.

Concrete behavior:

- Video path unchanged when yt-dlp succeeds.
- Photo path raises `MediaNotFoundError` only after all fallbacks fail.
- Prefer stdlib `urllib` for minimal deps (httpx optional if already present).
- User-Agent and headers suitable for public Instagram pages; respect existing proxy/WARP egress configuration.

## Alternatives

| Option | Rejected because |
|--------|------------------|
| Force yt-dlp image extract / custom format selectors | Unreliable for photo-only; couples photos to yt-dlp breakage |
| Official Instagram Graph API | App review, tokens, scope; out of band for this bot |
| Full browser automation (Playwright/Selenium) | Heavy, fragile on VPS, ops cost |
| Third-party unofficial IG APIs | ToS/stability/security risk |
| Photos out of scope | Product requirement: users expect photo posts |

## Consequences

**Positive**

- Photos work without yt-dlp media extraction.
- Videos/reels remain on the proven path.
- Minimal new surface: HTTP fetch + URL discovery + existing storage/delivery.

**Negative / trade-offs**

- HTML/oEmbed selectors can break when Instagram changes markup.
- Rate limits, soft blocks, and login walls may reduce success rate (mitigated by WARP/proxy already used for IG).
- Carousel completeness is best-effort, not guaranteed.
- Slightly more branching in the Instagram downloader.

## Implementation Plan

**Files**

- `socialfetch/downloaders/instagram.py` — orchestrate yt-dlp then photo fallback.
- `socialfetch/downloaders/instagram_photo.py` — oEmbed, meta scrape, mobile `display_url` discovery, image download.
- Tests with HTML/oEmbed fixtures (not live IG in CI).

**Methods**

- `download(url) -> MediaInfo`: try yt-dlp; on photo-only error → photo fallback.
- `resolve_image_urls(url) -> list[str]`: oEmbed → og:image → mobile scrape.
- `fetch_bytes(image_url) -> Path` + content-type check.
- Carousel: if `len(urls) > 1`, attach extras best-effort.

**Fallback order (runtime)**

1. yt-dlp
2. oEmbed/embed
3. `og:image` (desktop public HTML)
4. mobile page `display_url` (and siblings if present)
5. fail → `MediaNotFoundError`

## Risks

| Risk | Mitigation |
|------|------------|
| Login / interstitial walls | Public endpoints only; reuse WARP/proxy; clear error if HTML is challenge page |
| Carousels incomplete | Document best-effort; primary image always preferred |
| Rate limits / IP blocks | Backoff, shared egress config, avoid aggressive retries |
| Markup / oEmbed churn | Isolate parsers; fixture-based tests; feature flag to disable photo path |
| Hotlink / CDN auth on image URLs | Fetch promptly; send Referer/User-Agent if required; fail closed to `MediaNotFoundError` |

## Acceptance Criteria

- [ ] Reel/video Instagram URLs still succeed via yt-dlp with no regression.
- [ ] Single photo-only post returns image bytes, stored, deliverable by the Telegram bot.
- [ ] yt-dlp “No video formats found” (or equivalent) triggers fallback instead of immediate hard fail when photo URLs resolve.
- [ ] All listed fallbacks exhausted → `MediaNotFoundError`.
- [ ] No new heavy dependencies required for the happy path; stdlib preferred.
- [ ] Carousel: at least primary image; multiple images when URLs are available without login.
- [ ] Unit tests cover parser/fallback order; photo path does not call yt-dlp for image download after the no-video signal.
