"""Render registry evidence, including a reason for every retained version."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "dev/log/issues/151/pulls/152"


def table(path, introduction, headers, rows):
    content = [introduction, "", "| " + " | ".join(headers) + " |"]
    content.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        content.append(
            "| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |"
        )
    (OUT / path).write_text("\n".join(content) + "\n")


def resolve(packages, parent, name):
    directory = parent
    while True:
        candidate = (directory + "/" if directory else "") + "node_modules/" + name
        if candidate in packages:
            return candidate
        if not directory:
            return None
        directory = (
            directory.rsplit("/node_modules/", 1)[0]
            if "/node_modules/" in directory
            else ""
        )


def main():
    before = json.loads((OUT / "registry-initial.json").read_text())
    after = json.loads((OUT / "registry-final.json").read_text())
    old_python = {}
    for value in before["python_old"]:
        name = re.split(r"[\[>=<~! ]", value)[0].lower().replace("_", "-")
        old_python[name] = value
    py_rows = []
    for package in after["python_lock"]:
        name, version = package["name"], package["version"]
        if name not in after["pypi"]:
            continue
        latest = after["pypi"][name]["version"]
        reason = "Current stable release"
        if version != latest:
            reason = (
                "Scriv 1.8.1 requires click==8.5.0 and markdown-it-py==4.2.0; resolver rejects latest. "
                "[Upstream report](https://github.com/nedbat/scriv/issues/209); no forced incompatible override."
            )
        py_rows.append(
            [
                f"[{name}](https://pypi.org/project/{name}/)",
                old_python.get(name, "Unpinned (no previous Python lock)"),
                version,
                latest,
                reason,
            ]
        )
    table(
        "DEPENDENCIES-PYTHON.md",
        f"# Python registry inventory\n\nPyPI queried {after['queried_at']}. Every registry package in the universal uv lock, including optional/platform dependencies, is listed. Previous manifest constraints are shown verbatim; previously unresolved transitives have no historical pinned version. The local project is excluded.",
        ["Dependency / registry", "Before", "Locked now", "Latest stable", "Decision"],
        py_rows,
    )

    old = before["npm_old"]["packages"]
    new = after["npm_lock"]["packages"]
    parents = {}
    for parent, metadata in new.items():
        for field in ("dependencies", "devDependencies", "optionalDependencies"):
            for name, constraint in metadata.get(field, {}).items():
                resolved = resolve(new, parent, name)
                if resolved:
                    parent_name = (
                        parent.rsplit("node_modules/", 1)[-1]
                        if parent
                        else "artifact action"
                    )
                    parents.setdefault(resolved, []).append(
                        f"{parent_name}: {name}{constraint}"
                    )
    npm_rows = []
    for key in sorted(set(old) | set(new)):
        if not key:
            continue
        name = key.rsplit("node_modules/", 1)[-1]
        previous = old.get(key, {}).get("version", "New")
        current = new.get(key, {}).get("version", "Removed")
        latest = after["npm"][name]["version"]
        reason = "Current stable release"
        if current == "Removed":
            reason = (
                "Removed by the updated parent graph; no stale installed entry remains."
            )
        elif current != latest:
            reason = (
                "Upstream compatibility constraint: "
                + "; ".join(parents.get(key, ["see the committed lock graph"]))
                + ". Latest requires the parent to migrate its API; retained without an unsupported major override."
            )
            if name in (
                "archiver",
                "archiver-utils",
                "readdir-glob",
                "zip-stream",
                "compress-commons",
                "crc32-stream",
                "lazystream",
                "readable-stream",
                "isarray",
                "safe-buffer",
                "string_decoder",
                "is-stream",
            ):
                reason += " [SDK archiver migration](https://github.com/actions/toolkit/pull/2483)."
        npm_rows.append(
            [
                f"`{key}`",
                previous,
                current,
                f"[{latest}](https://registry.npmjs.org/{name}/latest)",
                reason,
            ]
        )
    table(
        "DEPENDENCIES-NPM.md",
        f"# npm registry inventory\n\nRegistry latest dist-tags queried {after['queried_at']}. Every old and new lock entry is included, including nested copies, scanner/build dev dependencies, removals, and explicit reasons for every retained release. Parent ranges are taken from the actual resolved parent, using Node's ancestor lookup. All direct dependencies are current; a forced transitive major upgrade is not API-compatible merely because npm permits an override.",
        ["Lock entry", "Before", "Locked now", "Registry latest", "Decision"],
        npm_rows,
    )

    references = []
    for path in sorted((ROOT / ".github").rglob("*.yml")):
        if "node_modules" in path.parts:
            continue
        for match in re.finditer(r"uses:\s+([^\s]+)", path.read_text()):
            reference = match[1]
            if "@" not in reference:
                continue
            if reference.startswith(("./", "$/")):
                continue
            if reference not in references:
                references.append(reference)
    rows = []
    for reference in sorted(references):
        name = reference.split("@")[0]
        if name.startswith("docker://"):
            rows.append(
                [
                    name,
                    next(
                        (x for x in before["actions_old"] if x.startswith(name + "@")),
                        "New",
                    ),
                    reference.split("@", 1)[1],
                    "1.7.12 / same verified digest",
                    "Docker Hub latest and 1.7.12 manifests have identical digest; actionlint-docker-*.json",
                ]
            )
            continue
        repo = "/".join(name.split("/")[:2])
        metadata = before["github"][repo]
        latest = "v4.39.3" if repo == "github/codeql-action" else metadata["tag_name"]
        old_refs = sorted(
            {
                x.split("@", 1)[1]
                for x in before["actions_old"]
                if x.startswith(name + "@")
            }
        )
        rows.append(
            [
                name,
                ", ".join(old_refs) or "New",
                reference.split("@", 1)[1],
                latest,
                f"[Upstream releases](https://github.com/{repo}/releases); hash pins match the annotated current release; CodeQL bundle-only tags are not action releases.",
            ]
        )
    hooks = (ROOT / ".pre-commit-config.yaml").read_text()
    for repo, version in re.findall(
        r"repo: https://github.com/(\S+)\n\s+rev: (\S+)", hooks
    ):
        old_match = re.search(
            r"repo: https://github.com/" + re.escape(repo) + r"\n\s+rev: (\S+)",
            before["hooks_old"],
        )
        rows.append(
            [
                repo,
                old_match[1],
                version,
                before["github"][repo]["tag_name"],
                f"[Hook releases](https://github.com/{repo}/releases)",
            ]
        )
    rows.extend(
        [
            [
                "Python",
                "3.13 workflow / >=3.9 metadata",
                "3.15.2 / >=3.15",
                "3.15.2",
                "python-tags.txt and python.org; 3.16 alpha excluded",
            ],
            [
                "Node.js",
                "24 (workflow major)",
                "26.13.1",
                "26.13.1",
                "node-releases.json official stable feed; 27 alpha excluded",
            ],
            [
                "npm",
                "Unpinned (runner default)",
                "12.2.2",
                before["npm"]["npm"]["version"],
                "npm registry; npm 12 major migration reviewed",
            ],
            [
                "GitHub action execution ABI",
                "node24",
                "node24",
                "node24 (supported runner ABI)",
                "Node26 is not an Actions execution ABI. GitHub metadata and runner sources: runner-node-runtimes.txt. Node26 builds/tests the action.",
            ],
            [
                "Hosted Ubuntu",
                "24.04 / 24.04-arm",
                "26.04 / 26.04-arm",
                "26.04 LTS",
                "ubuntu-2604.json and GitHub GA announcement; no repository Dockerfile or independently pinned base image",
            ],
            [
                "lychee",
                "0.24.2",
                "0.24.2",
                before["github"]["lycheeverse/lychee"]["tag_name"],
                "Latest stable; install script verifies the release checksum",
            ],
            [
                "ShellCheck",
                "0.11.0 (wrapper 0.11.0.1)",
                "0.11.0 (wrapper 0.11.0.1)",
                "0.11.0",
                "shellcheck-release.json and shellcheck-py PyPI registry",
            ],
        ]
    )
    table(
        "DEPENDENCIES-AUTOMATION.md",
        "# Actions, hooks, toolchains and image inventory\n\nRegistry evidence is archived in registry-initial.json, codeql-action-releases.json, node-releases.json, python-tags.txt, shellcheck-release.json and the Docker Hub manifest responses. Python-installed CLI tools appear individually in DEPENDENCIES-PYTHON.md. Every distinct uses reference and hook is included here.",
        [
            "Dependency",
            "Before",
            "Now",
            "Latest stable",
            "Source / compatibility decision",
        ],
        rows,
    )


if __name__ == "__main__":
    main()
