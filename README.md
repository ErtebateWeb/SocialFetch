# SocialFetch

Open-source self-hosted Social Media Downloader Framework.

## Features (Planned)

- **Instagram** - Download posts, stories, reels, and profile media
- **TikTok** - Download videos without watermark
- **YouTube** - Download videos and audio
- **X (Twitter)** - Download tweets, videos, and media
- Provider plugin architecture for easy extension
- REST API for programmatic access
- Self-hosted with Docker support

## Architecture

```
SocialFetch follows a provider-based architecture:

app/
  core/          - Shared abstractions and interfaces
  providers/     - Platform-specific download implementations
  api/           - REST API layer
  config/        - Application configuration
```

Each social media platform is implemented as an independent provider module that adheres to a common interface. This design keeps providers decoupled and testable in isolation.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/ErtebateWeb/SocialFetch.git
cd SocialFetch

# Create and activate virtual environment
python -m venv .venv
py -3.11 -m  vemv .venv    # Use Python 3.11 
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Copy environment variables
cp .env.example .env

# Run tests
pytest

# Run linter
ruff check .

# Run formatter check
black --check .
```

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the project roadmap and planned milestones.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a pull request.
