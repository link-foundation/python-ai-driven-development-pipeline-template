"""Bounded reproductions against the immutable pre-fix scripts.

Run with the development environment: python experiments/issue-147/reproduce_original.py
Uses tiny local Git repositories and a loopback HTTP fixture; never publishes.
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
BASE = "f28c9d836cd18426adbc2f17629ac58202e04a83"


def original(path):
    return subprocess.check_output(
        ["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True
    )


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def reproduce(work):
    old_size = work / "old_size.py"
    old_size.write_text(original("scripts/check_file_size.py"))
    size = load("original_size", old_size)
    source = work / "sources"
    source.mkdir()
    for suffix in (".sh", ".mjs", ".js"):
        (source / f"helper{suffix}").write_text("x\n" * 1001)
    github = source / ".github/actions"
    github.mkdir(parents=True)
    (github / "helper.py").write_text("x\n" * 1001)
    assert not size.check_directory(source).violations
    print("BASELINE: 1001-line shell/JS/MJS and .github helpers escape the size gate")

    from tests.test_lychee_install_and_scan import release_server

    fixture = release_server.__wrapped__()
    url, state = next(fixture)
    state["replace_asset"] = True
    installer = work / "original-installer.sh"
    installer.write_text(original("scripts/install-lychee.sh"))
    try:
        result = subprocess.run(
            ["bash", str(installer), str(work / "bin")],
            env={
                **os.environ,
                "LYCHEE_VERSION": "v0.24.2",
                "LYCHEE_DOWNLOAD_BASE_URL": url,
                "LYCHEE_DOWNLOAD_RETRIES": "1",
                "LYCHEE_DOWNLOAD_RETRY_DELAY": "1",
            },
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0, result.stderr
        print(
            "BASELINE: modified lychee archive + matching replacement checksum accepted"
        )
    finally:
        fixture.close()

    old_release = work / "old_release.py"
    old_release.write_text(original("scripts/version_and_commit.py"))
    release = load("original_release", old_release)
    repo = work / "repo"
    repo.mkdir()
    os.chdir(repo)

    def git(*args):
        return subprocess.check_output(
            ["git", *args], stderr=subprocess.DEVNULL, text=True
        ).strip()

    def commit(message):
        git("add", "-A")
        git("commit", "-m", message)
        return git("rev-parse", "HEAD")

    git("init", "--initial-branch=main")
    git("config", "user.name", "Test")
    git("config", "user.email", "test@example.com")
    Path("pyproject.toml").write_text('[project]\nname="example"\nversion="1.0.0"\n')
    Path("source.py").write_text("validated = True\n")
    validated = commit("A: validated")
    remote = work / "remote.git"
    git("init", "--bare", "--initial-branch=main", str(remote))
    git("remote", "add", "origin", str(remote))
    git("push", "origin", "main")
    Path("source.py").write_text("new_source = True\n")
    commit("B: concurrent source")
    git("push", "origin", "main")
    git("reset", "--hard", validated)
    Path("pyproject.toml").write_text('[project]\nname="example"\nversion="1.0.1"\n')
    commit("R: release metadata")
    try:
        release.push_branch_with_rebase_retry("main", validated_sha=validated)
    except ValueError as error:
        assert "drift" in str(error)
        print(
            f"BASELINE: real non-fast-forward fails before rebase/redispatch: {error}"
        )
    else:
        raise AssertionError("Expected the original race failure")
    workflow = original(".github/workflows/release.yml")
    assert "check_dist_size" not in workflow
    print("BASELINE: build and publication have no distribution size gate")


if __name__ == "__main__":
    previous = Path.cwd()
    try:
        with tempfile.TemporaryDirectory(prefix="issue147-repro-") as directory:
            reproduce(Path(directory))
    finally:
        os.chdir(previous)
