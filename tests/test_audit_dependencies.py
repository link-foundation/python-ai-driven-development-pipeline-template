"""Tests for scripts/audit_dependencies.py (issue #68)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent / "scripts" / "audit_dependencies.py"
)
spec = importlib.util.spec_from_file_location("audit_dependencies", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)  # type: ignore[union-attr]


def test_run_streams_output_when_the_command_fails(capfd) -> None:
    """A failing tool must not swallow its own report.

    pip-audit prints the advisory table on stdout and then exits non-zero;
    capturing stdout under check=True discarded the table exactly when it
    mattered. The default must stream, so the table survives.
    """
    try:
        module.run(
            [sys.executable, "-c", "print('advisory table'); raise SystemExit(1)"],
            cwd=Path.cwd(),
        )
    except subprocess.CalledProcessError:
        pass
    else:
        raise AssertionError("run() should propagate a non-zero exit")

    assert "advisory table" in capfd.readouterr().out


def test_run_captured_mode_returns_output() -> None:
    output = module.run(
        [sys.executable, "-c", "print('purelib path')"],
        cwd=Path.cwd(),
        capture=True,
    )
    assert output == "purelib path"


def test_target_venv_is_created_without_pip(monkeypatch) -> None:
    """Auditing a bundled pip reports tool advisories as if they were ours."""
    commands: list[list[str]] = []

    def fake_run(command, *, cwd, capture=False):
        commands.append([str(part) for part in command])
        return "purelib"

    monkeypatch.setattr(module, "run", fake_run)

    project_root = Path(__file__).resolve().parent.parent
    module.audit_dependencies(project_root)

    target_creation = next(
        command for command in commands if command[-1].endswith("target")
    )
    assert "--without-pip" in target_creation

    # Installs into the pip-less target go through the host interpreter's pip
    # with --python, so pip itself never lands in the audit scope. The audit
    # venv's own pip-audit install is deliberately excluded from that claim.
    target_installs = [
        command
        for command in commands
        if command[0] == sys.executable
        and "install" in command
        and "venv" not in command
    ]
    assert len(target_installs) >= 2, commands
    for command in target_installs:
        assert command[1:3] == ["-m", "pip"], command
        assert "--python" in command, command
        assert "target" in command[4], command


def test_missing_dependency_surface_fails_the_audit(tmp_path: Path) -> None:
    import pytest

    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    with pytest.raises(FileNotFoundError, match="docs/requirements.txt"):
        module.audit_dependencies(tmp_path)


def test_every_install_uses_the_committed_lock(monkeypatch) -> None:
    """Fresh audits must inspect CI's tree rather than resolving newer versions."""
    commands = []

    def fake_run(command, *, cwd, capture=False):
        commands.append(command)
        return "purelib"

    monkeypatch.setattr(module, "run", fake_run)
    module.audit_dependencies(Path(__file__).resolve().parents[1])
    export = next(command for command in commands if "export" in command)
    assert "--locked" in export
    assert "--all-extras" in export
    constraints = export[export.index("--output-file") + 1]
    installs = [command for command in commands if "install" in command]
    assert len(installs) == 3
    for command in installs:
        assert command[command.index("-c") + 1] == constraints


def test_missing_lock_is_rejected_before_any_install(tmp_path, monkeypatch) -> None:
    import pytest

    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/requirements.txt").write_text("")
    monkeypatch.setattr(
        module,
        "run",
        lambda *args, **kwargs: pytest.fail("installed before checking lock"),
    )
    with pytest.raises(FileNotFoundError, match="uv.lock"):
        module.audit_dependencies(tmp_path)
