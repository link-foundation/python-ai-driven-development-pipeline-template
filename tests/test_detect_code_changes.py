"""Regression tests for CI change detection."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.detect_code_changes import detect_change_types


@pytest.mark.parametrize("event_name", ["pull_request", "push"])
@pytest.mark.parametrize(
    ("file_path", "docs_changed"),
    [
        ("experiments/repro.md", True),
        ("README.md", True),
        ("docs/case-studies/audit.py", True),
        ("changelog.d/20260903_fragment.md", True),
        ("experiments/repro.mjs", False),
        ("dev/log/trace.py", False),
    ],
)
def test_excluded_only_changes_do_not_activate_jobs(
    event_name: str, file_path: str, docs_changed: bool
) -> None:
    """Excluded paths must stay excluded for every automatic event type."""
    assert detect_change_types([file_path], event_name=event_name) == {
        "any-code-changed": False,
        "docs-changed": docs_changed,
    }


@pytest.mark.parametrize("event_name", ["pull_request", "push"])
def test_source_changes_activate_jobs(event_name: str) -> None:
    """Source changes must activate change-gated jobs for PRs and pushes."""
    assert detect_change_types(
        ["src/my_package/__init__.py"], event_name=event_name
    ) == {"any-code-changed": True, "docs-changed": False}


@pytest.mark.parametrize("event_name", ["pull_request", "push"])
def test_markdown_changes_activate_the_docs_gate(event_name: str) -> None:
    """A docs-only PR must flip docs-changed so validate-docs runs."""
    assert detect_change_types(["README.md"], event_name=event_name) == {
        "any-code-changed": False,
        "docs-changed": True,
    }


@pytest.mark.parametrize("event_name", ["pull_request", "push"])
@pytest.mark.parametrize("prefix", ["", "python/"])
@pytest.mark.parametrize(
    "path",
    [
        "scripts/simulate-fresh-merge.sh",
        ".secretlintrc.json",
        "src/data.json",
        "pyproject.toml",
        "config.yml",
        "config.yaml",
        "scripts/check-deprecated-packages.mjs",
        ".github/actions/artifact/index.mjs",
        ".github/actions/deploy-pages/deploy.mjs",
        "scripts/helper.js",
        "scripts/helper.cjs",
    ],
)
def test_code_and_config_changes_activate_jobs(event_name, prefix, path) -> None:
    assert detect_change_types([prefix + path], event_name=event_name) == {
        "any-code-changed": True,
        "docs-changed": False,
    }


@pytest.mark.parametrize("event_name", ["pull_request", "push"])
@pytest.mark.parametrize("prefix", ["", "python/"])
@pytest.mark.parametrize(
    "folder", ["docs", "changelog.d", "dev/log", "examples", "experiments"]
)
@pytest.mark.parametrize("extension", ["sh", "json", "js", "mjs", "cjs"])
def test_excluded_folders_win_over_code_extensions(
    event_name, prefix, folder, extension
) -> None:
    changes = detect_change_types(
        [f"{prefix}{folder}/fixture.{extension}"], event_name=event_name
    )
    assert changes == {"any-code-changed": False, "docs-changed": folder == "docs"}


def git(repo: Path, *args: str) -> str:
    """Run Git in a disposable repository."""
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Create a repository with an initial source commit."""
    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init", "-q")
    git(path, "config", "user.email", "test@example.invalid")
    git(path, "config", "user.name", "Test")
    commit(path, "src/initial.py")
    return path


def commit(repo: Path, name: str) -> str:
    """Commit one new file and return its SHA."""
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("test\n", encoding="utf-8")
    git(repo, "add", "--", name)
    git(repo, "commit", "-qm", "fixture")
    return git(repo, "rev-parse", "HEAD")


def run_detector(
    repo: Path, tmp_path: Path, event: str = "push", **env: str
) -> tuple[subprocess.CompletedProcess[str], str]:
    """Run the CLI and return the GitHub output records, if any."""
    output = tmp_path / "github-output"
    output.unlink(missing_ok=True)
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "scripts/detect_code_changes.py"),
        ],
        cwd=repo,
        env=os.environ
        | {"GITHUB_OUTPUT": str(output), "GITHUB_EVENT_NAME": event}
        | env,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    return completed, output.read_text() if output.exists() else ""


def test_initial_commit_uses_source_tree(repo: Path, tmp_path: Path) -> None:
    completed, output = run_detector(repo, tmp_path)
    assert completed.returncode == 0, completed.stderr
    assert "any-code-changed=true" in output


