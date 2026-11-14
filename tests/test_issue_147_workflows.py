"""Cache ownership, release recovery permissions and pinning policy."""

import re

from tests.workflow_helpers import (
    assert_action_reference_count,
    read_workflow,
    workflow_job_block,
    workflow_step_block,
)


def test_pr_cache_is_read_only_and_main_saves_only_on_miss():
    job = workflow_job_block(read_workflow("links.yml"), "link-checker")
    restore = workflow_step_block(job, "Restore lychee cache")
    save = workflow_step_block(job, "Save lychee cache on main")
    assert_action_reference_count(restore, "actions/cache/restore", 1)
    assert_action_reference_count(save, "actions/cache/save", 1)
    assert "github.event_name == 'push'" in save
    assert "github.ref == 'refs/heads/main'" in save
    assert "steps.lychee-cache.outputs.cache-hit != 'true'" in save
    assert "steps.lychee-cache.outputs.cache-primary-key" in save
    assert "actions/cache@" not in job
    docker = workflow_job_block(read_workflow("release.yml"), "docker-build")
    assert "cache-to:" not in docker


def test_digest_pins_cover_both_supported_architectures():
    job = workflow_job_block(read_workflow("links.yml"), "link-checker")
    for architecture in ("X86_64", "AARCH64"):
        assert re.search(rf"LYCHEE_SHA256_{architecture}: [0-9a-f]{{64}}$", job, re.M)


def test_release_dispatch_can_trigger_full_validation_and_skips_stale_publish():
    job = workflow_job_block(read_workflow("release.yml"), "manual-release")
    assert "actions: write" in job
    version = workflow_step_block(job, "Version and commit")
    assert "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in version
    check = workflow_step_block(job, "Check release artifacts")
    assert "version_committed == 'true'" in check
    assert "already_released == 'true'" in check
    # Deferred release sets neither success output, so no stale build/upload runs.
