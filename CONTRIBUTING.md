# Contributing to BMW Wallbox Integration

Thank you for your interest in contributing! This document provides guidelines and instructions for development.

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/JoaoPedroBelo/bmw-wallbox-ha.git
cd bmw-wallbox-ha
```

### 2. Install Development Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt
```

### 3. Install Pre-commit Hooks (Recommended)

```bash
pre-commit install
```

This will automatically run linters on every commit.

## Development Workflow

### Quick Commands

We provide a `Makefile` with common development tasks:

```bash
make help          # Show all available commands
make install       # Install development dependencies
make lint          # Run all linters
make format        # Auto-format code
make test          # Run tests
make coverage      # Run tests with coverage
make check         # Run lint + tests
make clean         # Remove generated files
```

### Manual Commands

If you prefer running commands directly:

```bash
# Linting
ruff check custom_components/ tests/              # Check for issues
ruff check custom_components/ tests/ --fix        # Fix issues automatically
ruff format custom_components/ tests/ --check     # Check formatting
ruff format custom_components/ tests/             # Format code
mypy custom_components/bmw_wallbox                # Type checking

# Testing
pytest tests/ -v                                  # Run tests
pytest tests/ --cov=custom_components.bmw_wallbox # With coverage

# Pre-commit (run all hooks)
pre-commit run --all-files
```

## Code Quality Standards

This project follows Home Assistant's code quality standards:

### Linting with Ruff

We use [Ruff](https://github.com/astral-sh/ruff) - a fast Python linter that replaces multiple tools:
- **flake8** - Code quality checks
- **isort** - Import sorting
- **pyupgrade** - Python version upgrades
- **black** - Code formatting

Configuration is in `pyproject.toml`.

### Type Checking with MyPy

We use [MyPy](https://mypy.readthedocs.io/) for static type checking:
- All functions should have type hints
- Configuration is in `pyproject.toml`

### Testing

- **100% test coverage goal** - All new code should have tests
- Use `pytest` for testing
- Use `pytest-asyncio` for async tests
- Mock external dependencies

## Coding Standards

### General Guidelines

1. **Follow PEP 8** - Python style guide
2. **Type hints required** - All functions should have type annotations
3. **Docstrings required** - All public functions should have docstrings
4. **Keep it simple** - Prefer readability over cleverness
5. **Test everything** - Write tests for new features

### Home Assistant Specific

1. **Use Home Assistant patterns** - Follow HA integration patterns
2. **Async/await** - Use async functions for I/O operations
3. **Coordinators** - Use DataUpdateCoordinator for data fetching
4. **Entity naming** - Follow HA entity naming conventions
5. **Config flow** - Use config flow for user configuration

### Import Order

Imports should be organized in this order (handled by Ruff):

```python
# Standard library
import asyncio
from datetime import datetime

# Third-party
import websockets
from ocpp.v201 import ChargePoint

# Home Assistant
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

# Local
from .const import DOMAIN
```

### Code Example

```python
"""Example module demonstrating coding standards."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant


async def example_function(
    hass: HomeAssistant,
    param1: str,
    param2: int | None = None,
) -> dict[str, Any]:
    """Do something useful.
    
    Args:
        hass: Home Assistant instance
        param1: Description of parameter 1
        param2: Optional parameter 2
        
    Returns:
        Dictionary with results
    """
    result: dict[str, Any] = {
        "param1": param1,
        "param2": param2 or 0,
    }
    return result
```

## Testing Guidelines

### Writing Tests

1. **Test file naming**: `test_<module>.py`
2. **Test function naming**: `test_<functionality>`
3. **Use fixtures**: Define reusable fixtures in `conftest.py`
4. **Mock external calls**: Don't make real network calls
5. **Test edge cases**: Not just happy paths

### Example Test

```python
"""Test example functionality."""
import pytest
from homeassistant.core import HomeAssistant

from custom_components.bmw_wallbox.sensor import BMWWallboxSensor


async def test_sensor_state(hass: HomeAssistant, mock_coordinator):
    """Test sensor returns correct state."""
    sensor = BMWWallboxSensor(mock_coordinator, mock_entry)
    
    assert sensor.native_value == "expected_value"
    assert sensor.available is True
```

## Pull Request Process

### Before Submitting

1. **Run linters**: `make lint` or `pre-commit run --all-files`
2. **Run tests**: `make test`
3. **Check coverage**: `make coverage`
4. **Update docs**: Update relevant documentation
5. **Update CHANGELOG**: Add entry to `CHANGELOG.md`

### PR Guidelines

1. **Clear title**: Describe what the PR does
2. **Description**: Explain why the change is needed
3. **Link issues**: Reference related issues
4. **Small PRs**: Keep changes focused and reviewable
5. **Tests included**: Add tests for new features
6. **No merge conflicts**: Rebase on latest main

### PR Template

```markdown
## Summary
Brief description of what this PR does.

## Changes
- Change 1
- Change 2

## Related Issues
Fixes #123

## Testing
- [ ] All tests pass
- [ ] New tests added
- [ ] Linting passes
- [ ] Tested manually
```

## Documentation

### Update Documentation

When adding features, update:
1. **README.md** - User-facing documentation
2. **CHANGELOG.md** - Version history
3. **docs/** - Technical documentation
4. **Docstrings** - Code documentation

### Documentation Style

- Use clear, concise language
- Include code examples
- Add screenshots for UI features
- Link to related documentation

## Release Process

See `custom_components/bmw_wallbox/docs/RELEASES.md` for the release process.

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (1.x.x): Breaking changes
- **MINOR** (x.1.x): New features (backwards compatible)
- **PATCH** (x.x.1): Bug fixes (backwards compatible)

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/JoaoPedroBelo/bmw-wallbox-ha/issues)
- **Discussions**: [GitHub Discussions](https://github.com/JoaoPedroBelo/bmw-wallbox-ha/discussions)
- **Documentation**: Check `custom_components/bmw_wallbox/docs/`

## Code of Conduct

- Be respectful and constructive
- Welcome newcomers
- Focus on what's best for the community
- Show empathy towards others

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to open a discussion or issue if you have questions!

