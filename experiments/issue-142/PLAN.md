# Issue 142 requirements, research and verification

Scope: parent #142 and native sub-issues #140 and #141; all issue comments,
PR conversation, inline comments and reviews were empty at initial inspection.
All changes belong in PR #143, with separate `Fixes` references for all three.

## Requirement inventory and chosen solutions

| Requirement | Implementation plan | Verification |
| --- | --- | --- |
| #140 cancel superseded checks on PRs and main | Literal true per check job, distinct workflow/ref/job groups | Evaluate production policies for both refs |
| Include matrix axes in check groups | Preserve CodeQL language axis; test all check matrices | Workflow-wide policy test |
| Preserve and serialize active writers repository-wide | Same repository/main group, false cancellation and existing queue:max for release, Docker and Pages | Compare every writer policy and gate behavior |
| No workflow cancellation around writers | Remove docs workflow concurrency, move configure-pages from build to deploy | Workflow policy and Pages tests |
| Superseded status gates stay accurate | Retain existing fail-closed classifier; exercise actual workflows on main and PR refs | Superseded checks warn; timed-out writers and current checks fail |
| #141 tolerate transient installer failures | Pinned v0.24.2 shell installer, curl retry for archive and checksum, SHA-256 verification, GITHUB_PATH | Local HTTP server returns 503 once per asset |
| Reject unpinned versions | Require explicit vMAJOR.MINOR.PATCH | Installer negative test |
| Preserve lychee arguments and downstream recovery | Direct shell invocation with existing scan flags, Markdown output and exit_code | Execute actual workflow run block against stub binary |
| Preserve job summary | Append report to GITHUB_STEP_SUMMARY | Stub report assertion |
| Fail on missing report, including exit 2 argument errors | Delete stale report, require fresh nonempty report and valid total | Missing/stale report tests |
| Fail on zero checked links | Parse Markdown total; reject zero | Empty-scan regression test |
| Keep broken-link recovery but distinguish infrastructure errors | Defer only real exit 2 reports to recheck/archive; require successful scan step for broken-link annotation | Success, broken links, CLI error and crash tests |
| Automated checks in PR | Existing pytest and workflow/ShellCheck CI jobs | Focused local tests then CI on final SHA |
| Prepare release | Add Scriv changelog fragment (automatic release trigger) | Changeset validation in CI |
| Finalize single PR | Merge current main, review diff, update title/body, wait for CI, ready PR, clean tree | Final checklist |

## Research and alternatives

- GitHub documents job-level concurrency, repository-scoped group names and
  queue:max: https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency
- Repository CI principles explicitly call for cancellable checks on main and
  shared writer groups: https://github.com/link-assistant/hive-mind/blob/main/docs/CI-CD-BEST-PRACTICES.md#10-concurrency-control
- Confirmed upstream #348 is open and v2.9.0 downloads with one curl call:
  https://github.com/lycheeverse/lychee-action/issues/348
- curl supports retry-all-errors, retry count/delay and transfer limits:
  https://curl.se/docs/manpage.html#--retry-all-errors
- The existing installer in hive-mind PR #4026 is an applicable reusable component:
  https://github.com/link-assistant/hive-mind/blob/issue-4025-c651727aa29c/scripts/install-lychee.sh
- Verified the pinned lychee release publishes Linux archives and .sha256 assets:
  https://github.com/lycheeverse/lychee/releases/tag/lychee-v0.24.2

Alternatives: wait for the upstream action patch, wrap the whole action in a retry
component, or use a prebuilt container. The explicit installer retries only setup,
verifies the asset, preserves existing scanning behavior and needs no new runtime.
A workflow-level cancel policy cannot protect active writers. A shared job-level
writer group also serializes the two digest uploads; native architecture runners
are retained, but writer serialization takes precedence over parallel publishing.
The read-only Docker release config is protected as part of an already-started
release so supersession cannot strand its downstream publication.
