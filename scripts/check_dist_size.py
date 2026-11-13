#!/usr/bin/env python3
"""Reject distributions over the per-file upload budget before publishing.

DIST_SIZE_LIMIT_BYTES or --max-bytes overrides the conservative 99 MB default.
dist_size_bytes reports the largest individual file, since PyPI limits each
upload independently. Archive diagnostics read headers without extracting data.
"""

from __future__ import annotations

import argparse
import heapq
import os
import sys
import tarfile
import zipfile
from pathlib import Path

DEFAULT_MAX_BYTES = 99_000_000


def annotation(message: str) -> None:
    """Print an escaped Actions error annotation."""
    escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::error title=Distribution size::{escaped}")


def largest_members(path: Path) -> list[tuple[int, str]]:
    """Return the ten largest members by uncompressed size without extraction."""
    if path.suffix in {".whl", ".zip"}:
        with zipfile.ZipFile(path) as archive:
            return heapq.nlargest(
                10, ((entry.file_size, entry.filename) for entry in archive.infolist())
            )
    with tarfile.open(path, mode="r|*") as archive:
        return heapq.nlargest(
            10, ((entry.size, entry.name) for entry in archive if entry.isfile())
        )


def check_dist_size(dist_dir: Path, max_bytes: int = DEFAULT_MAX_BYTES) -> bool:
    """Check every dist/* file and emit the largest file size even on failure."""
    if max_bytes <= 0:
        raise ValueError("Distribution size budget must be a positive byte count")
    files = sorted(path for path in dist_dir.glob("*") if path.is_file())
    largest = max((path.stat().st_size for path in files), default=0)
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.write(f"dist_size_bytes={largest}\n")
    if not files:
        annotation(f"No distribution files found in {dist_dir}")
        return False
    valid = True
    for path in files:
        size = path.stat().st_size
        print(f"{str(path)!r}: {size} bytes (budget {max_bytes})")
        if size <= max_bytes:
            continue
        valid = False
        annotation(f"{path}: {size} bytes exceeds the {max_bytes}-byte upload budget")
        print("Largest members (uncompressed bytes):")
        try:
            for member_size, name in largest_members(path):
                print(f"  {member_size:>12}  {name!r}")
        except (OSError, tarfile.TarError, zipfile.BadZipFile) as error:
            # An unreadable archive must never turn a size failure into success.
            print(f"  Cannot inspect {str(path)!r}: {error}")
    return valid


def main() -> int:
    """Run the standalone gate with CLI or environment configuration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=os.environ.get("DIST_SIZE_LIMIT_BYTES", DEFAULT_MAX_BYTES),
    )
    args = parser.parse_args()
    try:
        return 0 if check_dist_size(args.dist_dir, args.max_bytes) else 1
    except (OSError, ValueError) as error:
        annotation(str(error))
        return 1


if __name__ == "__main__":
    sys.exit(main())
