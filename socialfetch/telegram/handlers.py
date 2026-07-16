"""Message handlers for the SocialFetch Telegram bot."""

import logging
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from socialfetch.core.models import MediaInfo
from socialfetch.services.downloader import DownloadOrchestrator, DownloadResult

logger = logging.getLogger(__name__)
orchestrator = DownloadOrchestrator()

INSTAGRAM_PATTERN = r"(?:https?://)?(?:www\.)?instagram\.com/(?:p|reel|tv|stories)/\S+"
YOUTUBE_PATTERN = r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/\S+"
TIKTOK_PATTERN = r"(?:https?://)?(?:www\.)?tiktok\.com/\S+"

# Telegram media caption hard limit
_CAPTION_LIMIT = 1024


def format_media_caption(media: MediaInfo, source_url: str | None = None) -> str:
    """Build a Telegram caption like classic Instagram bots.

    Includes author, post caption, and optional source link.
    Truncates to Telegram's 1024-character media caption limit.
    """
    parts: list[str] = []
    author = (media.author or "").strip()
    caption = (media.caption or "").strip()
    url = (source_url or media.url or "").strip()

    if author:
        # Instagram-style handle when author has no @
        handle = author if author.startswith("@") else f"@{author}"
        parts.append(handle)

    if caption:
        parts.append(caption)

    if url:
        parts.append(f"🔗 {url}")

    text = "\n\n".join(parts).strip()
    if not text:
        return ""

    if len(text) <= _CAPTION_LIMIT:
        return text

    # Prefer keeping author + start of caption; drop URL first if needed
    suffix = "…"
    budget = _CAPTION_LIMIT - len(suffix)
    return text[:budget].rstrip() + suffix


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🤖 **SocialFetch Bot**\n\n"
        "Send me a link and I'll download it!\n\n"
        "**Supported:**\n"
        "📸 Instagram (posts, reels, stories)\n"
        "🎬 YouTube (videos, shorts)\n"
        "🎵 TikTok (videos)\n\n"
        "Just paste a URL! 🚀"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "**How to use:**\n"
        "1. Copy a link\n"
        "2. Paste it here\n"
        "3. Receive your media!\n\n"
        "/start - Welcome\n"
        "/help - This message"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    url = update.message.text.strip()
    status_msg = await update.message.reply_text("⏳ Downloading...")

    try:
        await update.message.chat.send_action(ChatAction.TYPING)
        result: DownloadResult = await orchestrator.download(url)

        if result.error:
            await status_msg.edit_text(f"❌ {result.error}")
            return

        if not result.saved_paths:
            await status_msg.edit_text("❌ No files downloaded")
            return

        await status_msg.edit_text(f"✅ {len(result.saved_paths)} file(s)! Sending...")

        caption = format_media_caption(result.media, source_url=result.url)

        for index, file_path in enumerate(result.saved_paths):
            file_caption = caption if index == 0 else None
            path = Path(file_path)
            size_mb = path.stat().st_size / (1024 * 1024)

            if size_mb > 49:
                # Try compress with ffmpeg to fit under 50MB
                compressed = path.with_suffix(".compressed.mp4")
                try:
                    import subprocess as sp
                    # Target ~45MB for 50MB limit headroom
                    target_bitrate = int(
                        45 * 8192 / max(path.stat().st_size / (1024 * 1024), 1)
                    )
                    cmd = [
                        "ffmpeg", "-y", "-i", str(path),
                        "-c:v", "libx264", "-b:v", f"{target_bitrate}k",
                        "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart",
                        str(compressed),
                    ]
                    sp.run(cmd, capture_output=True, timeout=300)
                    threshold = 49 * 1024 * 1024
                    if compressed.exists() and compressed.stat().st_size < threshold:
                        with compressed.open("rb") as f:
                            await update.message.reply_video(
                                video=f,
                                caption=file_caption,
                                supports_streaming=True,
                            )
                        compressed.unlink()
                        path.unlink()
                        continue
                except Exception:
                    pass
                finally:
                    if compressed.exists():
                        compressed.unlink()

                # Compression failed — send source link as last resort
                await update.message.reply_text(
                    f"⚠️ File too large ({size_mb:.0f}MB)\n"
                    f"🔗 [Open in YouTube]({result.url})",
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                )
                continue

            with path.open("rb") as f:
                if path.suffix.lower() in {".mp4", ".webm", ".mkv"}:
                    await update.message.reply_video(
                        video=f,
                        caption=file_caption,
                        supports_streaming=True,
                    )
                else:
                    await update.message.reply_photo(photo=f, caption=file_caption)

        await status_msg.delete()

    except Exception as e:
        logger.error("Download error: %s", e)
        await status_msg.edit_text(f"❌ Error: {str(e)[:200]}")


def get_handlers() -> list:  # type: ignore[type-arg]
    return [
        CommandHandler("start", cmd_start),
        CommandHandler("help", cmd_help),
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND
            & (
                filters.Regex(INSTAGRAM_PATTERN)
                | filters.Regex(YOUTUBE_PATTERN)
                | filters.Regex(TIKTOK_PATTERN)
            ),
            handle_url,
        ),
    ]
