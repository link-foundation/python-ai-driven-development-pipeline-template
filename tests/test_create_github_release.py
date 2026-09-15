"""Tests for scripts/create_github_release.py."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent / "scripts" / "create_github_release.py"
)
spec = importlib.util.spec_from_file_location("create_github_release", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)  # type: ignore[union-attr]


def test_detect_python_layout_treats_root_manifest_as_single_language(tmp_path) -> None:
    """A root pyproject.toml means the Python package owns the repository."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "my-package"\nversion = "1.2.3"\n',
        encoding="utf-8",
    )

    layout = module.detect_python_layout(tmp_path)

    assert layout.root == tmp_path
    assert layout.multi_language is False


def test_detect_python_layout_treats_python_subdir_as_multi_language(tmp_path) -> None:
    """A python/pyproject.toml means releases share a multi-language namespace."""
    python_root = tmp_path / "python"
    python_root.mkdir()
    (python_root / "pyproject.toml").write_text(
        '[project]\nname = "my-package"\nversion = "1.2.3"\n',
        encoding="utf-8",
    )

    layout = module.detect_python_layout(tmp_path)

    assert layout.root == python_root
    assert layout.multi_language is True


def test_release_naming_uses_py_namespace_for_multi_language_layout() -> None:
    """Multi-language Python releases should use a namespaced tag and title."""
    assert module.build_release_tag("1.2.3", multi_language=True) == "py_v1.2.3"
    assert (
        module.build_release_title(
            "1.2.3",
            distribution_name="my-package",
            multi_language=True,
        )
        == "[Python] 1.2.3"
    )


def test_release_naming_keeps_plain_tag_and_package_title_for_single_language() -> None:
    """Single-language Python releases should keep the historical convention."""
    assert module.build_release_tag("1.2.3", multi_language=False) == "v1.2.3"
    assert (
        module.build_release_title(
            "1.2.3",
            distribution_name="my-package",
            multi_language=False,
        )
        == "my-package 1.2.3"
    )


def test_release_naming_is_idempotent_for_prefixed_versions() -> None:
    """Re-running on a prefixed version must not double-prefix tags or titles."""
    assert module.build_release_tag("py_v1.2.3", multi_language=True) == "py_v1.2.3"
    assert module.build_release_tag("py-v1.2.3", multi_language=True) == "py_v1.2.3"
    assert module.build_release_tag("v1.2.3", multi_language=False) == "v1.2.3"
    assert module.normalize_version("rust_v0.2.0") == "0.2.0"


def test_build_pypi_badge_links_to_exact_version_page() -> None:
    """PyPI badge should point at the exact published version, not the project."""
    badge = module.build_pypi_badge("my-package", "py_v1.2.3")

    assert "img.shields.io" in badge
    assert "https://pypi.org/project/my-package/1.2.3/" in badge
    assert "py_v1.2.3" not in badge


def test_create_release_uses_layout_aware_tag_and_title(monkeypatch) -> None:
    """Release creation should derive tag and title from the detected layout."""
    commands = []

    def fake_run_command(cmd, check=True):
        commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(module, "run_command", fake_run_command)

    module.create_release(
        version="1.2.3",
        repository="owner/repo",
        release_notes="Release notes",
        prerelease=False,
        distribution_name="my-package",
        multi_language=True,
    )

    assert commands == [
        [
            "gh",
            "release",
            "create",
            "py_v1.2.3",
            "--repo",
            "owner/repo",
            "--title",
            "[Python] 1.2.3",
            "--notes",
            "Release notes",
        ],
    ]


def test_create_release_caps_oversized_release_notes(monkeypatch) -> None:
    """Release creation should avoid sending oversized notes to GitHub."""
    commands = []
    oversized_notes = (
        "Important release summary\n\n"
        + ("Multi-byte change entry: café\n" * 3_000)
        + "\nTail marker that should be omitted"
    )

    def fake_run_command(cmd, check=True):
        commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(module, "run_command", fake_run_command)

    module.create_release(
        version="1.2.3",
        repository="owner/repo",
        release_notes=oversized_notes,
        prerelease=False,
        distribution_name="my-package",
        multi_language=True,
    )

    release_notes = commands[0][commands[0].index("--notes") + 1]

    assert len(release_notes.encode("utf-8")) <= module.MAX_RELEASE_NOTES_BYTES
    assert release_notes.startswith("Important release summary")
    assert "Tail marker that should be omitted" not in release_notes
    assert "Release notes were truncated" in release_notes
    assert "https://github.com/owner/repo/blob/py_v1.2.3/CHANGELOG.md" in release_notes


def test_untrusted_release_notes_are_bracketed_in_actions_logs(
    monkeypatch, capsys
) -> None:
    """A changelog's legacy workflow command must remain inert everywhere."""
    payload = "A note quoting ##[error]injected by a pull request"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(
        module,
        "run_command",
        lambda cmd, check=True: subprocess.CompletedProcess(cmd, 0, "", ""),
    )

    module.create_release("1.2.3", "owner/repo", payload)

    output = capsys.readouterr().out
    token_match = re.search(r"::stop-commands::([0-9a-f]{32})", output)
    assert token_match, output
    token = token_match.group(1)
    assert output.index(f"::stop-commands::{token}") < output.index(payload)
    assert output.index(payload) < output.index(f"::{token}::")


def test_logged_release_command_cannot_reinject_notes(monkeypatch, capsys) -> None:
    """The ``gh --notes`` argv log is guarded as well as the notes preview."""
    payload = "##[stop-commands]attacker-token"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, "", ""),
    )

    module.run_command(["gh", "release", "create", "v1", "--notes", payload])

    output = capsys.readouterr().out
    assert payload in output
    assert re.search(
        r"::stop-commands::([0-9a-f]{32})\n.*##\[stop-commands\].*\n::\1::",
        output,
        re.DOTALL,
    )


def test_subprocess_output_cannot_inject_runner_commands(monkeypatch, capsys) -> None:
    """Command output uses matching guards on its original output stream."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(
            cmd,
            1,
            "tool said ##[add-mask]secret",
            "tool said ##[error]failure",
        ),
    )

    module.run_command(["tool"], check=False)

    captured = capsys.readouterr()
    for stream, payload in (
        (captured.out, "tool said ##[add-mask]secret"),
        (captured.err, "tool said ##[error]failure"),
    ):
        assert re.search(
            rf"::stop-commands::(?P<token>[0-9a-f]{{32}})\n"
            rf"{re.escape(payload)}\n::(?P=token)::",
            stream,
        ), stream


def test_untrusted_output_stays_plain_outside_github_actions(
    monkeypatch, capsys
) -> None:
    """Local users should not see runner-specific control markers."""
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    module.print_untrusted("ordinary local output")

    assert capsys.readouterr().out == "ordinary local output\n"


def test_append_pypi_badge_if_missing_adds_linked_version_badge() -> None:
    """Release notes should get a linked PyPI badge before gh creates the release."""
    body = module.append_pypi_badge_if_missing("Release notes", "my-package", "1.2.3")

    assert "Release notes" in body
    assert "https://img.shields.io" in body
    assert "https://pypi.org/project/my-package/1.2.3/" in body


def test_append_pypi_badge_if_missing_does_not_duplicate_badge() -> None:
    """Existing shields.io badges should be preserved without duplication."""
    existing = (
        "Release notes\n\n"
        "[![PyPI](https://img.shields.io/badge/pypi-1.2.3-blue.svg)]"
        "(https://pypi.org/project/my-package/1.2.3/)"
    )

    assert (
        module.append_pypi_badge_if_missing(existing, "my-package", "1.2.3") == existing
    )
