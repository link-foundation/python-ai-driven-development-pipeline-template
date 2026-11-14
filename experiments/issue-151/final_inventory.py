"""Record all locked versions and registry latest releases with bounded I/O."""

import concurrent.futures
import json
import tomllib
from datetime import UTC, datetime

from inventory import OUT, ROOT, npm, pypi


def collect():
    python_lock = tomllib.loads((ROOT / "uv.lock").read_text())
    npm_lock = json.loads(
        (ROOT / ".github/actions/artifact/package-lock.json").read_text()
    )
    baseline = json.loads((OUT / "registry-initial.json").read_text())
    py_names = {
        item["name"] for item in python_lock["package"] if "registry" in item["source"]
    }
    npm_names = {
        key.rsplit("node_modules/", 1)[-1] for key in npm_lock["packages"] if key
    }
    npm_names |= set(baseline["npm"])
    result = {"queried_at": datetime.now(UTC).isoformat()}
    for kind, names, query in [("pypi", py_names, pypi), ("npm", npm_names, npm)]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            result[kind] = dict(executor.map(query, sorted(names)))
        print(f"{kind}: {len(names)} registry responses", flush=True)
    result["python_lock"] = [
        {k: p[k] for k in ("name", "version", "dependencies") if k in p}
        for p in python_lock["package"]
    ]
    result["npm_lock"] = npm_lock
    (OUT / "registry-final.json").write_text(json.dumps(result, indent=2) + "\n")
    mismatches = {"python": {}, "npm": {}}
    for item in python_lock["package"]:
        name = item["name"]
        if (
            name in result["pypi"]
            and item["version"] != result["pypi"][name]["version"]
        ):
            mismatches["python"][name] = {
                "locked": item["version"],
                "latest": result["pypi"][name]["version"],
            }
    for key, item in npm_lock["packages"].items():
        if key:
            name = key.rsplit("node_modules/", 1)[-1]
            if item["version"] != result["npm"][name]["version"]:
                mismatches["npm"][key] = {
                    "locked": item["version"],
                    "latest": result["npm"][name]["version"],
                }
    (OUT / "nonlatest.json").write_text(json.dumps(mismatches, indent=2) + "\n")
    print(json.dumps(mismatches, indent=2))


if __name__ == "__main__":
    collect()
