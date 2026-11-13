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

   If you changed public APIs or docstrings, build the documentation locally to
   make sure Sphinx still renders without warnings:

   ```bash
   pip install -e ".[docs]"
   sphinx-build -W --keep-going -b html docs _site
   ```

5. **Add a changelog fragment**

   For any user-facing changes, create a changelog fragment:

   ```bash
   # Create a new changelog fragment (similar to `npx changeset` in JS)
   scriv create
   ```

   This will create a new file in `changelog.d/`. Edit it to document your changes:

   ```markdown
   ### Added
   - Description of new feature

   ### Fixed
   - Description of bug fix
   ```

   **Why fragments?** This prevents merge conflicts in CHANGELOG.md when multiple PRs are open simultaneously (same as Changesets in JavaScript).

6. **Commit your changes**

   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

   Pre-commit hooks will automatically run and check your code.

7. **Push and create a Pull Request**

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
- Python, shell, JavaScript and MJS files warn above 900 lines and fail above
  1000; Markdown warns above 2250 and fails above 2500.
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
3. Add a changelog fragment with `scriv create` (see step 5 in Development Workflow)
4. Ensure the PR description clearly describes the changes
5. Link any related issues in the PR description
6. Wait for CI checks to pass
7. Address any review feedback

## Changelog Management

Built distributions are checked after `twine check` and before every PyPI upload,
including `scripts/publish_to_pypi.py`. Run `python scripts/check_dist_size.py`
locally after building. Each file has a conservative 99,000,000-byte budget;
set the `DIST_SIZE_LIMIT_BYTES` repository variable for CI, the environment
variable locally, or pass `--max-bytes` for a different project limit.
The gate reports the largest individual file as `dist_size_bytes` in
`GITHUB_OUTPUT` and lists the ten largest archive members on a failure.
Missing distributions also fail. PyPI's project storage quota is separate from
this per-file gate.

If main advances during a manual release, the release script dispatches
`release.yml` on main with the original bump type and description. The new run
validates the new source before releasing; the old run skips publication.
The manual release job therefore needs `actions: write` and `GH_TOKEN` in
addition to its existing publishing permissions. A failed dispatch fails the
job visibly. No unvalidated source is rebased into the release.

When updating lychee, review and update `LYCHEE_VERSION` and both architecture
SHA-256 pins together in `.github/workflows/links.yml`. The installer checks
the archive against those pins as well as the release checksum. Local callers
must supply the same pins via `LYCHEE_SHA256_X86_64` and
`LYCHEE_SHA256_AARCH64`.

This project uses [Scriv](https://scriv.readthedocs.io/) for changelog management, which works similarly to [Changesets](https://github.com/changesets/changesets) in JavaScript projects.

### Creating a Fragment

```bash
# Install scriv (included in dev dependencies)
pip install -e ".[dev]"

# Create a new fragment
scriv create
```

### Fragment Categories

Use these categories in your fragments:

- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Features that will be removed in future
- **Removed**: Features that were removed
- **Fixed**: Bug fixes
- **Security**: Security-related changes

### During Release

Fragments are automatically collected into CHANGELOG.md during the release process. The release workflow:

1. Bumps the version in pyproject.toml
2. Collects all fragments with `scriv collect --version` using the new version
3. Updates CHANGELOG.md and removes processed fragment files
4. Commits the version and changelog together
5. Publishes to PyPI
6. Creates a git tag and GitHub release

## Project Structure

```
.
├── .github/workflows/    # GitHub Actions CI/CD
├── changelog.d/          # Changelog fragments (like .changeset/)
│   ├── README.md         # Fragment instructions
│   └── *.md              # Individual changelog fragments
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
