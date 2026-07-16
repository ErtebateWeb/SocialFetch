#!/usr/bin/env python3
"""Run the SocialFetch REST API server."""
import logging
import os

from socialfetch.services.api import serve

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    host = os.getenv("SOCIALFETCH__API_HOST", "127.0.0.1")
    port = int(os.getenv("SOCIALFETCH__API_PORT", "8080"))
    logger.info("Starting SocialFetch API on %s:%s", host, port)
    serve(host=host, port=port)


if __name__ == "__main__":
    main()
