# Issue 151: findings, requirements and implementation decisions

Research date: 2026-11-14 UTC. Source issue, its complete comment, native
sub-issue response (empty), PR conversation, inline comments and reviews are
archived alongside this document. No screenshots or UI changes are involved.
Related work reviewed: merged Dependabot PR 135 and dependency/CI PR 150;
upstream toolkit PR 2483 is still open.

## Requirement-to-solution and verification map

| Requirement from issue or execution instructions | Alternatives considered and selected solution | Verification / evidence |
| --- | --- | --- |
| Investigate all default-branch runs following merged PR 135 | Reverting the update is prohibited. Compare SHAs/timestamps and retain every failing log instead. | `main-runs-initial.json`, `main-pipeline-43575817822.log`; only CI/CD Pipeline failed, at release credential preflight. |
| Update Python first, across both manifests | pip-tools or Poetry would add another dependency format; select uv's native universal lock for pyproject and its extras. | `uv.lock`, mirrored docs extra, locked installation and audit tests. |
| Update Python build, runtime, dev, test, lint, docs and audit tools | Raise every direct floor to the queried stable release; remove obsolete upper ceilings and the legacy Scriv TOML extra. | `DEPENDENCIES-PYTHON.md`, PyPI metadata, metadata regression tests. |
| Update npm direct and development dependencies across majors | Query `/latest` for every direct package rather than relying on `npm update` alone. Keep exact direct pins and update all allowed transitives. | `DEPENDENCIES-NPM.md`, package.json/lock, Node tests, rebuilt bundle. |
| Update every transitive entry, or explain each exception | Unsupported blanket major overrides can break library APIs. Resolve actual declaring parents and record every retained constraint individually. | All old/new npm lock entries and every Python registry entry have before/current/latest/decision rows. Scriv's exact pins have a reproducing resolver failure and upstream report. |
| Update every Actions reference, including local/composite manifests | Pin current complete release tags or verified immutable hashes; keep local actions commit-bound with `$/`. | `DEPENDENCIES-AUTOMATION.md`, source snapshots, workflow tests/actionlint/zizmor. |
| Update pre-commit hooks and shell-installed tools | Current upstream hook tags; align Ruff/mypy and scanner versions with Python/npm manifests. | Registry inventory and full `pre-commit run --all-files`. |
| Update language/toolchain versions and base images | Python 3.15.2, Node 26.13.1, npm 12.2.2 and GA Ubuntu 26.04. Keep node24 only where it names the supported Actions execution ABI. | Runtime pin tests, official release feeds, runner metadata; there is no repository Dockerfile/base-image pin. |
| Keep duplicate pins consistent throughout the codebase | Central Python install helper plus committed uv lock; npm lock now includes Secretlint instead of independently resolving it with npx. | Repository-wide searches, manifest/lock alignment tests, CI jobs use the same helper. Historical logs and old-version test fixtures remain historical. |
| Read major changelogs and migration guides | Review actual breaking changes and exercise updated APIs instead of suppressing warnings. | Migration notes and source references below; full warning-strict builds/tests. |
| Replace bespoke logic with new upstream functionality | Native Node filesystem glob replaces recursive JS traversal; Python Path.walk prunes ignored directories; pytest strict mode and asyncio fixture-scope replace older configuration. | Existing filesystem semantics/ZIP regressions, ignored-tree test, full suite. |
| Remove obsolete compatibility shims | Remove the optional tomllib import, Python 3.9 typing/runtime target and Scriv's unused TOML extra. Adopt SPDX metadata accepted by current Hatchling/Twine. | Package build and metadata checks, smoke-test regressions. |
| Preserve previous behavior/features while updating | Keep bounded artifact transport retries, official SDK transfer/digest checks, strict ZIP extraction, Pages protocol and release safeguards until upstream supplies equivalents. | Existing behavioral tests remain active; only version-dependent assertions and effective lint configuration are updated. |
| Regenerate and commit every lock | Add uv.lock and regenerate package-lock.json with current toolchains; build without untracked build isolation. | `uv sync --locked --all-extras`, fresh `npm ci`, `python -m build --no-isolation`, committed bundle check. |
| Dependabot every ecosystem and directory | Current official support includes dedicated `uv` and `pre-commit` managers. Use uv at `/`, pip at `/docs`, npm at the action directory and Actions at `/`. | YAML-parsing coverage regression checks every manager/directory and preserves weekly cooldown/grouping. |
| Full build/test/lint for all ecosystems | Sequential complete Python suite, all Node tests, source typing, hooks, docs, distribution and workflow checks. Existing CI repeats them on the PR commit. | Validation logs and current-SHA CI summary. No frontend, Rust or other package ecosystem exists. |
| Resolve new deprecation warnings | Run Python docs/tests and Node tests with warnings as errors. A new Sphinx 9.2.0 regression requires a tiny exact-version compatibility hook. | Before/after reproduction, regression test and Sphinx upstream issue 14841. |
| No unresolved security advisories | Audit the complete locked Python environment, including tools/docs, and npm lock including dev dependencies. | `pip-audit.log`, `npm-audit-final.json`; no advisory exclusions or forced audit fixes. |
| Search and report every upstream gap behind retained workarounds | Reuse existing reports instead of creating duplicates. New Sphinx, Scriv and artifact SDK findings have minimal reproductions and suggested changes. | Upstream matrix below, archived issue bodies and searches. |
| Research existing components/libraries | Compare official artifact/glob/Pages SDKs, native runtime APIs, uv/Poetry/pip-tools and Dependabot/Renovate. | Component decisions below and primary-source references. |
| Reproduce bugs with automated regressions | Keep resolver-conflict and Sphinx reproductions in experiments; add regressions for lock-constrained audits, docs alignment and pruned traversal. | `experiments/issue-151`, new/updated tests. |
| Prepare release through existing workflow | Add a Scriv changelog fragment; the existing release workflow computes the package version. | `changelog.d/20261114_issue_151_dependencies.md`; no publishing during development. |
| Single prepared PR, forward history, default branch included, clean tree | Commit and push only issue-151-30849d3080e6, inspect PR diff/checks, update its description and mark ready; never merge it. | Git history, final status/ancestry checks and PR 152. |
| Default branch CI green again | Code cannot configure another service's publisher identity or merge itself under this task's rules. Preserve explicit failing main preflight and successful report-only PR behavior. | **Unfinished external criterion:** PyPI trusted publisher for `my-package` is missing; details below. |

