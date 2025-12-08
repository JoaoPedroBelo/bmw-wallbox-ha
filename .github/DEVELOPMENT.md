# Development Guide

## Quick Start

```bash
# Install dependencies
make install

# Run linters
make lint

# Auto-format code  
make format

# Run tests
make test

# Run everything
make check
```

## Tools

- **Ruff**: Fast Python linter and formatter
- **MyPy**: Static type checker
- **Pre-commit**: Git hooks for automatic checks
- **Pytest**: Testing framework

## Configuration

- `pyproject.toml`: Ruff, MyPy, Pytest configuration
- `.pre-commit-config.yaml`: Pre-commit hooks
- `Makefile`: Development commands

## See Also

- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Full contributing guide
- [TESTING.md](../../TESTING_CHECKLIST.md) - Testing checklist
