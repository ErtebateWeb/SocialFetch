# ADR 0004: Configuration System

## Status
Accepted

## Context
The application needs configuration management supporting:
- Environment variables (12-factor app)
- .env files for local development
- Type validation
- Per-platform credentials

## Decision
Use Pydantic Settings with BaseSettings:
- Single source of truth
- Automatic .env loading
- Type coercion and validation
- Hierarchical config via nested models

## Consequences
- No runtime config errors due to type mismatch
- Clear documentation via model fields
- Easy to add new settings
