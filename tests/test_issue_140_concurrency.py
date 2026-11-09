"""Evaluate real concurrency policies and status gates on main and PR refs."""

from __future__ import annotations

import json
import os
import re
import subprocess

import pytest

from tests.test_check_pipeline_status import read_values
from tests.workflow_helpers import (
    ROOT,
    WORKFLOWS,
    read_workflow,
    workflow_job_block,
    workflow_job_names,
)

WRITERS = {
    "release.yml": {
        "auto-release",
        "manual-release",
        "docker-publish-config",
        "docker-publish-build",
        "docker-publish",
    },
    "docs.yml": {"deploy"},
}


@pytest.mark.parametrize("ref", ["refs/heads/main", "refs/pull/143/head"])
@pytest.mark.parametrize("path", sorted(WORKFLOWS.glob("*.yml")))
def test_all_job_policies(path, ref):
    """Check concrete effective policies, identity isolation and writer gates."""
    workflow = path.read_text()
    assert "\nconcurrency:\n" not in workflow.split("\njobs:\n")[0]
    jobs = workflow_job_names(workflow)
    policies = read_values(path, *jobs)
    writers = WRITERS.get(path.name, set())
    groups = set()
    for job in jobs:
        block = workflow_job_block(workflow, job)
        if job == "pipeline-status":
            continue
        if job in writers:
            assert policies[job] == "false", (path.name, ref, job)
            assert "group: main-writer-${{ github.repository }}-main" in block
            assert "queue: max" in block
        else:
            assert policies[job] == "true", (path.name, ref, job)
            group = re.search(r"^      group: (.+)$", block, re.MULTILINE)[1]
            evaluated = group.replace("${{ github.ref }}", ref).replace(
                "${{ github.workflow }}", path.stem
            )
            assert evaluated not in groups
            groups.add(evaluated)
            assert job in group or (
                job == "artifact-roundtrip" and "artifacts" in group
            )
            if "matrix:" in block:
                matrix = block.split("      matrix:\n", 1)[1].split("    steps:", 1)[0]
                axes = re.findall(r"^        ([a-z-]+):", matrix, re.MULTILINE)
                assert all(f"matrix.{axis}" in group for axis in axes)

        result = subprocess.run(
            ["bash", str(ROOT / "scripts/check-pipeline-status.sh")],
            env={
                **os.environ,
                "WORKFLOW_FILE": str(path),
                "HEAD_REF": ref,
                "RUN_SHA": "a" * 40,
                "BRANCH_HEAD_SHA": "b" * 40,
                "NEEDS_JSON": json.dumps({job: {"result": "cancelled"}}),
            },
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        assert result.returncode == (1 if job in writers else 0), result.stdout


def test_pages_build_has_no_configuration_writes():
    """Only the serialized deploy job may configure the Pages site."""
    workflow = read_workflow("docs.yml")
    build = workflow_job_block(workflow, "build")
    deploy = workflow_job_block(workflow, "deploy")
    assert "pages: write" not in build
    assert "configure-pages" not in build
    assert "configure-pages" in deploy
    assert "needs: [build]" in deploy
