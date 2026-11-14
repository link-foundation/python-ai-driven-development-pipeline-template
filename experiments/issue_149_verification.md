# Issue #149 verification

## Reproduction

PR #135's CI run 43399754022 (2026-11-13) failed three assertions, while
755 tests passed and one was skipped. The saved log identifies cache restore
v5 assertions at lines 1696–1709 and zizmor-action v0.6.4 at lines 1716–1719;
the summary is at lines 1731–1734.

Before changing the policy tests, the new
`tests/test_dependabot_updates.py::test_policy_accepts_dependabot_version_updates`
failed on `tests/test_issue_118_workflows.py:51` after changing cache v5 to v6
in temporary workflow files. The actual workflow files were untouched.
The same regression now passes, along with a synthetic update of every
tagged action and the actionlint image. The test calls the existing behavioral
tests, preserving cache ownership, action identity/pinning, Pages inputs,
Docker settings, security scans and shared zizmor settings.

## Requirement coverage

| Requirement | Implementation and automated evidence |
| --- | --- |
| Dependabot updates pass without unrelated test edits | `assert_action_reference_count`, updated workflow policies, simulated #135 and all-action bumps; invalid/floating pins still rejected |
| zizmor action/CLI coupling | `check_zizmor_compatibility.py` reads both workflow values and selected upstream data; digest and lockfile formats, compatible bumps, unsupported versions, incomplete trees and API errors covered |
| Report bot PRs that stay open | Daily/manual read-only health workflow; exact 14-day boundary, just over it, repeated banners, both reasons, closed/non-bot exclusion and configurable thresholds covered |
| Inspect all PRs and report visible failures | `gh api --paginate --slurp`, 101-PR/two-page test, malformed/error responses, CLI exit codes, linked annotations, append-only summary and default-off diagnostics covered |
| Existing behavior and release preparation | Existing workflow/concurrency policy suites pass; Scriv fragment added as the repository's automatic release trigger |

## Local results

- 166 focused tests passed, covering changed policies, release checks and every
  workflow's concurrency behavior. A follow-up 72-test run passed after improving
  API diagnostics and adding negative-threshold cases. The final six mutation
  and pinning regressions also pass.
- Repository Ruff lint/format, file-size policy and whitespace checks pass.
- `python experiments/check_issue_149_upstream.py` checked the real upstream
  data: both current v0.6.4 (digest table) and #135's v0.8.1 (lockfiles) support
  the existing CLI 1.30.1. No upstream code is executed by this check.
- A real authenticated health scan found one open Dependabot PR and none over
  the default thresholds. #135 is under 14 days at the time of this check;
  its failing tests are reproduced independently of the age policy.

Local outputs are saved under ignored `ci-logs/`. Full Python suites, builds,
workflow audits, security and online link checks run in existing PR CI.
Final commit/run URLs and readiness are recorded in PR #150 after CI completes.
