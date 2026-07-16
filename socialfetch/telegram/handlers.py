"""Message handlers for the SocialFetch Telegram bot."""

import logging

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from socialfetch.services.downloader import DownloadOrchestrator

logger = logging.getLogger(__name__)
orchestrator = DownloadOrchestrator()

INSTAGRAM_PATTERN = r"(?:https?://)?(?:www\.)?instagram\.com/(?:p|reel|tv|stories)/\S+"
YOUTUBE_PATTERN = r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/\S+"
TIKTOK_PATTERN = r"(?:https?://)?(?:www\.)?tiktok\.com/\S+"


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
        result = await orchestrator.download(url)

        if result.error:
            await status_msg.edit_text(f"❌ {result.error}")
            return

        await status_msg.edit_text(f"✅ {len(result.saved_paths)} file(s)! Sending...")

        for file_path in result.saved_paths:
            with open(file_path, "rb") as f:
                if file_path.lower().endswith((".mp4", ".webm", ".mkv")):
                    await update.message.reply_video(video=f, supports_streaming=True)
                else:
                    await update.message.reply_photo(photo=f)

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
