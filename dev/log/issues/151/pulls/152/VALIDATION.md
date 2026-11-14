# Verification checkpoint

Date: 2026-11-14 UTC. Implementation commit:
`6f2c3bcc6b7230c48e0b822b43a7fc94c110d859`. The following research commit
also removes a redundant unlocked pre-commit installation from README setup.
Final commit checks remain visible on [PR 152](https://github.com/link-foundation/python-ai-driven-development-pipeline-template/pull/152).

| Verification | Result / saved evidence |
| --- | --- |
| `.venv/bin/python -W error -m pytest --cov=src --cov-report=term-missing` | 823 passed, one existing multi-language-layout skip; 100% package coverage. `pytest-verified.log` |
| `node --throw-deprecation --test tests/*.test.mjs` | All 49 pass. `node-tests-final.log` |
| Fresh `npm ci --ignore-scripts`, `npm run build`, full Secretlint | Pass. `npm-ci-final.log`, `npm-build-final.log`, `secretlint-evidence.log` |
| Locked Python all-extra audit | No known vulnerabilities. `pip-audit.log`; only the local unpublished template project lacks a registry record. |
| npm production and development audit | Zero vulnerabilities. `npm-audit-final.json` |
| Strict Sphinx, wheel/sdist, Twine metadata | Pass. `docs-build.log`, `python-build.log`, `twine-check.log` |
| Ruff lint/format, strict source mypy | Pass. `ruff-verified.log`, `mypy-final.log` |
| Full pre-commit including ShellCheck and file checks | Pass. `pre-commit-final.log` |
| actionlint and zizmor | Pass. `actionlint-final.log`, `zizmor-verified.log`; three exact npm CLI bootstrap annotations explained in RESEARCH.md. |
| Source/Markdown size policy after adding research | Pass. `file-size-final.log` |
| Sphinx minimal reproducer | Fails before hook, passes after; `sphinx-before.log`, `sphinx-after.log` and regression test. |
| Scriv's two outdated exact requirements | Both latest-version resolutions fail before installation; `scriv-conflict.log`, `scriv-markdown-conflict.log`. Upstream issue 209. |
| Actual artifact SDK transient-network retry | Reproduced with fake HTTP, finite three-attempt budget and no waits; `artifact-network-repro.log`. Upstream issue 2579. |
| Main ancestry | Fetched origin/main; `git merge-base --is-ancestor origin/main HEAD` succeeds. No merge or history rewrite. |
| PR diff review | Read implementation changes, manifests, tests and workflow changes from `gh pr diff 152`; generated bundle checked by CI's reproducibility and actual artifact roundtrip. |

All six implementation-SHA workflow runs passed, each created at
2026-11-14T09:16:38Z. Raw status/SHA evidence: `ci-implementation.json`.

| Workflow | Successful run |
| --- | --- |
| CI/CD Pipeline | [43579782575](https://github.com/link-foundation/python-ai-driven-development-pipeline-template/actions/runs/43579782575) |
| Workflows | [43579782619](https://github.com/link-foundation/python-ai-driven-development-pipeline-template/actions/runs/43579782619) |
| Security | [43579782638](https://github.com/link-foundation/python-ai-driven-development-pipeline-template/actions/runs/43579782638) |
| Docs | [43579782556](https://github.com/link-foundation/python-ai-driven-development-pipeline-template/actions/runs/43579782556) |
| Broken Link Checker | [43579782621](https://github.com/link-foundation/python-ai-driven-development-pipeline-template/actions/runs/43579782621) |
| Dependabot Health | [43579782555](https://github.com/link-foundation/python-ai-driven-development-pipeline-template/actions/runs/43579782555) |

Initial implementation Workflows run 43579252326 failed solely because three
exact npm CLI bootstrap commands triggered `adhoc-packages`: saved log lines
396–399. Commit 6f2c3bc documents that boundary with narrow inline annotations;
its subsequent regular audit has no findings. Other security rules remain active.

The default-branch failure is a separate, still unfinished external requirement:
main run 43575817822 returns PyPI `invalid-publisher` (log lines 157–160).
RESEARCH.md and the PR describe the required publisher identity and placeholder
project-name correction. Pull-request checks do not claim to prove a successful
main-branch release. This PR remains unmerged.
