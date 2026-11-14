# Issue 151 / PR 152 work plan

Objective: implement and verify every acceptance criterion in the single prepared
PR, with registry evidence for every dependency and explicit external blockers.
The native goal remains active until the unfinished criterion below is met.

## Requirements and decisions

The complete prose requirement inventory, possible approaches, selected solutions
and implementation/verification mapping are in [RESEARCH.md](RESEARCH.md).

| Work item | Status and evidence |
| --- | --- |
| Complete issue/comments, PR conversation/inline/reviews and required children | Read and archived; final API refresh confirms one issue comment, no native children or PR feedback. |
| Diagnose default CI after Dependabot PR 135 | Completed: only pipeline failed at missing PyPI trusted publisher, not an action-version regression. Original log retained. |
| Current Python, dev/docs/build/audit tools, honest floors and reproducibility | Implemented: current direct floors, universal uv.lock, frozen install helper, lock-constrained audits. |
| Current npm direct/dev/transitives and generated bundle | Implemented: exact latest direct pins, upgraded allowed transitives, Secretlint included in lock, rebuilt ncc output. |
| Current Actions/hooks/toolchains/images in all occurrences | Implemented: complete release tags, verified immutable hashes/digest, Python 3.15.2, Node 26.13.1, npm 12.2.2, Ubuntu 26.04. Supported action runtime ABI remains node24. |
| Every dependency before/current/latest table | Generated from archived live registries: DEPENDENCIES-PYTHON.md, DEPENDENCIES-NPM.md, DEPENDENCIES-AUTOMATION.md. Every retained version has a parent constraint or supported-ABI reason. |
| Major migration research and upstream feature adoption | Completed: RESEARCH.md and archived migration sources. Native glob/Path.walk, pytest strict mode, current asyncio scope; removed old TOML fallback. |
| Dependabot every ecosystem/directory | Implemented: uv root, pip docs, npm action, Actions and pre-commit, with existing weekly cooldowns/groups. Coverage regression passes. |
| Minimal bug reproductions and regression tests | Implemented: Sphinx before/after, locked audit constraints, docs consistency, ignored-directory traversal and existing actual artifact/ZIP regressions. |
| Full local verification | Python: 823 passed, one existing layout-specific skip, 100% package coverage with warnings as errors. Node: all 49 pass with deprecations as errors. Full pre-commit passes. Docs, distributions, strict typing and workflow linters pass. |
| No unresolved security advisories | Both locked-tree audits clean. Default alert 3 affects old fast-xml-parser 5.11.2; this PR resolves 5.12.1 (patched since 5.12.0). |
| Upstream reports for dependency gaps | New Sphinx 14841, Scriv 209 and toolkit 2579; existing toolkit, Pages and actionlint reports reviewed and linked, with no repetitive duplicate comments. See RESEARCH.md. |
| Release preparation | Scriv fragment added; existing automatic version-bump workflow retained. |
| Commit/push, fresh CI, self-review, clean tree, PR description and readiness | Implementation 3ebb751 and bootstrap-audit correction 6f2c3bc pushed; all six implementation-SHA workflows pass. PR title/body updated and code diff reviewed. Final research commit, its CI/status check and readiness follow this checkpoint. |
| Green default branch CI | **UNFINISHED: external PyPI maintainer must configure the trusted publisher for the intended project; normal reviewed merge/rerun then required.** Preserve explicit main failure and report-only PR mode; never claim this criterion complete. |

## Remaining execution

1. Commit reviewed research separately; local full hooks and security scanning pass.
2. Inspect every final-SHA CI run. Save non-passing logs, identify exact failing
   lines and fix code causes without bypassing checks. Implementation-SHA runs
   are all green; see VALIDATION.md.
3. Confirm clean status, final PR diff and latest feedback; mark the PR ready.
4. Leave the PR unmerged and the external default-CI criterion explicitly
   unfinished. Do not mark the native goal complete while it remains unmet.
