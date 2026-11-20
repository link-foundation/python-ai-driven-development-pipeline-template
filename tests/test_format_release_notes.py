"""Verify the release-notes CLI transports already-decoded example text."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/format_release_notes.py"
BODY = r"""Example with café:
```json
{"message":"hello\nworld","quote":"\"","path":"C:\repo"}
```"""


@pytest.fixture
def mock_gh(tmp_path: Path) -> Path:
    gh = tmp_path / "gh"
    gh.write_text(
        f"#!{sys.executable}\n"
        """import os
import sys
from pathlib import Path

if '--jq' in sys.argv:
    if os.environ.get('FAIL_READ'):
        sys.exit('read failed')
    print(Path('incoming.md').read_text(encoding='utf-8'))
elif 'PATCH' in sys.argv:
    if os.environ.get('FAIL_WRITE'):
        sys.exit('write failed')
    Path('patched.md').write_text(sys.argv[-1].removeprefix('body='), encoding='utf-8')
else:
    sys.exit('unexpected gh invocation')
""",
        encoding="utf-8",
    )
    gh.chmod(0o755)
    (tmp_path / "incoming.md").write_text(BODY, encoding="utf-8")
    return tmp_path


def run_formatter(path: Path, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--release-id",
            "123",
            "--version",
            "1.2.3",
            "--repository",
            "owner/repo",
            "--package-name",
            "example-package",
        ],
        cwd=path,
        env=os.environ | {"PATH": f"{path}:{os.environ['PATH']}"} | env,
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )


def test_cli_preserves_literal_escapes_and_is_idempotent(mock_gh: Path) -> None:
    first = run_formatter(mock_gh)
    assert first.returncode == 0, first.stderr
    patched = mock_gh / "patched.md"
    formatted = patched.read_text(encoding="utf-8")
    assert formatted.startswith("[![PyPI")
    assert formatted.endswith(f"\n\n{BODY}")
    patched.rename(mock_gh / "incoming.md")

    second = run_formatter(mock_gh)
    assert second.returncode == 0, second.stderr
    assert "No changes needed" in second.stdout
    assert not patched.exists()


@pytest.mark.parametrize("operation", ["READ", "WRITE"])
def test_api_failure_is_fatal(mock_gh: Path, operation: str) -> None:
    result = run_formatter(mock_gh, **{f"FAIL_{operation}": "1"})
    assert result.returncode == 1
    assert f"{operation.lower()} failed" in result.stderr
    assert not (mock_gh / "patched.md").exists()
