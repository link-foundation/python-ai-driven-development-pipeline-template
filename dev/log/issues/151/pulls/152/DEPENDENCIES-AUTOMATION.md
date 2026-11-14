# Actions, hooks, toolchains and image inventory

Registry evidence is archived in registry-initial.json, codeql-action-releases.json, node-releases.json, python-tags.txt, shellcheck-release.json and the Docker Hub manifest responses. Python-installed CLI tools appear individually in DEPENDENCIES-PYTHON.md. Every distinct uses reference and hook is included here.

| Dependency | Before | Now | Latest stable | Source / compatibility decision |
| --- | --- | --- | --- | --- |
| actions/cache/restore | v6 | v6.1.0 | v6.1.0 | [Upstream releases](https://github.com/actions/cache/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases. |
| actions/cache/save | v6 | v6.1.0 | v6.1.0 | [Upstream releases](https://github.com/actions/cache/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases. |
| actions/checkout | v7 | v7.0.1 | v7.0.1 | [Upstream releases](https://github.com/actions/checkout/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases. |
| actions/configure-pages | v6 | v6.0.0 | v6.0.0 | [Upstream releases](https://github.com/actions/configure-pages/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases. |
| actions/dependency-review-action | v5 | v5.0.0 | v5.0.0 | [Upstream releases](https://github.com/actions/dependency-review-action/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases. |
| actions/setup-node | v7 | v7.1.0 | v7.1.0 | [Upstream releases](https://github.com/actions/setup-node/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases. |
| actions/setup-python | v7 | v7.1.0 | v7.1.0 | [Upstream releases](https://github.com/actions/setup-python/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases. |
| codecov/codecov-action | 303a32d7a59b442fa8d48b6a1cc6825c09c847a5 | 303a32d7a59b442fa8d48b6a1cc6825c09c847a5 | v7.1.1 | [Upstream releases](https://github.com/codecov/codecov-action/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases. |
| docker/build-push-action | v7 | v7.4.0 | v7.4.0 | [Upstream releases](https://github.com/docker/build-push-action/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases. |
| docker/login-action | v4 | v4.8.0 | v4.8.0 | [Upstream releases](https://github.com/docker/login-action/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases. |
| docker/setup-buildx-action | v4 | v4.4.1 | v4.4.1 | [Upstream releases](https://github.com/docker/setup-buildx-action/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases. |
| docker://rhysd/actionlint | docker://rhysd/actionlint@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667 | sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667 | 1.7.12 / same verified digest | Docker Hub latest and 1.7.12 manifests have identical digest; actionlint-docker-*.json |
| github/codeql-action/analyze | v4 | v4.39.3 | v4.39.3 | [Upstream releases](https://github.com/github/codeql-action/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases. |
| github/codeql-action/autobuild | v4 | v4.39.3 | v4.39.3 | [Upstream releases](https://github.com/github/codeql-action/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases. |
| github/codeql-action/init | v4 | v4.39.3 | v4.39.3 | [Upstream releases](https://github.com/github/codeql-action/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases. |
| pypa/gh-action-pypi-publish | 7245906fb61fa33a13554f9d5fb856fe61758086 | 7245906fb61fa33a13554f9d5fb856fe61758086 | v1.14.3 | [Upstream releases](https://github.com/pypa/gh-action-pypi-publish/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases. |
| zizmorcore/zizmor-action | v0.8.1 | v0.8.1 | v0.8.1 | [Upstream releases](https://github.com/zizmorcore/zizmor-action/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases. |
| shellcheck-py/shellcheck-py | v0.11.0.1 | v0.11.0.1 | v0.11.0.1 | [Hook releases](https://github.com/shellcheck-py/shellcheck-py/releases) |
| pre-commit/pre-commit-hooks | v5.0.0 | v6.0.0 | v6.0.0 | [Hook releases](https://github.com/pre-commit/pre-commit-hooks/releases) |
| astral-sh/ruff-pre-commit | v0.8.4 | v0.17.5 | v0.17.5 | [Hook releases](https://github.com/astral-sh/ruff-pre-commit/releases) |
| pre-commit/mirrors-mypy | v1.13.0 | v2.4.1 | v2.4.1 | [Hook releases](https://github.com/pre-commit/mirrors-mypy/releases) |
| Python | 3.13 workflow / >=3.9 metadata | 3.15.2 / >=3.15 | 3.15.2 | python-tags.txt and python.org; 3.16 alpha excluded |
| Node.js | 24 (workflow major) | 26.13.1 | 26.13.1 | node-releases.json official stable feed; 27 alpha excluded |
| npm | Unpinned (runner default) | 12.2.2 | 12.2.2 | npm registry; npm 12 major migration reviewed |
| GitHub action execution ABI | node24 | node24 | node24 (supported runner ABI) | Node26 is not an Actions execution ABI. GitHub metadata and runner sources: runner-node-runtimes.txt. Node26 builds/tests the action. |
| Hosted Ubuntu | 24.04 / 24.04-arm | 26.04 / 26.04-arm | 26.04 LTS | ubuntu-2604.json and GitHub GA announcement; no repository Dockerfile or independently pinned base image |
| lychee | 0.24.2 | 0.24.2 | lychee-v0.24.2 | Latest stable; install script verifies the release checksum |
| ShellCheck | 0.11.0 (wrapper 0.11.0.1) | 0.11.0 (wrapper 0.11.0.1) | 0.11.0 | shellcheck-release.json and shellcheck-py PyPI registry |
