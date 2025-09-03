# Development Guide

## Prerequisites
- Python 3.9+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Setup Development Environment

```bash
git clone https://github.com/buildermethods/agent-os.git
cd agent-os

# Install all dependencies
uv sync --all-extras

# Install in development mode (editable install)
make dev

# Use CLI with uv run:
uv run agentos --help

# Or activate virtual environment for direct access:
source .venv/bin/activate
agentos --help
```

## Running Tests

```bash
# Run full test suite
make test

# Run with coverage
make coverage

# Run pre-CI checks (format, lint, typecheck, test)
make pre-ci

# Individual commands
make format      # Format code with black
make lint        # Lint with ruff  
make typecheck   # Type check with mypy
```

## Project Structure

```
agent-os/
├── src/agentos/           # Main package
│   ├── __init__.py        # Package initialization
│   ├── cli.py             # CLI interface (Typer)
│   ├── types.py           # Type definitions (Pydantic)
│   └── core/              # Core modules
│       ├── config.py      # Configuration management
│       ├── installer.py   # Installation logic
│       └── shell.py       # Shell script execution
├── tests/                 # Test suite (143 tests, 90% coverage)
├── scripts/               # Installation shell scripts
└── specs/                 # Project specifications
```

## Code Quality Standards

- **Type Safety**: 100% mypy coverage required
- **Test Coverage**: >90% test coverage required  
- **Code Style**: Black formatting and Ruff linting required
- **Security**: All user inputs validated, safe subprocess execution