# ADR 0008: Configuration System

## Status
Accepted

## Context
The application needs a robust configuration system supporting:
- Environment variables (12-factor app)
- .env files for local development
- Type validation and coercion
- Per-platform credentials (cookies, tokens)
- Download path management

## Decision
Use **Pydantic Settings v2** (`BaseSettings`):
- Automatic `.env` file loading
- Type coercion with validation
- Nested models for logical grouping
- Immutable config after initialization

## Implementation
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    download: DownloadConfig
    logging: LogConfig
    instagram: InstagramConfig = InstagramConfig()
```

## Consequences
- No runtime config errors due to type mismatch
- Self-documenting via model fields
- Easy to add new providers
- Slightly more complex than flat env vars
