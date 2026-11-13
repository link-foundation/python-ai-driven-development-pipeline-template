"""Offline regression coverage for the actual installer and workflow command."""

from __future__ import annotations

import hashlib
import gzip
import http.server
import io
import os
import re
import subprocess
import tarfile
import threading

import pytest

from tests.workflow_helpers import (
    ROOT,
    read_workflow,
    workflow_job_block,
    workflow_step_block,
)


@pytest.fixture
def release_server():
    """Serve a tiny release, failing once for each download URL."""
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as bundle:
        binary = b"#!/bin/sh\necho 'lychee 0.24.2'\n"
        entry = tarfile.TarInfo("lychee-v0.24.2/lychee")
        entry.size = len(binary)
        entry.mode = 0o755
        bundle.addfile(entry, io.BytesIO(binary))
    payload = archive.getvalue()
    replaced_payload = gzip.compress(
        gzip.decompress(payload).replace(b"lychee 0.24.2", b"lychee 9.99.9")
    )
    state = {
        "requests": {},
        "bad_checksum": False,
        "always_fail": False,
        "digest": hashlib.sha256(payload).hexdigest(),
        "replace_asset": False,
    }

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            counts = state["requests"]
            counts[self.path] = counts.get(self.path, 0) + 1
            if counts[self.path] == 1 or state["always_fail"]:
                self.send_error(503)
                return
            body = replaced_payload if state["replace_asset"] else payload
            if self.path.endswith(".sha256"):
                digest = (
                    "0" * 64
                    if state["bad_checksum"]
                    else hashlib.sha256(body).hexdigest()
                )
                body = f"{digest}  release.tar.gz\n".encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", state
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def install(tmp_path, url, **overrides):
    """Run production installer with short, finite retries against loopback."""
    return subprocess.run(
        ["bash", str(ROOT / "scripts/install-lychee.sh"), str(tmp_path / "bin")],
        env={
            **os.environ,
            "LYCHEE_VERSION": "v0.24.2",
            "LYCHEE_SHA256_X86_64": overrides.pop("digest", "0" * 64),
            "LYCHEE_SHA256_AARCH64": overrides.pop("arm_digest", "0" * 64),
            "LYCHEE_DOWNLOAD_BASE_URL": url,
            "LYCHEE_DOWNLOAD_RETRY_DELAY": "1",
            "LYCHEE_DOWNLOAD_RETRIES": "1",
            "GITHUB_PATH": str(tmp_path / "path"),
            **overrides,
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )


def test_installer_retries_both_assets_and_adds_verified_binary_to_path(
    tmp_path, release_server
):
    url, state = release_server
    # Reproduce the upstream one-shot failure before running the replacement.
    original = subprocess.run(
        ["curl", "-sfL", url + "/original", "-o", str(tmp_path / "original")],
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert original.returncode == 22
    result = install(tmp_path, url, digest=state["digest"], arm_digest=state["digest"])
    assert result.returncode == 0, result.stderr
    assert "lychee 0.24.2" in result.stdout
    assert (tmp_path / "path").read_text().strip() == str(tmp_path / "bin")
    downloads = {
        path: count for path, count in state["requests"].items() if path != "/original"
    }
    assert len(downloads) == 2
    assert set(downloads.values()) == {2}


@pytest.mark.parametrize("failure", ["bad_checksum", "always_fail", "replace_asset"])
def test_installer_fails_closed(tmp_path, release_server, failure):
    url, state = release_server
    state[failure] = True
    result = install(tmp_path, url, digest=state["digest"], arm_digest=state["digest"])
    assert result.returncode != 0
    assert not (tmp_path / "bin/lychee").exists()
    assert not (tmp_path / "path").exists()
    assert (
        "Checksum mismatch" if failure != "always_fail" else "after retries"
    ) in result.stderr


@pytest.mark.parametrize("version", ["latest", "v0.24", "", "v0.24.2/other"])
def test_installer_rejects_unpinned_version(tmp_path, version):
    result = install(tmp_path, "http://127.0.0.1:1", LYCHEE_VERSION=version)
    assert result.returncode != 0
    assert not (tmp_path / "bin").exists()


@pytest.mark.parametrize("digest", ["", "abc", "G" * 64])
def test_installer_requires_committed_digest_before_downloading(
    tmp_path, release_server, digest
):
    url, state = release_server
    result = install(tmp_path, url, digest=digest, arm_digest=digest)
    assert result.returncode != 0
    assert "SHA-256 pin is required" in result.stderr
    assert not state["requests"]


def test_installer_uses_arm_pin_on_arm_runner(tmp_path, release_server):
    url, state = release_server
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    uname = stub_dir / "uname"
    uname.write_text("#!/bin/sh\necho aarch64\n")
    uname.chmod(0o755)
    result = install(
        tmp_path,
        url,
        arm_digest=state["digest"],
        PATH=f"{stub_dir}:{os.environ['PATH']}",
    )
    assert result.returncode == 0, result.stderr
    assert all("aarch64" in path for path in state["requests"])


@pytest.mark.parametrize(
    ("exit_code", "report", "expected"),
    [
        (0, "| 🔍 Total | 12 |", 0),
        (2, "| 🔍 Total | 12 |\n## Errors\n* [404] https://invalid.example", 0),
        (0, "| 🔍 Total | 0 |", 1),
        (2, "| 🔍 Total | 0 |", 1),
        (2, "", 1),
        (0, "", 1),
        (1, "| 🔍 Total | 12 |", 1),
        (101, "", 1),
        (0, "unrecognized output", 1),
    ],
)
def test_real_workflow_scan_command(tmp_path, exit_code, report, expected):
    """Execute the exact workflow command, stubbing only the lychee process."""
    binary = tmp_path / "lychee-stub"
    binary.mkdir()
    stub = binary / "lychee"
    stub.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "Path('args.json').write_text(json.dumps(sys.argv[1:]))\n"
        "if os.environ['STUB_REPORT']:\n"
        "    Path(sys.argv[sys.argv.index('--output')+1]).write_text(os.environ['STUB_REPORT'])\n"
        "sys.exit(int(os.environ['STUB_EXIT']))\n"
    )
    stub.chmod(0o755)
    output = tmp_path / "outputs"
    summary = tmp_path / "summary"
    summary.write_text("Earlier summary\n")
    # Ensure a previous report cannot hide a failed invocation.
    (tmp_path / "lychee").mkdir()
    (tmp_path / "lychee/out.md").write_text("| 🔍 Total | 999 |")
    job = workflow_job_block(read_workflow("links.yml"), "link-checker")
    step = workflow_step_block(job, "Check links with lychee")
    command = step.split("run: >-\n", 1)[1].split("        env:", 1)[0]
    command = " ".join(line.strip() for line in command.splitlines())
    command = command.replace(
        "scripts/check-links.sh", str(ROOT / "scripts/check-links.sh")
    )
    result = subprocess.run(
        ["bash", "-e", "-c", command],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{binary}:{os.environ['PATH']}",
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(summary),
            "STUB_REPORT": report,
            "STUB_EXIT": str(exit_code),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == expected, result.stdout + result.stderr
    assert output.read_text() == f"exit_code={exit_code}\n"
    assert summary.read_text() == "Earlier summary\n" + report
    args = (tmp_path / "args.json").read_text()
    for flag in [
        "--config",
        "--hidden",
        "--cache",
        "--extensions",
        "--max-retries",
        "--format",
    ]:
        assert flag in args
    assert "scripts/fixtures" in args
    assert re.search(r"steps.lychee.outcome == 'success'", job)


def test_workflow_triggers_when_installer_or_scan_changes():
    workflow = read_workflow("links.yml")
    assert workflow.count("- 'scripts/install-lychee.sh'") == 2
    assert workflow.count("- 'scripts/check-links.sh'") == 2
    assert "LYCHEE_VERSION: v0.24.2" in workflow
    assert "lycheeverse/lychee-action@" not in workflow
