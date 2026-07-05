"""Tests for URL validation utilities."""

from __future__ import annotations

from socialfetch.shared.urls import is_valid_url


def test_valid_url_http() -> None:
    assert is_valid_url("http://example.com") is True


def test_valid_url_https() -> None:
    assert is_valid_url("https://example.com/video.mp4") is True


def test_valid_url_with_path() -> None:
    assert is_valid_url("https://www.example.com/path/to/resource") is True


def test_invalid_url_empty() -> None:
    assert is_valid_url("") is False


def test_invalid_url_whitespace() -> None:
    assert is_valid_url("   ") is False


def test_invalid_url_no_scheme() -> None:
    assert is_valid_url("example.com") is False


def test_invalid_url_random_string() -> None:
    assert is_valid_url("not-a-url") is False


def test_invalid_url_only_scheme() -> None:
    assert is_valid_url("https://") is False
