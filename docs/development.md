# Development Guide

## Requirements

- Python 3.11+
- Git

## Quick Start

### Bootstrap (Recommended)

Run the bootstrap script to set up everything automatically:

#### Linux / macOS

```bash
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh
```

#### Windows (PowerShell)

```powershell
.\scripts\bootstrap.ps1
```

This will:

1. Create a virtual environment in `.venv/`
2. Install the package in editable mode
3. Install all development dependencies
4. Set up pre-commit hooks

### Manual Setup

#### Linux / macOS

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install package with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Copy environment variables
cp .env.example .env
```

#### Windows (PowerShell)

```powershell
# Create virtual environment
py -3.11 -m venv .venv

# Activate it
.venv\Scripts\Activate.ps1

# Install package with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Copy environment variables
Copy-Item .env.example .env
```

## Daily Commands

### Run Tests

#### Linux / macOS

```bash
./scripts/test.sh
./scripts/test.sh --coverage
```

#### Windows (PowerShell)

```powershell
.\scripts\test.ps1
.\scripts\test.ps1 --coverage
```

Or directly:

```bash
pytest
pytest --cov --cov-report=term-missing
```

### Run Linters

#### Linux / macOS

```bash
./scripts/lint.sh
```

#### Windows (PowerShell)

```powershell
.\scripts\lint.ps1
```

Or individually:

```bash
ruff check .          # Lint
black --check .       # Format check
mypy socialfetch/     # Type check
```

### Auto-fix Issues

```bash
ruff check --fix .    # Auto-fix lint issues
black .               # Auto-format code
```

## Git Workflow

1. Create a feature branch from `main`:

   ```bash
   git checkout -b feature/your-feature
   ```

2. Make your changes.

3. Run linters and tests:

   ```bash
   ./scripts/lint.sh
   ./scripts/test.sh
   ```

4. Commit with a clear message.

5. Push and open a pull request.

## Pre-commit Hooks

Pre-commit runs automatically on `git commit`. It checks:

- Trailing whitespace
- End-of-file fixer
- YAML validation
- Large file detection
- Black formatting
- Ruff linting

To run manually:

```bash
pre-commit run --all-files
```

## Coverage

Generate a coverage report:

```bash
pytest --cov --cov-report=term-missing --cov-report=html
```

Open `htmlcov/index.html` to view the report.

## IDE Setup

### VS Code

Recommended extensions:

- Python (ms-python.python)
- Ruff (charliermarsh.ruff)
- Black (ms-python.blackFormatter)

### PyCharm

Set the Python interpreter to `.venv/Python.exe` (or `.venv/bin/python` on Linux).
