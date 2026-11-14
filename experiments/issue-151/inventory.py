"""Snapshot registry metadata without installing or executing dependencies."""

import concurrent.futures
import json
import re
import subprocess
import tomllib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "dev/log/issues/151/pulls/152"


def fetch(url):
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def pypi(name):
    data = fetch(f"https://pypi.org/pypi/{name}/json")
    info = data["info"]
    return name, {
        k: info[k]
        for k in ("version", "requires_python", "project_urls", "requires_dist")
    }


def npm(name):
    data = fetch(f"https://registry.npmjs.org/{name}/latest")
    return name, {
        k: data.get(k) for k in ("version", "engines", "dependencies", "repository")
    }


def github(name):
    result = subprocess.run(
        ["gh", "api", f"repos/{name}/releases/latest"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        result = subprocess.run(
            ["gh", "api", f"repos/{name}/tags?per_page=5"],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        return name, {"tag_name": data[0]["name"], "tags": data}
    data = json.loads(result.stdout)
    return name, {k: data[k] for k in ("tag_name", "published_at", "html_url", "body")}


def main():
    manifest = tomllib.loads((ROOT / "pyproject.toml").read_text())
    reqs = manifest["build-system"]["requires"] + sum(
        manifest["project"]["optional-dependencies"].values(), []
    )
    py_names = {re.split(r"[\[>=<~! ]", r)[0] for r in reqs}
    py_names |= {
        "pip",
        "uv",
        "build",
        "twine",
        "pip-audit",
        "shellcheck-py",
        "zizmor",
        "packaging",
        "pyyaml",
    }
    lock = json.loads((ROOT / ".github/actions/artifact/package-lock.json").read_text())
    npm_names = {p.rsplit("node_modules/", 1)[-1] for p in lock["packages"] if p}
    npm_names |= {
        "secretlint",
        "@secretlint/secretlint-rule-preset-recommend",
        "npm",
        "npm-check-updates",
        "@actions/glob",
    }
    workflows = "\n".join(p.read_text() for p in (ROOT / ".github").rglob("*.yml"))
    actions = {
        m.split("/")[0] + "/" + m.split("/")[1]
        for m in re.findall(r"uses: ([\w-]+/[\w/-]+)@", workflows)
    }
    hooks = re.findall(
        r"repo: https://github.com/([\w.-]+/[\w.-]+)",
        (ROOT / ".pre-commit-config.yaml").read_text(),
    )
    repositories = (
        actions
        | set(hooks)
        | {
            "rhysd/actionlint",
            "lycheeverse/lychee",
            "actions/deploy-pages",
            "actions/upload-artifact",
            "actions/download-artifact",
            "nodejs/node",
            "python/cpython",
            "astral-sh/uv",
            "zizmorcore/zizmor",
        }
    )
    snapshot = {
        "python_old": reqs,
        "npm_old": lock,
        "actions_old": sorted(set(re.findall(r"uses: ([^\s]+)", workflows))),
        "hooks_old": (ROOT / ".pre-commit-config.yaml").read_text(),
    }
    for kind, names, function in [
        ("pypi", py_names, pypi),
        ("npm", npm_names, npm),
        ("github", repositories, github),
    ]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            snapshot[kind] = dict(executor.map(function, sorted(names)))
        print(f"{kind}: {len(names)} dependencies", flush=True)
    (OUT / "registry-initial.json").write_text(json.dumps(snapshot, indent=2) + "\n")
    for kind in ("pypi", "github"):
        print(
            kind,
            {k: v.get("version", v.get("tag_name")) for k, v in snapshot[kind].items()},
        )
    print(
        "npm direct",
        {
            k: snapshot["npm"][k]["version"]
            for k in (
                "@actions/artifact",
                "@actions/core",
                "@actions/glob",
                "minimatch",
                "@vercel/ncc",
                "secretlint",
                "npm",
            )
        },
    )


if __name__ == "__main__":
    main()
