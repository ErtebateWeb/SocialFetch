# SocialFetch

Open-source self-hosted Social Media Downloader Framework.

## Features (Planned)

- **Instagram** - Download posts, stories, reels, and profile media
- **TikTok** - Download videos without watermark
- **YouTube** - Download videos and audio
- **X (Twitter)** - Download tweets, videos, and media
- Downloader plugin architecture for easy extension
- REST API for programmatic access
- Self-hosted with Docker support

## Architecture

```
socialfetch/
  core/          - Shared abstractions and interfaces
  downloaders/   - Platform-specific download implementations
  api/           - REST API layer
  config/        - Application configuration
```

Each social media platform is implemented as an independent downloader module that adheres to a common interface.

## Getting Started

```bash
git clone https://github.com/ErtebateWeb/SocialFetch.git
cd SocialFetch
./scripts/bootstrap.sh    # Linux/macOS
.\scripts\bootstrap.ps1   # Windows
```

See [docs/development.md](docs/development.md) for the full development guide.

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a pull request.

## License

MIT License. See [LICENSE](LICENSE).
