# Verification evidence

The [requirement inventory](PLAN.md) maps every issue requirement to code and
regressions. [Recorded baseline output](reproduction.txt) comes from
`python experiments/issue-147/reproduce_original.py`, using immutable original
scripts, bounded local Git repositories and small loopback HTTP fixtures.

Local verification used focused existing pytest suites covering release
integrity/retries, lychee installation/scanning, distribution size, source size,
workflow policies and the local publisher. Ruff lint and formatting, Bash syntax,
the repository size gate and `git diff --check` passed. The final source-exclusion
regression passed with all 13 source-size tests; it proves `.github` helpers and
names containing `dist`, `build` or `env` remain checked while actual generated
folders remain excluded.

Initial implementation commit `87a53858a0381560a6a8a7ce1d409205018876e2`
passed the full existing CI, including **757 tests passed, one skipped**, package
build, pinned ShellCheck without the pipx PATH warning, workflow/security audits,
CodeQL and online links:

- [CI/CD Pipeline](https://github.com/link-foundation/python-ai-driven-development-pipeline-template/actions/runs/43397440523)
- [Workflows](https://github.com/link-foundation/python-ai-driven-development-pipeline-template/actions/runs/43397440389)
- [Broken Link Checker](https://github.com/link-foundation/python-ai-driven-development-pipeline-template/actions/runs/43397440401)
- [Security](https://github.com/link-foundation/python-ai-driven-development-pipeline-template/actions/runs/43397440375)

Final-commit CI and review readiness are recorded in
[PR 148](https://github.com/link-foundation/python-ai-driven-development-pipeline-template/pull/148)
after pushing the source-exclusion regression. Full builds/tests are left to CI
to avoid duplicating their resource use locally. No production release or merge
is performed during verification.
