### Changed

- Update Python, npm, Actions, pre-commit hooks and CI toolchains to current
  releases. Python 3.15 is now the supported baseline; CI uses Python 3.15.2
  and Node.js 26.13.1. Local JavaScript actions retain the runner's node24 ABI.
- Lock all Python development, documentation, build and security tools in
  `uv.lock`; use locked installations and audit the locked dependency tree.
- Use current pytest strict configuration and asyncio fixture scopes, SPDX
  package license metadata, and pathlib traversal that prunes ignored trees.
- Add weekly Dependabot coverage for Python manifests and pre-commit hooks.
