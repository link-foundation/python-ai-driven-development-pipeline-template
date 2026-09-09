"""Tests for scripts/version_and_commit.py (issue #67)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent / "scripts" / "version_and_commit.py"
)
spec = importlib.util.spec_from_file_location("version_and_commit", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)  # type: ignore[union-attr]


def test_parse_version_reads_project_table_not_other_tables() -> None:
    """A version key in another table must not shadow project.version."""
    content = """
[tool.scriv]
version = "scripted"

[project]
name = "example"
version = "2.3.4"
"""
    assert module.parse_version(content) == "2.3.4"


def test_parse_version_fails_loudly_when_project_version_is_missing() -> None:
    import pytest

    with pytest.raises(ValueError, match="no project.version"):
        module.parse_version("[project]\nname = 'example'\n")


def test_parse_version_fails_loudly_on_invalid_toml() -> None:
    import pytest

    with pytest.raises(ValueError, match="not valid TOML"):
        module.parse_version("not toml at all ][")


def test_get_current_version_reads_file(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nversion = '3.1.4'\n")
    assert module.get_current_version(pyproject) == "3.1.4"
