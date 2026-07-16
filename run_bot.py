#!/usr/bin/env python3
"""Run the SocialFetch Telegram bot."""

import logging
import os
import sys

from socialfetch.telegram.bot import create_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        sys.exit(1)

    logger.info("Starting SocialFetch bot...")
    app = create_bot(token)
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
