# Issue #149 execution plan

Objective: implement both requested fixes in PR #150, with regression evidence
and passing CI on the final commit. No required sub-issues or later feedback
were present in the initial issue/PR audit.

## Requirements and verification

- [x] Remove exact action-version assertions throughout workflow policy tests;
  retain action identity, reference pinning, permissions, inputs and behavior.
  Verify current workflows and simulated Dependabot updates, including #135.
- [x] Check the zizmor action/CLI compatibility using the selected action's own
  support table, with a clear diagnostic for unsupported combinations.
  Verify compatible updates, mismatches and upstream lookup errors.
- [x] Add a scheduled/manual, read-only Dependabot health check: inspect all
  open PR pages, fail for age over 14 days or more than two rebase banners,
  report PR links/reasons and fail visibly on API errors.
  Verify thresholds, non-bot/closed PR exclusion, pagination and CLI exits.
- [x] Document operation and add a Scriv fragment (the existing release trigger).
- [x] Run focused automated checks locally; leave full suites/builds to CI.
- [ ] Review complete PR diff; merge current main; commit/push only the prepared
  branch; update PR title/body and mark ready after final-SHA checks pass.

## Investigation

Issue #149 and all comments, PR #150 conversation/inline comments/reviews, and
recent related PRs #148/#143/#134 were read. Main is already included.
PR #135's saved CI log has three failures at lines 1696–1719 and its final
summary at 1731–1734: two cache-v5 assertions and a zizmor-action-v0.6.4
assertion. 755 other tests passed. Its actual update is cache v5→v6,
zizmor-action v0.6.4→v0.8.1, and a Codecov hash bump.

Additional exact action tags occur in tests for checkout, setup-python,
setup-node, CodeQL, Pages and dependency review. These are also owned by the
weekly github-actions Dependabot configuration and need behavioral assertions.

The reference hive-mind health helper/workflow uses a 14-day threshold and
more than two repeated rebase banners. This Python repository can implement
the same policy with its existing standard-library/`gh` pattern and no new
runtime package or npm install. Local log files are ignored by Git. Detailed
local verification is recorded in `issue_149_verification.md`; final-commit CI
and readiness are recorded in the PR description after verification.

## CI investigation protocol

List the latest five branch runs with creation time and head SHA. Compare each
run with the latest commit before using its result. Download every failed run
to `ci-logs/<workflow>-<run-id>.log`, read the relevant chunks (at most 1500
lines per read), and record exact errors/line numbers. Refresh all feedback and
verify no requirement-related uncommitted files before final readiness.