def test_shallow_parent_is_not_an_initial_commit(repo: Path, tmp_path: Path) -> None:
    commit(repo, "docs/guide.md")
    shallow = tmp_path / "shallow"
    git(tmp_path, "clone", "-q", "--depth=1", repo.as_uri(), str(shallow))
    completed, output = run_detector(shallow, tmp_path)
    assert completed.returncode != 0
    assert output == ""


@pytest.mark.parametrize("event", ["pull_request", "push"])
def test_complete_comparison_includes_earlier_source_commits(
    repo: Path, tmp_path: Path, event: str
) -> None:
    base = git(repo, "rev-parse", "HEAD")
    commit(repo, "src/éarlier.py")
    head = commit(repo, "docs/last.md")
    completed, output = run_detector(
        repo,
        tmp_path,
        event,
        GITHUB_BASE_SHA=base,
        GITHUB_HEAD_SHA=head,
        GITHUB_BEFORE_SHA=base,
    )
    assert completed.returncode == 0, completed.stderr
    assert output == "any-code-changed=true\ndocs-changed=true\n"


@pytest.mark.parametrize("event", ["pull_request", "push"])
@pytest.mark.parametrize("extension", ["js", "mjs", "cjs"])
def test_javascript_only_comparison_activates_code_gates(
    repo: Path, tmp_path: Path, event: str, extension: str
) -> None:
    base = git(repo, "rev-parse", "HEAD")
    head = commit(repo, f"scripts/helper.{extension}")
    completed, output = run_detector(
        repo,
        tmp_path,
        event,
        GITHUB_BASE_SHA=base,
        GITHUB_HEAD_SHA=head,
        GITHUB_BEFORE_SHA=base,
    )
    assert completed.returncode == 0, completed.stderr
    assert output == "any-code-changed=true\ndocs-changed=false\n"


@pytest.mark.parametrize("add_docs", [False, True])
def test_successful_pr_comparison_can_report_no_code(
    repo: Path, tmp_path: Path, add_docs: bool
) -> None:
    base = git(repo, "rev-parse", "HEAD")
    head = commit(repo, "docs/guide.md") if add_docs else base
    completed, output = run_detector(
        repo, tmp_path, "pull_request", GITHUB_BASE_SHA=base, GITHUB_HEAD_SHA=head
    )
    assert completed.returncode == 0, completed.stderr
    assert output == f"any-code-changed=false\ndocs-changed={str(add_docs).lower()}\n"


@pytest.mark.parametrize("event", ["pull_request", "push"])
def test_renaming_code_into_docs_changes_both_paths(
    repo: Path, tmp_path: Path, event: str
) -> None:
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "config", "diff.renames", "true")
    (repo / "docs").mkdir()
    git(repo, "mv", "src/initial.py", "docs/guide.py")
    git(repo, "commit", "-qm", "move source into docs")
    completed, output = run_detector(
        repo,
        tmp_path,
        event,
        GITHUB_BASE_SHA=base,
        GITHUB_HEAD_SHA=git(repo, "rev-parse", "HEAD"),
        GITHUB_BEFORE_SHA=base,
    )
    assert completed.returncode == 0, completed.stderr
    assert output == "any-code-changed=true\ndocs-changed=true\n"


@pytest.mark.parametrize("event", ["push", "pull_request"])
def test_failed_comparison_never_emits_outputs(
    repo: Path, tmp_path: Path, event: str
) -> None:
    base = git(repo, "rev-parse", "HEAD")
    commit(repo, "src/earlier.py")
    head = commit(repo, "docs/last.md")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    mock_git = bin_dir / "git"
    mock_git.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = diff ]; then\n'
        '    for arg do [ "$arg" != "HEAD^" ] || '
        f'exec "{shutil.which("git")}" "$@"; done\n'
        "    printf 'docs/partial.md\\000'; echo 'comparison failed' >&2; exit 128\n"
        "fi\n"
        f'exec "{shutil.which("git")}" "$@"\n',
        encoding="utf-8",
    )
    mock_git.chmod(0o755)
    completed, output = run_detector(
        repo,
        tmp_path,
        event,
        GITHUB_BASE_SHA=base,
        GITHUB_HEAD_SHA=head,
        GITHUB_BEFORE_SHA=base,
        PATH=f"{bin_dir}:{os.environ['PATH']}",
    )
    assert completed.returncode != 0
    assert "comparison failed" in completed.stderr
    assert output == ""
