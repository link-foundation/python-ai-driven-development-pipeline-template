"""Regression tests for GitHub Actions workflow policy."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def read_workflow(name: str) -> str:
    """Read a workflow file by name."""
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def workflow_job_block(workflow: str, job_name: str) -> str:
    """Return the YAML text block for one top-level workflow job."""
    lines = workflow.splitlines()
    start = next(index for index, line in enumerate(lines) if line == f"  {job_name}:")
    end = next(
        (
            index
            for index, line in enumerate(lines[start + 1 :], start + 1)
            if re.match(r"^  [A-Za-z0-9_-]+:$", line)
        ),
        len(lines),
    )
    return "\n".join(lines[start:end])


def assert_action_pin_count(
    workflow: str, action: str, version: str, count: int
) -> None:
    """Assert every expected action reference is pinned to the requested version."""
    pattern = rf"uses:\s+{re.escape(action)}@{re.escape(version)}\b"
    assert len(re.findall(pattern, workflow)) == count


def assert_action_pin_absent(workflow: str, action: str, version: str) -> None:
    """Assert an outdated action reference is not used."""
    pattern = rf"uses:\s+{re.escape(action)}@{re.escape(version)}\b"
    assert not re.search(pattern, workflow)


def test_release_workflow_keeps_main_releases_running() -> None:
    """Main release runs must not be cancelled by follow-up pushes."""
    workflow = read_workflow("release.yml")

    assert "cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}" in workflow
    assert "cancel-in-progress: true" not in workflow


def test_release_workflow_jobs_have_explicit_timeouts() -> None:
    """Release workflow jobs should fail fast instead of using the six-hour default."""
    workflow = read_workflow("release.yml")

    expected_timeouts = {
        "detect-changes": 5,
        "lint": 20,
        "test": 30,
        "build": 20,
        "changelog": 10,
        "auto-release": 30,
        "manual-release": 30,
    }

    for job_name, timeout in expected_timeouts.items():
        block = workflow_job_block(workflow, job_name)
        assert f"timeout-minutes: {timeout}" in block


def test_release_workflow_action_versions_are_current() -> None:
    """Release workflow actions should use the current major versions."""
    release_workflow = read_workflow("release.yml")

    assert_action_pin_count(release_workflow, "actions/checkout", "v6", 7)
    assert_action_pin_count(release_workflow, "actions/upload-artifact", "v7", 1)
    assert_action_pin_count(release_workflow, "actions/download-artifact", "v7", 1)


def test_release_workflow_auto_detects_python_layout() -> None:
    """Release workflow should support root and python/ package layouts."""
    workflow = read_workflow("release.yml")

    assert "if [ -f pyproject.toml ]; then" in workflow
    assert "elif [ -f python/pyproject.toml ]; then" in workflow
    assert "root=python" in workflow
    assert "multi_language=true" in workflow


def test_release_workflow_namespaces_multi_language_python_tags() -> None:
    """Multi-language releases should use py_v tags and plain root releases keep v."""
    workflow = read_workflow("release.yml")
    auto_release = workflow_job_block(workflow, "auto-release")

    assert 'TAG="py_v$CURRENT_VERSION"' in auto_release
    assert 'TAG="v$CURRENT_VERSION"' in auto_release
    assert 'git rev-parse "$TAG"' in auto_release


def test_release_workflow_runs_python_steps_from_detected_root() -> None:
    """Package build and release commands should run against the detected root."""
    workflow = read_workflow("release.yml")

    assert 'cd "${{ steps.python_layout.outputs.root }}"' in workflow
    assert "path: ${{ steps.python_layout.outputs.dist_dir }}" in workflow
    assert "packages-dir: ${{ steps.python_layout.outputs.dist_dir }}" in workflow
    assert (
        'python "${{ steps.python_layout.outputs.root }}/scripts/create_github_release.py"'
        in workflow
    )


STATUS_CHECK_FUNCTIONS = ("always()", "!cancelled()", "!failure()", "success()")


def job_condition(workflow: str, job_name: str) -> str:
    """Return the ``if:`` condition text for a workflow job."""
    block = workflow_job_block(workflow, job_name)
    match = re.search(r"^    if:(.*?)(?=^    [a-z])", block, re.DOTALL | re.MULTILINE)
    assert match, f"job {job_name!r} has no if condition"
    return match.group(1)


def test_dispatch_dependent_jobs_use_status_check_function() -> None:
    """Jobs that depend on skippable jobs must override the default status gate.

    ``detect-changes`` is skipped for ``workflow_dispatch``. GitHub Actions skips
    a job whose dependency was skipped unless the dependent ``if`` condition
    includes a status-check function (``always()``, ``!cancelled()``, ...).
    Without it, a manual release silently skips lint/test and then the release
    itself even though it appears successful.
    """
    workflow = read_workflow("release.yml")

    for job_name in ("lint", "test", "manual-release"):
        condition = job_condition(workflow, job_name)
        assert any(fn in condition for fn in STATUS_CHECK_FUNCTIONS), (
            f"job {job_name!r} depends on a skippable job but its if condition "
            f"does not start with a status-check function: {condition!r}"
        )


def test_manual_release_requires_required_checks_to_succeed() -> None:
    """Manual release must only run after lint, test, and build succeed."""
    workflow = read_workflow("release.yml")
    condition = job_condition(workflow, "manual-release")

    assert "needs.lint.result == 'success'" in condition
    assert "needs.test.result == 'success'" in condition
    assert "needs.build.result == 'success'" in condition
    assert "github.event_name == 'workflow_dispatch'" in condition


def test_release_jobs_smoke_test_published_package_before_github_release() -> None:
    """Published packages must be installed and exercised before announcing release."""
    workflow = read_workflow("release.yml")

    expected_version_outputs = {
        "auto-release": "steps.version_check.outputs.current_version",
        "manual-release": "steps.version.outputs.new_version",
    }

    for job_name, version_output in expected_version_outputs.items():
        block = workflow_job_block(workflow, job_name)
        assert "- name: Smoke test published package" in block
        assert "python scripts/smoke_test_published_package.py" in block
        assert f'--version "${{{{ {version_output} }}}}"' in block

        publish_index = block.index("- name: Publish to PyPI")
        smoke_index = block.index("- name: Smoke test published package")
        release_index = block.index("- name: Create GitHub Release")
        assert publish_index < smoke_index < release_index


def test_docs_workflow_action_versions_are_current() -> None:
    """Docs workflow actions should stay aligned with the current Pages stack."""
    docs_workflow = read_workflow("docs.yml")

    assert_action_pin_count(docs_workflow, "actions/checkout", "v6", 1)
    assert_action_pin_count(docs_workflow, "actions/upload-artifact", "v7", 1)
    assert_action_pin_count(docs_workflow, "actions/configure-pages", "v6", 1)
    assert_action_pin_count(docs_workflow, "actions/upload-pages-artifact", "v5", 1)
    assert_action_pin_count(docs_workflow, "actions/deploy-pages", "v5", 1)

    assert_action_pin_absent(docs_workflow, "actions/checkout", "v4")
    assert_action_pin_absent(docs_workflow, "actions/upload-artifact", "v4")
    assert_action_pin_absent(docs_workflow, "actions/configure-pages", "v5")
    assert_action_pin_absent(docs_workflow, "actions/upload-pages-artifact", "v3")
    assert_action_pin_absent(docs_workflow, "actions/deploy-pages", "v4")
