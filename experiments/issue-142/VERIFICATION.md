# Verification for PR 143

- Read parent #142, native sub-issues #140/#141, all issue comments and all three
  PR feedback endpoints; no additional requirements were present.
- Historical run 34994688031 log lines 222–223 show the lychee archive URL and
  immediate curl exit 22, before any scan. Log preserved during investigation
  in `/tmp/issue142-original-links.log`.
- `PYTHONPATH=. python experiments/issue-142/reproduce_concurrency.py` rejects
  the original d359342 release workflow on both main and PR refs.
- Focused pytest selection: **124 passed** in 27.34 seconds. Includes both new
  regression modules and existing release, workflow, pipeline-status and Pages
  policy tests. Log: `/tmp/issue142-focused.log`.
- Installer regression uses a tiny local HTTP release server: one-shot upstream
  curl fails 22; production installer retries both archive and checksum URLs,
  verifies and installs. Wrong checksums, exhausted retries and unpinned versions
  fail without exposing an installed binary or PATH update.
- Production workflow scan command tested with success, broken links, empty
  scans, missing/stale/malformed reports, argument errors and process crashes.
  Existing summaries are preserved; outputs carry the original scanner code.
- Real v0.24.2 download, SHA-256 verification and version invocation succeeded.
  A real offline one-link scan confirmed the Markdown `🔍 Total` layout.
- Ruff check and format for new files, bash syntax, `git diff --check` and
  repository file-size check passed.
- Full test suite, workflow schema, ShellCheck, security audits, CodeQL and link
  scan run through the existing PR CI. Current main was already an ancestor of
  the branch when fetched; no merge changes were necessary.

The Docker writer matrix retains native amd64/arm64 runners. Its uploads now
serialize with other writers as #140 requests. Checks and builds that do not
publish still have distinct concurrency groups and remain parallel.
