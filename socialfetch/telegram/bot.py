"""SocialFetch Telegram bot application."""

import logging

from telegram import BotCommand
from telegram.ext import Application

from socialfetch.telegram.handlers import get_handlers

logger = logging.getLogger(__name__)


def create_bot(token: str) -> Application:
    app = Application.builder().token(token).post_init(_post_init).build()
    for handler in get_handlers():
        app.add_handler(handler)
    return app


async def _post_init(app: Application) -> None:
    commands = [
        BotCommand("start", "Welcome message"),
        BotCommand("help", "Usage instructions"),
    ]
    await app.bot.set_my_commands(commands)
    logger.info("Bot commands registered")


def run_bot(token: str) -> None:
    app = create_bot(token)
    logger.info("Starting SocialFetch bot...")
    app.run_polling(allowed_updates=["message"])
