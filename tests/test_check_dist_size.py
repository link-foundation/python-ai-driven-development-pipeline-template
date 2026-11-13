"""Small archive regressions for the per-file PyPI upload gate."""

import io
import os
import subprocess
import sys
import tarfile
import zipfile

import pytest

from scripts.check_dist_size import DEFAULT_MAX_BYTES, check_dist_size, largest_members
from scripts import publish_to_pypi
from tests.workflow_helpers import (
    ROOT,
    read_workflow,
    workflow_job_block,
    workflow_step_block,
)


@pytest.mark.parametrize("kind", ["whl", "tar.gz"])
def test_archive_boundaries_and_largest_members(tmp_path, monkeypatch, capsys, kind):
    archive = tmp_path / f"package.{kind}"
    members = [(f"data-{i}", b"x" * i) for i in range(1, 15)]
    if kind == "whl":
        with zipfile.ZipFile(archive, "w") as bundle:
            for name, data in members:
                bundle.writestr(name, data)
    else:
        with tarfile.open(archive, "w:gz") as bundle:
            for name, data in members:
                entry = tarfile.TarInfo(name)
                entry.size = len(data)
                bundle.addfile(entry, io.BytesIO(data))
    output = tmp_path.parent / f"{kind}-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    size = archive.stat().st_size
    assert check_dist_size(tmp_path, size)
    assert not check_dist_size(tmp_path, size - 1)
    assert output.read_text() == f"dist_size_bytes={size}\n" * 2
    assert largest_members(archive) == [(i, f"data-{i}") for i in range(14, 4, -1)]
    report = capsys.readouterr().out
    assert "::error title=Distribution size::" in report
    assert archive.name in report and "data-14" in report


def test_every_file_is_checked_and_output_is_largest_not_total(tmp_path, monkeypatch):
    (tmp_path / "one.whl").write_bytes(b"x" * 20)
    (tmp_path / "two.tar.gz").write_bytes(b"x" * 30)
    output = tmp_path.parent / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    assert check_dist_size(tmp_path, 30)
    assert output.read_text() == "dist_size_bytes=30\n"
    assert not check_dist_size(tmp_path, 29)  # Invalid archive still fails closed.


def test_empty_or_missing_distribution_fails(tmp_path):
    assert not check_dist_size(tmp_path)
    assert not check_dist_size(tmp_path / "missing")


@pytest.mark.parametrize("budget", ["0", "-1", "invalid", "19", "20"])
def test_cli_environment_budget(tmp_path, budget):
    (tmp_path / "package.whl").write_bytes(b"x" * 20)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_dist_size.py"),
            "--dist-dir",
            str(tmp_path),
        ],
        env={**os.environ, "DIST_SIZE_LIMIT_BYTES": budget},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert (result.returncode == 0) == (budget == "20")
    assert DEFAULT_MAX_BYTES < 100_000_000


def test_local_publish_rejects_large_distribution_before_upload(tmp_path, monkeypatch):
    (tmp_path / "package.whl").write_bytes(b"x" * 20)
    monkeypatch.setenv("DIST_SIZE_LIMIT_BYTES", "19")
    with pytest.raises(SystemExit):
        publish_to_pypi.publish_package(tmp_path)


def test_workflow_gates_build_and_both_uploads():
    workflow = read_workflow("release.yml")
    for job_name in ("build", "manual-release"):
        job = workflow_job_block(workflow, job_name)
        check = workflow_step_block(job, "Check package")
        assert check.index("twine check") < check.index(
            "python scripts/check_dist_size.py"
        )
        assert job.index("python scripts/check_dist_size.py") < job.index(
            "- name: Upload artifacts"
            if job_name == "build"
            else "- name: Publish to PyPI"
        )
    auto = workflow_job_block(workflow, "auto-release")
    assert auto.index("--dist-dir dist") < auto.index("- name: Publish to PyPI")
