"""Prove the issue-140 regression test rejects the original workflow snapshot."""

import subprocess
import tempfile
from pathlib import Path

from tests.test_issue_140_concurrency import test_all_job_policies

original = subprocess.run(
    ["git", "show", "d359342:.github/workflows/release.yml"],
    check=True,
    capture_output=True,
    text=True,
).stdout
with tempfile.TemporaryDirectory() as directory:
    workflow = Path(directory) / "release.yml"
    workflow.write_text(original)
    for ref in ("refs/heads/main", "refs/pull/143/head"):
        try:
            test_all_job_policies(workflow, ref)
        except AssertionError as error:
            print(f"Original policy rejected on {ref}: {error}")
        else:
            raise AssertionError("Regression test unexpectedly accepted old workflow")
