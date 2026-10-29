# CI evidence and security gates

All artifact transfers use the local JavaScript action in
`.github/actions/artifact`. It bundles exact versions of GitHub's artifact SDK,
Core and Glob with a committed lockfile and third-party license notices. Runtime
credentials stay inside the runner's JavaScript action context.

Transfers retry transient DNS/socket failures and HTTP 429/5xx responses up to
three times, with 5 and 10 second delays. Permanent refusals, quota errors and
missing evidence fail. Give every producer a unique artifact name: the action
refuses preexisting artifacts. If an upload's final response is lost, it deletes
only its own name before retrying; it never accepts old evidence as success.
Pages uploads use the standard `artifact.tar` layout and one-day retention.

Downloads retain SDK SHA256 verification and fail on mismatches or missing
digests. Until the upstream Buffer deprecation is fixed, `skipDecompress` avoids
unzip-stream. Python's standard `zipfile` module validates every member before
writing: traversal, symlinks, special files and conflicting destinations fail.
The action supports named downloads, star name patterns and `merge-multiple`.
Python 3 and GNU tar are supplied by the pinned Ubuntu runners.

After editing the action, regenerate and commit its bundle:

```sh
npm ci --prefix .github/actions/artifact --ignore-scripts
npm test --prefix .github/actions/artifact
npm run build --prefix .github/actions/artifact
git add -f .github/actions/artifact/dist
```

The Workflows pipeline tests injected transport errors and a real artifact
round trip, compares every downloaded byte, verifies the Pages tar, and runs
downloads with `NODE_OPTIONS=--throw-deprecation`. It also checks the bundle is
reproducible from the committed source and lockfile.

CodeQL uses full analysis for both Python and Actions. The job-level
`CODEQL_ACTION_DIFF_INFORMED_QUERIES='false'` setting avoids the compare API's
300-file truncation without changing query selection. The official analyzer
still uploads to Code Scanning, then `scripts/check_codeql_results.py` checks
every local SARIF report/run and fails on every finding regardless of severity,
invalid reports, or failed invocations. Reports are uploaded even when the gate
fails. The aggregate Security status therefore observes these failures directly.

The link checker accepts actual live-link recovery, but archive snapshots are
repair suggestions. A failed checker cannot pass without usable report evidence.
The archive helper fails closed when its report is missing or unusable.
