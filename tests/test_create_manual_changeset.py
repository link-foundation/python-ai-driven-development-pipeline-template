"""Regression tests for identifying and preserving manual changelog fragments."""

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from scripts import create_manual_changeset


def test_scriv_reports_the_created_path_to_the_cli(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    creator = shutil.copy(create_manual_changeset.__file__, scripts)
    (tmp_path / "pyproject.toml").write_text(
        '[tool.scriv]\nformat = "md"\nfragment_directory = "changelog.d"\n',
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "init", "-q", "-b", "topic"], cwd=tmp_path, check=True, timeout=5
    )
    for key, value in (
        ("user.name", "Fragment Test"),
        ("user.email", "test@example.invalid"),
        ("scriv.create.add", "false"),
        ("scriv.create.edit", "false"),
    ):
        subprocess.run(
            ["git", "config", key, value], cwd=tmp_path, check=True, timeout=5
        )
    result = subprocess.run(
        [sys.executable, creator, "minor", "--description", "A new feature"],
        cwd=tmp_path,
        env=os.environ
        | {
            "PATH": os.pathsep.join(
                (str(Path(sys.executable).parent), os.environ["PATH"])
            )
        },
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    (fragment,) = (tmp_path / "changelog.d").glob("*.md")
    assert fragment.read_text(encoding="utf-8") == "### Added\n\n- A new feature\n"


@pytest.mark.parametrize(
    ("created", "reported", "description", "success"),
    [
        (("new.md",), "new.md", "Later patch", True),
        (("new.md",), "new.md", "", True),
        ((), "new.md", "Later patch", False),
        (("new.md", "concurrent.md"), "new.md", "Later patch", False),
        (("concurrent.md",), "new.md", "Later patch", False),
        (("concurrent.md",), "earlier.md", "Later patch", False),
    ],
)
def test_scriv_only_updates_its_new_fragment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    created: tuple[str, ...],
    reported: str,
    description: str,
    success: bool,
) -> None:
    monkeypatch.chdir(tmp_path)
    directory = Path("changelog.d")
    directory.mkdir()
    earlier = directory / "earlier.md"
    original = b"### Added\n\n- Earlier feature\n"
    earlier.write_bytes(original)
    os.utime(earlier, (1_900_000_000, 1_900_000_000))
    draft = b"Scriv draft\n"

    def run_scriv(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert args == ["scriv", "create"]
        for name in created:
            fragment = directory / name
            fragment.write_bytes(draft)
            os.utime(fragment, (1_700_000_000, 1_700_000_000))
        return subprocess.CompletedProcess(
            args, 0, "", f"Creating {directory / reported}\n"
        )

    monkeypatch.setattr(create_manual_changeset.subprocess, "run", run_scriv)
    status = create_manual_changeset.create_with_scriv("patch", description)

    assert earlier.read_bytes() == original
    assert (status == 0) == success
    for name in created:
        expected = b"### Fixed\n\n- Later patch\n" if success and description else draft
        assert (directory / name).read_bytes() == expected
    if not success:
        assert "Cannot identify the new Scriv fragment" in capsys.readouterr().err


def test_same_second_collision_preserves_the_first_fragment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class FrozenDatetime:
        @staticmethod
        def now() -> datetime:
            return datetime(2026, 11, 20, 12, 0, 0)

    monkeypatch.setattr(create_manual_changeset, "datetime", FrozenDatetime)
    monkeypatch.setattr(
        create_manual_changeset, "__file__", str(tmp_path / "scripts/creator.py")
    )
    monkeypatch.setattr(create_manual_changeset, "get_username", lambda: "author")
    monkeypatch.setattr(create_manual_changeset, "get_branch_name", lambda: "topic")
    monkeypatch.setattr(
        "sys.argv", ["creator.py", "minor", "--no-scriv", "-d", "Earlier feature"]
    )
    assert create_manual_changeset.main() == 0
    [fragment] = (tmp_path / "changelog.d").glob("*.md")
    original = b"### Added\n\n- Earlier feature\n"
    assert fragment.read_bytes() == original

    monkeypatch.setattr(
        "sys.argv", ["creator.py", "patch", "--no-scriv", "-d", "Later patch"]
    )
    assert create_manual_changeset.main() != 0
    assert fragment.read_bytes() == original
    assert "already exists" in capsys.readouterr().err
