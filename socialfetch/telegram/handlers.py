"""Message handlers for the SocialFetch Telegram bot."""
import logging
import shutil
import subprocess as sp
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

        for index, file_path in enumerate(result.saved_paths):
            file_caption = caption if index == 0 else None
            path = Path(file_path)
            size_mb = path.stat().st_size / (1024 * 1024)

            if size_mb > 49:
                sent = await _send_large_file(update, path, file_caption)
                if sent:
                    path.unlink(missing_ok=True)
                    continue
                # Fallback — plain text
                await update.message.reply_text(
                    f"⚠️ Could not send file ({size_mb:.0f}MB)"
                )
                continue

            with path.open("rb") as f:
                if path.suffix.lower() in {".mp4", ".webm", ".mkv"}:
                    await update.message.reply_video(
                        video=f,
                        caption=file_caption,
                        supports_streaming=True,
                        read_timeout=120,
                        write_timeout=120,
                    )
                else:
                    await update.message.reply_photo(
                        photo=f, caption=file_caption
                    )

            path.unlink(missing_ok=True)

        await status_msg.delete()

    except Exception as e:
        logger.error("Download error: %s", e)
        await status_msg.edit_text(f"❌ Error: {str(e)[:200]}")


async def _send_large_file(
    update: Update, path: Path, caption: str | None
) -> bool:
    """Send a file >50MB. Tries compress then split. Returns True if sent."""
    has_ffmpeg = shutil.which("ffmpeg") is not None

    # 1) Compress with increasing aggression
    if has_ffmpeg:
        compressed = path.with_suffix(".compressed.mp4")
        try:
            orig_size = path.stat().st_size
            for crf, scale in [(28, None), (32, "720"), (35, "480")]:
                cmd = [
                    "ffmpeg", "-y", "-i", str(path),
                    "-c:v", "libx264", "-preset", "fast",
                    "-crf", str(crf), "-c:a", "aac", "-b:a", "96k",
                    "-movflags", "+faststart",
                ]
                if scale:
                    cmd += ["-vf", f"scale={scale}:-2"]
                cmd.append(str(compressed))
                sp.run(cmd, capture_output=True, timeout=300)
                if compressed.exists():
                    new_size = compressed.stat().st_size
                    logger.info(
                        "compress: crf=%s scale=%s %s->%sMB",
                        crf, scale or "orig",
                        orig_size // 1024 // 1024,
                        new_size // 1024 // 1024,
                    )
                    if new_size < 49 * 1024 * 1024:
                        break
            if compressed.exists() and compressed.stat().st_size < 49 * 1024 * 1024:
                with compressed.open("rb") as f:
                    await update.message.reply_video(
                        video=f,
                        caption=caption,
                        supports_streaming=True,
                        read_timeout=120,
                        write_timeout=120,
                    )
                compressed.unlink()
                return True
        except Exception as exc:
            logger.error("compress failed: %s", exc)
        finally:
            if compressed.exists():
                compressed.unlink()

    # 2) Split without re-encode
    if has_ffmpeg:
        try:
            dur_str = sp.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                capture_output=True, text=True, timeout=30,
            ).stdout.strip()
            dur = float(dur_str)
            size_mb = path.stat().st_size / (1024 * 1024)
            parts = int(size_mb / 45) + 1
            seg_dur = dur / parts
            logger.info("splitting %sMB into %s parts", size_mb, parts)

            for i in range(parts):
                seg = path.with_name(f"{path.stem}_part{i+1}{path.suffix}")
                ss = i * seg_dur
                sp.run([
                    "ffmpeg", "-y", "-ss", str(ss), "-i", str(path),
                    "-t", str(seg_dur), "-c", "copy", str(seg),
                ], capture_output=True, timeout=300)
                seg_cap = caption if i == 0 else None
                with seg.open("rb") as f:
                    await update.message.reply_video(
                        video=f,
                        caption=seg_cap,
                        supports_streaming=True,
                        read_timeout=120,
                        write_timeout=120,
                    )
                seg.unlink(missing_ok=True)
            return True
        except Exception as exc:
            logger.error("split failed: %s", exc)

    return False


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
