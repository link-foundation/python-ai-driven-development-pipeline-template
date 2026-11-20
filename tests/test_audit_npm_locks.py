"""Exercise the audit CLI's Git inventory and npm status handling offline."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit-npm-locks.sh"


def mock_executable(path: Path, shell: str) -> None:
    path.write_text(f"#!/bin/sh\n{shell}\n", encoding="utf-8")
    path.chmod(0o755)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    return tmp_path


def run_audit(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=repo,
        env=os.environ
        | {"PATH": f"{repo / 'bin'}:{os.environ['PATH']}", "NPM_AUDIT_LEVEL": "high"},
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )


@pytest.mark.parametrize("args", [(), ("--list",)])
@pytest.mark.parametrize("partial", [False, True])
def test_git_failure_aborts_before_listing_or_auditing(
    repo: Path, args: tuple[str, ...], partial: bool
) -> None:
    bin_dir = repo / "bin"
    bin_dir.mkdir()
    mock_executable(
        bin_dir / "git",
        ("printf 'package-lock.json\\000'\n" if partial else "") + "exit 128",
    )
    mock_executable(bin_dir / "npm", "echo npm-should-not-run; exit 0")
    result = run_audit(repo, *args)
    assert result.returncode == 128
    assert result.stdout == ""


def test_empty_inventory_succeeds(repo: Path) -> None:
    result = run_audit(repo)
    assert result.returncode == 0
    assert "nothing to audit" in result.stdout
    assert run_audit(repo, "--list").stdout == ""


def test_audit_continues_after_a_failed_lock(repo: Path) -> None:
    bin_dir = repo / "bin"
    bin_dir.mkdir()
    mock_executable(
        bin_dir / "npm",
        'printf "auditing %s with %s\\n" "${PWD##*/}" "$*"\n'
        '[ "${PWD##*/}" != "first lock" ]',
    )
    for directory in ("first lock", "second-é", "untracked"):
        path = repo / directory
        path.mkdir()
        (path / "package-lock.json").touch()
        if directory != "untracked":
            subprocess.run(["git", "add", "--", directory], cwd=repo, check=True)
    listed = run_audit(repo, "--list")
    assert listed.stdout.splitlines() == [
        "first lock/package-lock.json",
        "second-é/package-lock.json",
    ]
    result = run_audit(repo)
    assert result.returncode == 1
    for directory in ("first lock", "second-é"):
        assert (
            f"auditing {directory} with audit --package-lock-only --audit-level=high"
            in result.stdout
        )
    assert "untracked" not in result.stdout
