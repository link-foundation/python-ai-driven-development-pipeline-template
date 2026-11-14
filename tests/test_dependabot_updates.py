"""Workflow behavior must survive action updates owned by Dependabot."""

import re

import pytest

from tests import (
    test_issue_98,
    test_issue_118_workflows,
    test_issue_133_workflows,
    test_issue_147_workflows,
    test_release_workflow,
    test_workflows,
)
from tests import workflow_helpers as helpers


@pytest.mark.parametrize("all_actions", [False, True])
def test_policy_accepts_dependabot_version_updates(tmp_path, monkeypatch, all_actions):
    """Reproduce #135's bumps without modifying the working workflows."""
    for path in helpers.WORKFLOWS.glob("*.yml"):
        workflow = path.read_text().replace(
            "actions/cache/restore@v5", "actions/cache/restore@v6"
        )
        workflow = workflow.replace("actions/cache/save@v5", "actions/cache/save@v6")
        workflow = re.sub(
            r"zizmorcore/zizmor-action@v[\d.]+",
            "zizmorcore/zizmor-action@v0.8.1",
            workflow,
        )
        if all_actions:
            workflow = re.sub(r"(uses: [\w/-]+)@v[\d.]+", r"\1@v99.0.0", workflow)
            workflow = re.sub(
                r"(docker://rhysd/actionlint@sha256:)[0-9a-f]+ # v[\d.]+",
                rf"\g<1>{'a' * 64} # v99.0.0",
                workflow,
            )
        (tmp_path / path.name).write_text(workflow)
    monkeypatch.setattr(helpers, "WORKFLOWS", tmp_path)
    test_issue_118_workflows.test_link_scan_uses_directory_extensions_and_persists_cache()
    test_issue_147_workflows.test_pr_cache_is_read_only_and_main_saves_only_on_miss()
    test_issue_98.test_zizmor_has_one_supported_version_and_checks_low_confidence()
    test_workflows.test_security_workflow_scans_code_actions_and_dependencies()
    test_workflows.test_links_workflow_fails_for_every_broken_live_link()
    test_workflows.test_workflow_lint_job_validates_every_workflow()
    test_workflows.test_docs_workflow_uses_expected_pages_actions()
    test_workflows.test_docs_workflow_deploys_pages_only_when_opted_in()
    test_issue_133_workflows.test_security_workflow_audits_npm_lockfiles_and_gates_on_it()
    test_release_workflow.test_release_workflow_uses_expected_pinned_actions()
    test_release_workflow.test_release_workflow_sets_git_default_branch_before_checkout()
    test_release_workflow.test_release_workflow_builds_docker_images_on_pull_requests()
    for path in tmp_path.glob("*.yml"):
        test_issue_118_workflows.test_first_party_checkout_and_python_actions_are_versioned(
            path
        )


@pytest.mark.parametrize("ref", ["main", "latest", "v1oops", "a" * 39])
def test_behavioral_assertions_still_reject_floating_or_invalid_pins(ref):
    with pytest.raises(
        AssertionError, match="must use a version tag or full commit hash"
    ):
        helpers.assert_action_reference_count(
            f"uses: actions/cache/restore@{ref}", "actions/cache/restore", 1
        )
