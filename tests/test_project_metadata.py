"""Regression tests for project package metadata."""

from __future__ import annotations

import tomllib
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]


def dev_requirement(name: str) -> Requirement:
    """Return one requirement from the project's ``dev`` dependency group."""
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    dev_group = pyproject.split("dev = [", maxsplit=1)[1].split("]", maxsplit=1)[0]
    requirement_lines = (line.strip().strip('",') for line in dev_group.splitlines())
    requirements = (Requirement(line) for line in requirement_lines if line)
    return next(requirement for requirement in requirements if requirement.name == name)


def test_mypy_dependency_supports_configured_python_target() -> None:
    """The dev extra must use the current mypy major without a stale ceiling."""
    mypy = dev_requirement("mypy")

    assert "2.4.1" in mypy.specifier
    assert "2.4.0" not in mypy.specifier
    assert "3.0" in mypy.specifier


def test_mypy_uses_extra_checks_without_deprecated_concatenate() -> None:
    """Keep the stricter checks without a deprecation warning (#109)."""
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["mypy"]
    assert config["extra_checks"] is True
    assert "strict_concatenate" not in config


def test_documentation_requirements_match_the_locked_project_extra() -> None:
    """The separate docs manifest must stay covered by the universal lock."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    docs = {
        str(Requirement(line))
        for line in (ROOT / "docs/requirements.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert docs == {
        str(Requirement(value))
        for value in project["project"]["optional-dependencies"]["docs"]
    }
    locked = tomllib.loads((ROOT / "uv.lock").read_text())
    versions = {item["name"]: item["version"] for item in locked["package"]}
    for value in (
        project["project"]["optional-dependencies"]["dev"]
        + project["project"]["optional-dependencies"]["docs"]
    ):
        requirement = Requirement(value)
        assert versions[requirement.name] in requirement.specifier
