"""Application configuration via Pydantic Settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogConfig(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )


class DownloadConfig(BaseSettings):
    """Download-related settings."""

    model_config = SettingsConfigDict(extra="ignore")
    download_dir: Path = Field(
        default=Path("downloads"),
        description="Root directory for downloaded files",
    )
    temp_path: Path = Field(
        default=Path("downloads/tmp"),
        description="Temporary directory for in-progress downloads",
    )
    max_file_size_mb: int = Field(
        default=50,
        description="Maximum file size in MB for uploads",
    )


class InstagramConfig(BaseSettings):
    """Instagram-specific configuration."""

    cookies_file: Path | None = Field(
        default=None,
        description="Path to Instagram cookies file for authenticated downloads",
    )


class Settings(BaseSettings):
    """Root application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SOCIALFETCH__",
        env_nested_delimiter="__",
        extra="ignore",
    )

    download: DownloadConfig = Field(default_factory=DownloadConfig)
    logging: LogConfig = Field(default_factory=LogConfig)
    instagram: InstagramConfig = Field(default_factory=InstagramConfig)
    telegram_api_url: str = Field(
        default="http://127.0.0.1:8081/bot",
        description="Telegram Bot API base URL (local or remote)",
    )
    proxy_url: str | None = Field(
        default="socks5h://127.0.0.1:40000",
        description="SOCKS5 proxy URL for downloaders (WARP)",
    )


# Global singleton for easy import
settings = Settings()
