#!/usr/bin/env python3
"""Read-only live verification of both zizmor layouts and PR #135's update."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_zizmor_compatibility import check_compatibility  # noqa: E402


def main() -> None:
    workflow = Path(".github/workflows/workflows.yml").read_text()
    ref, version = check_compatibility(workflow)
    print(f"Current workflow: zizmor-action@{ref} supports CLI {version}")
    updated = workflow.replace(f"zizmor-action@{ref}", "zizmor-action@v0.8.1")
    ref, version = check_compatibility(updated)
    print(f"PR #135 update: zizmor-action@{ref} supports CLI {version}")


if __name__ == "__main__":
    main()
