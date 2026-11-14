#!/usr/bin/env python3
"""Resolve and audit every Python dependency surface supported by the template.

The audit uses the committed uv lock as constraints for every dependency surface.
The target starts without a bundled pip (issue #68); only the explicitly declared,
locked pip tool is included, so an old virtualenv seed cannot create a false
positive. Reports stream to the caller even when vulnerabilities cause failure.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

PIP_AUDIT_VERSION = "2.10.1"
DEPENDENCY_SURFACES = ("pyproject.toml", "docs/requirements.txt", "uv.lock")


def run(command: list[str], *, cwd: Path, capture: bool = False) -> str:
    """Run a command, streaming output so failures stay visible.

    pip-audit prints its advisory table on stdout and then exits non-zero;
    capturing that stdout under check=True threw the table away exactly when
    it mattered (issue #68). Stream by default and capture only when the
    caller needs the output value.
    """
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture,
    )
    output = completed.stdout.strip() if capture else ""
    if output:
        print(output)
    return output


def python_executable(venv: Path) -> Path:
    """Return the Python executable for a virtual environment."""
    scripts_directory = "Scripts" if sys.platform == "win32" else "bin"
    executable = "python.exe" if sys.platform == "win32" else "python"
    return venv / scripts_directory / executable


def project_install_target(project_root: Path) -> str:
    """Build an install target that resolves every declared optional extra."""
    pyproject_path = project_root / "pyproject.toml"
    with pyproject_path.open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)
    extras = sorted(pyproject.get("project", {}).get("optional-dependencies", {}))
    return f".[{','.join(extras)}]" if extras else "."


def audit_dependencies(project_root: Path) -> None:
    """Resolve application dependencies in isolation and audit the result."""
    missing = [
        surface
        for surface in DEPENDENCY_SURFACES
        if not (project_root / surface).is_file()
    ]
    if missing:
        message = f"Unmapped or missing dependency surfaces: {', '.join(missing)}"
        raise FileNotFoundError(message)

    with tempfile.TemporaryDirectory(prefix="dependency-audit-") as temporary:
        temporary_root = Path(temporary)
        target_venv = temporary_root / "target"
        audit_venv = temporary_root / "audit"
        # Avoid an untracked bundled pip. The locked tools extra supplies the
        # current pip explicitly, through the host interpreter's --python.
        run(
            [sys.executable, "-m", "venv", "--without-pip", str(target_venv)],
            cwd=project_root,
        )
        run([sys.executable, "-m", "venv", str(audit_venv)], cwd=project_root)

        constraints = temporary_root / "locked-requirements.txt"
        run(
            [
                sys.executable,
                "-m",
                "uv",
                "export",
                "--locked",
                "--all-extras",
                "--no-emit-project",
                "--no-hashes",
                "--output-file",
                str(constraints),
            ],
            cwd=project_root,
        )
        target_python = python_executable(target_venv)
        audit_python = python_executable(audit_venv)
        run(
            [
                sys.executable,
                "-m",
                "pip",
                "--python",
                str(target_python),
                "install",
                "-c",
                str(constraints),
                project_install_target(project_root),
            ],
            cwd=project_root,
        )
        run(
            [
                sys.executable,
                "-m",
                "pip",
                "--python",
                str(target_python),
                "install",
                "-c",
                str(constraints),
                "-r",
                "docs/requirements.txt",
            ],
            cwd=project_root,
        )
        run(
            [
                str(audit_python),
                "-m",
                "pip",
                "install",
                "-c",
                str(constraints),
                f"pip-audit=={PIP_AUDIT_VERSION}",
            ],
            cwd=project_root,
        )
        site_packages = run(
            [
                str(target_python),
                "-c",
                "import sysconfig; print(sysconfig.get_paths()['purelib'])",
            ],
            cwd=project_root,
            capture=True,
        )
        run(
            [
                str(audit_python),
                "-m",
                "pip_audit",
                "--path",
                site_packages,
                "--skip-editable",
            ],
            cwd=project_root,
        )


if __name__ == "__main__":
    audit_dependencies(Path(__file__).resolve().parents[1])
