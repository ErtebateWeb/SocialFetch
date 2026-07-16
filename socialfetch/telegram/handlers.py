"""Message handlers for the SocialFetch Telegram bot."""

import logging
from pathlib import Path

from telegram import InputMediaPhoto, InputMediaVideo, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from socialfetch.core.models import MediaInfo
from socialfetch.services.downloader import DownloadOrchestrator, DownloadResult

logger = logging.getLogger(__name__)
orchestrator = DownloadOrchestrator()

INSTAGRAM_PATTERN = r"(?:https?://)?(?:www\.)?instagram\.com/(?:p|reel|tv|stories)/\S+"
YOUTUBE_PATTERN = r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/\S+"
TIKTOK_PATTERN = r"(?:https?://)?(?:www\.)?tiktok\.com/\S+"

_CAPTION_LIMIT = 1024


def format_media_caption(media: MediaInfo, source_url: str | None = None) -> str:
    parts: list[str] = []
    author = (media.author or "").strip()
    caption = (media.caption or "").strip()
    url = (source_url or media.url or "").strip()

    if author:
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

        # Use album (media group) for multiple files, single for one
        if len(result.saved_paths) > 1:
            media_group = []
            paths = [Path(p) for p in result.saved_paths]
            files = [p.open("rb") for p in paths]
            try:
                for idx, (f, p) in enumerate(zip(files, paths, strict=False)):
                    cap = caption if idx == 0 else None
                    if p.suffix.lower() in {".mp4", ".webm", ".mkv"}:
                        media_group.append(InputMediaVideo(media=f, caption=cap))
                    else:
                        media_group.append(InputMediaPhoto(media=f, caption=cap))
                await update.message.reply_media_group(media_group)
            finally:
                for f in files:
                    f.close()
        else:
            path = Path(result.saved_paths[0])
            with path.open("rb") as f:
                if path.suffix.lower() in {".mp4", ".webm", ".mkv"}:
                    await update.message.reply_video(
                        video=f,
                        caption=caption,
                        supports_streaming=True,
                        read_timeout=300,
                        write_timeout=300,
                    )
                else:
                    await update.message.reply_photo(photo=f, caption=caption)

        # Cleanup all temp files
        for file_path in result.saved_paths:
            Path(file_path).unlink(missing_ok=True)

        await status_msg.delete()

    except Exception as e:
        logger.error("Download error: %s", e)
        await status_msg.edit_text(f"❌ Error: {str(e)[:200]}")


def get_handlers() -> list:
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
