# Contributing to SocialFetch

Thank you for considering contributing to SocialFetch.

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a feature branch: `git checkout -b feature/your-feature`
4. Make your changes
5. Run tests: `pytest`
6. Run linter: `ruff check .`
7. Run formatter: `black .`
8. Commit your changes
9. Push to your fork and submit a pull request

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Code Standards

- All code must have type hints
- All public functions must have docstrings
- Write tests for every feature
- Keep commits small and focused
- Use English for all code comments

## Pull Request Process

1. Update documentation if needed
2. Ensure all CI checks pass
3. Request a review from a maintainer
4. Address review feedback

## Reporting Issues

Use the GitHub issue templates for bug reports, feature requests, and tasks.

## Security

Report security vulnerabilities privately. See [SECURITY.md](SECURITY.md).
