"""Manual changelog fragments must survive concurrent filename collisions."""

from datetime import datetime
from pathlib import Path

import pytest

from scripts import create_manual_changeset


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
