"""Tests for the Telegram bot module."""

import pytest
from telegram.error import InvalidToken
from telegram.ext import Application

from socialfetch.telegram.bot import create_bot
from socialfetch.telegram.handlers import get_handlers


class TestTelegramHandlers:
    """Verify handlers are properly configured."""

    def test_get_handlers_returns_list(self) -> None:
        handlers = get_handlers()
        assert isinstance(handlers, list)
        assert len(handlers) == 3

    def test_handlers_have_correct_types(self) -> None:
        from telegram.ext import CommandHandler, MessageHandler

        handlers = get_handlers()
        assert isinstance(handlers[0], CommandHandler)
        assert isinstance(handlers[1], CommandHandler)
        assert isinstance(handlers[2], MessageHandler)

    def test_create_bot_valid_token(self) -> None:
        app = create_bot("test:token")
        assert isinstance(app, Application)

    def test_create_bot_empty_token(self) -> None:
        """Empty token should raise InvalidToken."""
        with pytest.raises(InvalidToken):
            create_bot("")