## Default branch failure and external prerequisite

The failing run is [CI/CD Pipeline 43575817822](https://github.com/link-foundation/python-ai-driven-development-pipeline-template/actions/runs/43575817822)
at `78024ea7244c3d94d5b4474106d23f739837c497`, after PR 135 merged.
Lines 157–160 of its saved log show PyPI returning HTTP 422, `invalid-publisher`:
no publisher matches the repository/workflow identity. This is a credential
configuration failure, with no evidence that the merged action bumps caused it.
The other completed runs for that SHA passed.

A maintainer of the intended PyPI project must configure its trusted publisher:
owner `link-foundation`, repository
`python-ai-driven-development-pipeline-template`, workflow `release.yml`,
environment blank. The template currently names `my-package`; if that name is
not the intended owned PyPI project, configure the real project name before
registering its publisher. This PR deliberately preserves the actionable
main-branch failure and the PR report mode. No release credentials are bypassed.
The requirement for a green **default branch** remains unfinished until this
external setup and the normal reviewed merge/rerun occur.

## Major migrations and components

- Python 3.15 and Node 26 are current stable language releases, excluding alpha
  tags. Native [Path.walk](https://docs.python.org/3/library/pathlib.html#pathlib.Path.walk)
  can prune ignored dependency trees before visiting them; stable
  [fs.promises.glob](https://nodejs.org/api/fs.html#fspromisesglobpattern-options)
  replaces the local recursive Node walker. Ordered include/exclude matching
  remains necessary because native glob alone does not implement the action's
  multiline artifact input semantics.
- [uv's project synchronization](https://docs.astral.sh/uv/concepts/projects/sync/)
  supplies a universal, platform-aware resolution without a separate requirements
  compiler or Poetry-specific manifest. All project extras, docs and audit tools
  are locked; audit installation uses an exported lock constraint. The initial
  pip-less audit target still prevents an old virtualenv seed from contaminating
  results. Its pip now comes only from the explicitly locked tools extra.
- [mypy 2 migration notes](https://mypy.readthedocs.io/en/stable/changelog.html)
  cover stricter defaults and removal of old Python targets. The project targets
  Python 3.15 and its source passes strict typing. The pre-commit hook now checks
  the same typed `src/` surface as CI rather than feeding untyped test fixtures
  to a strict hook; tests still all run and are linted. Ruff's effective old
  E4/E7/E9/F policy is made explicit and import sorting added; the pre-existing
  `.ruff.toml` takes precedence over pyproject's unused broader rule list.
- [pytest 9 changes](https://docs.pytest.org/en/stable/changelog.html) introduce
  strict mode covering configuration and markers; use that rather than manually
  combining legacy strict flags. [pytest-asyncio migration guidance](https://pytest-asyncio.readthedocs.io/en/stable/how-to-guides/migrate_from_0_23.html)
  removes the old custom event-loop fixture; this repository has none. The 1.5
  `fixture-scope` setting preserves inferred async fixture scope without a warning.
  [pytest-cov 7](https://pytest-cov.readthedocs.io/en/latest/changelog.html) removes
  its subprocess `.pth` mechanism; package coverage here does not require it.
- [Sphinx 8](https://www.sphinx-doc.org/en/master/changes/8.0.html) removes old
  extension APIs not used here; [Sphinx 9](https://www.sphinx-doc.org/en/master/changes/9.0.html)
  changes autodoc internals. Keep the new implementation; do not opt back into
  legacy autodoc. Its bundled Napoleon caller currently tests options truthiness
  via a deprecated mapping interface. An exact-9.2.0 hook supplies ordinary
  truthiness while keeping `no_index` and parameter rendering. MyST 4/5 and Furo
  render the existing Markdown/docs with their current defaults.
- pre-commit-hooks 6 removes unused hooks and raises its own Python floor; no
  removed hook is configured here. Current Ruff uses `ruff-check`. Twine 6/7's
  metadata/format changes accept the new SPDX license string and wheel/sdist;
  this project publishes no eggs. Source changelogs are archived.
- [npm 12 migration](https://github.com/npm/cli/releases/tag/v12.0.0) changes CLI
  output and dependency execution policy. This repository uses package-lock,
  full supported flags and registry packages, with no lifecycle-script dependency,
  shrinkwrap or parsed `npm view --json` output. Fresh `npm ci --ignore-scripts`
  and the explicit ncc build work under 12.2.2. Secretlint and its preset now
  share that lock instead of resolving a separate transient tree.
  The exact npm CLI bootstrap necessarily runs before project-lock installation;
  npm's published tarball bundles its own CLI dependencies. Three isolated
  `adhoc-packages` annotations document that bootstrap boundary. No project
  dependency installation or other zizmor rule is exempted. The first CI run's
  audit failure and its exact lines 396–399 are retained in
  `ci-workflows-43579252326.log`; the corrected regular audit has no findings.
- [GitHub's runtime guidance](https://github.blog/changelog/2026-09-23-node-20-is-no-longer-available-in-github-actions/)
  requires `runs.using: node24`. That field selects a runner ABI rather than the
  development toolchain; setting it to node26 would invalidate the action.
  Ubuntu 26.04 is [generally available](https://github.blog/changelog/2026-09-17-ubuntu-26-generally-available-and-latest-migration/).
  actionlint 1.7.12 lacks its labels, so its documented exact-label configuration
  is used while every other label and workflow rule remains checked.
- Official `@actions/artifact` 6.3.1 remains the current transfer implementation.
  Its supported `skipDecompress` option allows the existing Python ZIP extraction
  to avoid deprecated Buffer construction in unzip-stream. Archiver 8 changes
  its factory/export API, so forcing it into SDK 6.3.1's `^7` contract is unsafe;
  upstream's migration PR is linked below. Patched glob/minimatch overrides remain
  covered by actual filesystem matching and ZIP-byte checks.
- Official `@actions/glob` 0.7.0 still uses removed minimatch methods and pins a
  vulnerable older major. Preserve the secure adapter until upstream migrates
  its partial matching API. Official deploy-pages 5.0.1 still lacks the artifact-ID
  and create-recovery interface used here and retains a deprecated dependency;
  its newer polling backoff does not replace all existing protocol behavior.
- [Dependabot's ecosystem support](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories)
  now includes uv and pre-commit; no bespoke updater is needed. Renovate is a
  viable alternative but introduces unnecessary parallel update ownership here.

## Upstream reports and retained compatibility boundaries

| Dependency / gap | Upstream report | Reproduction / retained local behavior |
| --- | --- | --- |
| Sphinx 9.2.0 Napoleon invokes deprecated options mapping | [New issue 14841](https://github.com/sphinx-doc/sphinx/issues/14841) | `experiments/issue-151/reproduce_sphinx_options.py`, before/after logs, Google parameter and no-index regression; remove exact-version hook when fixed. |
| Scriv 1.8.1 exact dependency pins block current Click and markdown-it-py | [New issue 209](https://github.com/nedbat/scriv/issues/209) | Dry-run resolver conflict logs; preserve declared requirements rather than silently override. Suggested compatible ranges are in the report. |
| actions/glob incompatible with secure minimatch 11 | [Existing toolkit 2564](https://github.com/actions/toolkit/issues/2564) | Existing runtime repro in the report; our native glob adapter preserves ordered patterns, hidden/symlink policy, search roots and implicit descendants. Proposed supported partial-match API is already reported. |
| Artifact unzip-stream deprecated Buffer construction | [Existing toolkit 2003](https://github.com/actions/toolkit/issues/2003) | SDK `skipDecompress` plus strict Python ZIP extraction; actual mocked download/digest regression remains. |
| Artifact SDK still declares Archiver 7 | [Open migration PR 2483](https://github.com/actions/toolkit/pull/2483) | Current registry metadata and actual archive test; no incompatible Archiver 8 override. |
| Artifact Twirp retries bypass recognized transient network failures and lose structured causes | [New toolkit 2579](https://github.com/actions/toolkit/issues/2579) | `experiments/issue-151/reproduce_artifact_network_retry.mjs` exercises the actual published SDK with fake HTTP and no waits. ECONNRESET fails after one call despite maxAttempts=3. Keep bounded producer-independent transport recovery and unique-name safeguards. |
| Pages deprecated punycode dependency | [Existing deploy-pages 434](https://github.com/actions/deploy-pages/issues/434) | Dependency-free REST/OIDC local action; Node tests throw on deprecations. |
| Pages artifact-ID input and bounded create recovery | [Existing deploy-pages 454](https://github.com/actions/deploy-pages/issues/454), [artifact input 399](https://github.com/actions/deploy-pages/issues/399) | Existing mocked tests cover transient/permanent statuses, retries, response loss, polling and cancellation. The issue discussion also records the upstream protocol's artifact/environment reconciliation limitation. |
| actionlint missing Ubuntu labels | [Existing actionlint 682](https://github.com/rhysd/actionlint/issues/682) | Exact known-label config; no broad suppression or unverified fork introduced. |
| actionlint queue and commit-bound local-action schemas | [Existing 657](https://github.com/rhysd/actionlint/issues/657), [654](https://github.com/rhysd/actionlint/pull/654), [711](https://github.com/rhysd/actionlint/issues/711) | Narrow existing message/path exceptions; malformed unrelated actions remain checked by tests and zizmor. |
| Lychee 0.24.2 omits connection/TLS failures from its retry policy | [Existing lychee 2297](https://github.com/lycheeverse/lychee/issues/2297) | Keep the bounded transient-network recheck; the current upstream report already contains the failure, reproduction and proposed retry-policy change. |

Existing reports already contain reproductions and suggested changes. In
particular, the actionlint maintainer discussion explicitly objects to repetitive
bot comments; this work links and preserves those reports rather than posting
duplicates without a new finding. Registry-constrained transitive packages are
listed individually in the npm table; their declaring parent's major migration
must precede an API-compatible replacement.
