#!/usr/bin/env python3
"""Verify the workflow's CLI pin against the selected zizmor action's files."""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote


def read_pins(workflow: str) -> tuple[str, str]:
    """Read the one action ref and exact shared CLI version from a workflow."""
    refs = re.findall(r"uses: zizmorcore/zizmor-action@([^\s]+)", workflow)
    versions = re.findall(
        r"^  ZIZMOR_VERSION: ['\"]?(\d+\.\d+\.\d+)['\"]?$", workflow, re.M
    )
    if len(refs) != 1 or len(versions) != 1:
        msg = "Expected one zizmor action reference and one exact ZIZMOR_VERSION"
        raise ValueError(msg)
    return refs[0], versions[0]


def gh_json(endpoint: str) -> dict:
    """Read upstream metadata without executing any upstream code."""
    result = subprocess.run(
        ["gh", "api", endpoint], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def check_compatibility(workflow: str) -> tuple[str, str]:
    """Support legacy container digests and newer per-version Python locks."""
    ref, version = read_pins(workflow)
    repository = "repos/zizmorcore/zizmor-action"
    tree = gh_json(f"{repository}/git/trees/{quote(ref, safe='')}?recursive=1")
    if tree.get("truncated") is not False:
        msg = "The zizmor action file tree is incomplete"
        raise ValueError(msg)
    paths = {entry["path"] for entry in tree["tree"] if entry["type"] == "blob"}
    supported = f"support/locks/zizmor-{version}.txt" in paths
    if "support/versions" in paths:
        data = gh_json(
            f"{repository}/contents/support/versions?ref={quote(ref, safe='')}"
        )
        table = base64.b64decode(data["content"]).decode()
        supported = supported or any(
            re.fullmatch(rf"{re.escape(version)} sha256:[0-9a-f]{{64}}", line)
            for line in table.splitlines()
        )
    if not supported:
        msg = (
            f"zizmor-action@{ref} does not support ZIZMOR_VERSION={version}. "
            "Choose a CLI version present in that action ref's support/versions "
            "or support/locks table and update ZIZMOR_VERSION."
        )
        raise ValueError(msg)
    return ref, version


def main(argv: list[str] | None = None) -> int:
    """Fail visibly if upstream lookup or version compatibility fails."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workflow", type=Path, default=Path(".github/workflows/workflows.yml")
    )
    args = parser.parse_args(argv)
    try:
        ref, version = check_compatibility(args.workflow.read_text())
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"Zizmor compatibility check failed: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr.strip(), file=sys.stderr)
        return 1
    print(f"zizmor-action@{ref} supports ZIZMOR_VERSION={version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
