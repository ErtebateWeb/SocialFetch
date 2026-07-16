"""Tests for the Telegram bot module."""

import pytest
from telegram.error import InvalidToken
from telegram.ext import Application

from socialfetch.core.models import MediaInfo, MediaType
from socialfetch.telegram.bot import create_bot
from socialfetch.telegram.handlers import format_media_caption, get_handlers


class TestTelegramHandlers:
    """Verify handlers are properly configured."""

    def test_get_handlers_returns_list(self) -> None:
        handlers = get_handlers()
        assert isinstance(handlers, list)
        assert len(handlers) == 5

    def test_handlers_have_correct_types(self) -> None:
        from telegram.ext import CommandHandler, MessageHandler

        handlers = get_handlers()
        assert isinstance(handlers[0], CommandHandler)
        assert isinstance(handlers[1], CommandHandler)
        assert isinstance(handlers[2], CommandHandler)
        assert isinstance(handlers[3], CommandHandler)
        assert isinstance(handlers[4], MessageHandler)

    def test_create_bot_valid_token(self) -> None:
        app = create_bot("test:token")
        assert isinstance(app, Application)

    def test_create_bot_empty_token(self) -> None:
        """Empty token should raise InvalidToken."""
        with pytest.raises(InvalidToken):
            create_bot("")


class TestFormatMediaCaption:
    """Caption formatting for media delivery (like @ew_insta_bot)."""

    def test_includes_author_caption_and_url(self) -> None:
        media = MediaInfo(
            platform="instagram",
            media_type=MediaType.PHOTO,
            shortcode="ABC",
            url="https://www.instagram.com/p/ABC/",
            caption="hello world",
            author="hdshy",
        )
        text = format_media_caption(media)
        assert "@hdshy" in text
        assert "hello world" in text
        assert "https://www.instagram.com/p/ABC/" in text

    def test_empty_when_no_metadata(self) -> None:
        media = MediaInfo(
            platform="instagram",
            media_type=MediaType.PHOTO,
            shortcode="ABC",
            url="",
        )
        assert format_media_caption(media) == ""

    def test_truncates_to_telegram_limit(self) -> None:
        media = MediaInfo(
            platform="instagram",
            media_type=MediaType.PHOTO,
            shortcode="ABC",
            url="https://instagram.com/p/ABC/",
            caption="x" * 2000,
            author="user",
        )
        text = format_media_caption(media)
        assert len(text) <= 1024
        assert text.endswith("…")
