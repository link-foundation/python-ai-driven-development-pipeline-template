# Issue 147: requirement inventory, research and verification plan

Read issue 147, native sub-issues 144/145/146 and all their comments on
2026-11-13. All comment lists were empty. PR 148 had no conversation comments,
inline review comments or reviews. No child has further sub-issues. No requested
fix was already resolved. Work remains in one PR on issue-147-aca811598ee8.

## Requirements, alternatives and chosen solutions

| Source | Every actionable requirement | Options and implementation plan | Verification |
| --- | --- | --- | --- |
| 144 | Remove the always-present pipx PATH warning without losing pinned ShellCheck or tracked-script coverage | pipx supports `--no-path-check`, but the suggested dedicated venv is independent of the runner's pipx version. Install shellcheck-py 0.11.0.1 there and invoke its absolute binary on NUL-delimited tracked shell paths | Workflow regression and actual ShellCheck CI log; no warning suppression |
| 145 8a | Resolve the unreachable release rebase/retry, including main advances pushed by GITHUB_TOKEN | Rebasing would change the validated source and conflict with prior release attestation requirements. Remove the dead path and misleading name/docstring; dispatch release.yml on main with the original bump/description. The fresh run performs lint/test/build before releasing. The old run publishes nothing. Apply to both pre-bump remote recovery and a non-fast-forward push race | Real tiny Git repositories in root/nested layouts; test concurrent source, equivalent metadata recovery, last allowed push attempt, dispatch success/failure, input preservation and no checkout mutation |
| 145 8a | Preserve existing release safety and retry behavior | Keep source/manifest/lock/mode attestation, original sole parent, unchanged transient retries/backoff, policy failures and default-off RELEASE_DEBUG diagnostics. Grant actions:write only to manual-release and pass GH_TOKEN only to its version step | Existing release-integrity and version tests plus workflow permission/gating tests |
| 145 8b | Verify lychee against independent committed per-architecture digests | An upstream checksum alone is replaceable. Commit reviewed x86_64/aarch64 pins next to LYCHEE_VERSION; require matching pins before download and compare archive and upstream checksum with the committed value | Local HTTP fixture serves a modified archive and matching checksum; installer must refuse it. Preserve download retry, corruption and version checks. Compare both pins with release API digests and published checksums |
| 145 item 4 | PR-only Docker builds must not export caches main cannot read | Drop cache-to, retaining restore. mode=min would still write inaccessible merge-ref caches | Existing Docker workflow regression now asserts no cache-to; publishing matrix caches retained |
| 145 item 4 | Link checks restore everywhere, save only on push to main without exact hit | Use existing actions/cache/restore and actions/cache/save, preserving UTC-day keys, freshness, reports and scan behavior | Workflow regression verifies event/ref/hit conditions and restored primary key |
| 145 item 5 | Apply 1000/900 hard/warning bands to .sh, .mjs and .js throughout the repository | Extend existing LIMITS; keep .py 1000/900 and Markdown 2500/2250 | Parameterized file discovery and warning/violation regressions; repository size gate |
| 146 item 1 | Add check_dist_size.py, configurable default just below 100 MB, annotate every oversized dist/* file by name, show largest members and write dist_size_bytes | Standard-library pathlib/stat, zipfile/tarfile and heapq avoid a dependency. Default 99,000,000 bytes; env DIST_SIZE_LIMIT_BYTES or CLI --max-bytes. Measure each compressed file; output largest individual size, not sum; list top ten uncompressed members without extraction. Fail closed on absent dist/files or invalid configuration | Tiny wheel/sdist fixtures check boundary equality, one byte over, multiple files, largest members, output on failure, missing files, invalid archives and environment configuration |
| 146 item 2 | Gate right after twine check in PR build and before upload | Apply to build, manual rebuilt distribution, automatic downloaded artifacts and both check/upload entry points in the local publisher | Workflow order/condition tests and a real subprocess proving local publish refuses oversized input before upload |
| 146 item 3 | Treat HTTP 400 File too large as permanent if upload retry is added | No upload retry is added; local publisher invokes twine once and publisher actions remain unwrapped. Keep the size gate before upload. A future retry classifier must treat this response as permanent | Review all upload call sites; no retry wrapper introduced |
| 147 | All three issues in this one PR; preserve each closing keyword separately | PR body includes Fixes #147, Fixes #144, Fixes #145 and Fixes #146, each on its own line. Keep the existing release mechanism prepared through a Scriv fragment | Final PR body and diff review, clean tree, main included, CI on current SHA, mark ready |

Issue 145's "Checked and not affected" section is context, not additional
requested fixes: link exit-code handling/scheduling and independent checks
already exist; there are no tracked compressed secrets; no infrastructure rerun
workflow, runner diversity or other inapplicable items need new machinery.

## Online research and existing components

- [PyPI storage limits](https://docs.pypi.org/project-management/storage-limits/)
  define per-file and total-project quotas separately. As of this investigation,
  personal defaults are 100 MB/file and organizations get 200 MB/file. Keep the
  issue's conservative 99 MB budget; projects can override it for their quota.
- [Twine check](https://twine.readthedocs.io/en/stable/#twine-check) checks the
  distribution description, not the upload-size budget.
- [pydistcheck](https://github.com/jameslamb/pydistcheck) already inspects wheel
  and sdist size and can enforce compressed-size policy. It is a viable broader
  package-quality tool, but would still need Actions output/annotation wrappers.
  The narrow standard-library gate satisfies this request without installation.
- [actions/cache](https://github.com/actions/cache) supplies independent restore
  and save actions; [cache restrictions](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)
  explain why PR merge-ref entries cannot be reused on main.
- [GitHub workflow triggering](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
  documents that workflow_dispatch creates a run even with GITHUB_TOKEN. A normal
  bot push is insufficient. The existing manual release workflow already runs
  the full checks and accepts the required original inputs.
- [pipx changelog](https://pipx.pypa.io/stable/changelog.html) documents the
  alternative --no-path-check. A venv keeps the requested pin and explicit binary.
- [Lychee v0.24.2 release](https://github.com/lycheeverse/lychee/releases/tag/lychee-v0.24.2):
  both committed archive digests agree with release API asset digests and the
  published .sha256 files retrieved during investigation. Future upgrades must
  update version and both pins together through review.
- Studied recent template PRs [143](https://github.com/link-foundation/python-ai-driven-development-pipeline-template/pull/143)
  and [139](https://github.com/link-foundation/python-ai-driven-development-pipeline-template/pull/139)
  to preserve installer retries, scan failures, release integrity and PR style.
  Related [link-cli PR 174](https://github.com/link-foundation/link-cli/pull/174)
  confirms the cache-eviction root cause and source warning bands; [hive-mind
  PR 4051](https://github.com/link-assistant/hive-mind/pull/4051) demonstrates the
  value of measuring archives before registry upload and permanent size failures.

## Execution checklist

- [x] Complete issue/comment/sub-issue/PR feedback inventory and code search.
- [x] Research primary sources, alternatives and recent related implementations.
- [x] Draft changes for every requirement and all upload/recovery call sites.
- [x] Add focused automated regressions with finite small fixtures.
- [ ] Complete local checks and record baseline reproductions.
- [ ] Commit and push atomic changes; review gh pr diff and update PR body.
- [ ] Check final-SHA CI; preserve and diagnose logs for each failing run.
- [ ] Ensure clean tree/main included, mark PR ready and record final evidence.
