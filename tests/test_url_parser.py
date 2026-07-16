"""Tests for the URL parser service."""

import pytest

from socialfetch.core.errors import InvalidURLError
from socialfetch.downloaders.instagram import (  # noqa: F401  trigger registry
    InstagramDownloader,
)
from socialfetch.services.url_parser import URLParser
from socialfetch.downloaders import instagram  # noqa: F401 - trigger registry


class TestURLParser:
    """Verify URL parsing and platform detection."""

    def test_parse_instagram_post(self) -> None:
        result = URLParser.parse("https://instagram.com/p/ABC123/")
        assert result.platform == "instagram"

    def test_parse_instagram_reel(self) -> None:
        result = URLParser.parse("https://www.instagram.com/reel/DEF456/")
        assert result.platform == "instagram"

    def test_parse_with_query_params(self) -> None:
        result = URLParser.parse("https://instagram.com/p/XYZ/?utm_source=share")
        assert result.platform == "instagram"

    def test_match_returns_true(self) -> None:
        assert URLParser.match("https://instagram.com/p/123/") is True

    def test_match_returns_false(self) -> None:
        assert URLParser.match("https://unknown.example.com") is False

    def test_parse_invalid_raises(self) -> None:
        with pytest.raises(InvalidURLError):
            URLParser.parse("https://youtube.com/watch?v=123")
