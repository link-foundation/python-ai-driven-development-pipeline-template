# Contributing to python-ai-driven-development-pipeline-template

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Development Setup

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/YOUR-USERNAME/python-ai-driven-development-pipeline-template.git
   cd python-ai-driven-development-pipeline-template
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks**

   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Development Workflow

1. **Create a feature branch**

   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make your changes**

   - Write code following the project's style guidelines
   - Add tests for any new functionality
   - Update documentation as needed

3. **Run quality checks**

   ```bash
   # Lint code
   ruff check .

   # Format code
   ruff format .

   # Type check
   mypy src/

   # Check file sizes
   python scripts/check_file_size.py

   # Run all checks together
   ruff check . && ruff format --check . && mypy src/ && python scripts/check_file_size.py
   ```

4. **Run tests**

   ```bash
   # Run tests
   pytest

   # Run tests with coverage
   pytest --cov=src --cov-report=term --cov-report=html
   ```

5. **Commit your changes**

   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

   Pre-commit hooks will automatically run and check your code.

6. **Push and create a Pull Request**

   ```bash
   git push origin feature/my-feature
   ```

   Then create a Pull Request on GitHub.

## Code Style Guidelines

This project uses:

- **Ruff** for linting and formatting (replaces black, isort, flake8)
- **mypy** for static type checking
- **pytest** for testing

### Code Standards

- Follow PEP 8 style guidelines
- Use type hints for all functions and methods
- Write docstrings for all public APIs (Google style)
- Keep functions under 50 lines when possible
- Keep files under 1000 lines
- Maintain test coverage above 80%

### Docstring Format

Use Google-style docstrings:

```python
def example_function(arg1: str, arg2: int) -> bool:
    """Brief description of the function.

    Longer description if needed.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value

    Raises:
        ValueError: Description of when this is raised
    """
    pass
```

## Testing Guidelines

- Write tests for all new features
- Maintain or improve test coverage
- Use descriptive test names
- Organize tests using classes when appropriate
- Use pytest fixtures for common setup

Example test structure:

```python
class TestMyFeature:
    """Tests for my feature."""

    def test_basic_functionality(self) -> None:
        """Test basic functionality."""
        assert my_function() == expected_result

    def test_edge_case(self) -> None:
        """Test edge case."""
        assert my_function(edge_case_input) == expected_result
```

## Pull Request Process

1. Ensure all tests pass locally
2. Update documentation if needed
3. Add an entry to CHANGELOG.md under "Unreleased"
4. Ensure the PR description clearly describes the changes
5. Link any related issues in the PR description
6. Wait for CI checks to pass
7. Address any review feedback

## Project Structure

```
.
├── .github/workflows/    # GitHub Actions CI/CD
├── examples/             # Usage examples
├── scripts/              # Utility scripts
├── src/my_package/       # Source code
│   ├── __init__.py       # Package entry point
│   └── py.typed          # Type marker file
├── tests/                # Test files
├── .pre-commit-config.yaml  # Pre-commit hooks
├── .ruff.toml            # Ruff configuration
├── pyproject.toml        # Project configuration
├── CHANGELOG.md          # Project changelog
├── CONTRIBUTING.md       # This file
└── README.md             # Project README
```

## Release Process

This project uses semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

Releases are managed through GitHub releases and PyPI publishing is handled via GitHub Actions.

## Getting Help

- Open an issue for bugs or feature requests
- Use discussions for questions and general help
- Check existing issues and PRs before creating new ones

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

Thank you for contributing!
