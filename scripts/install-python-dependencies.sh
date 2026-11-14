#!/usr/bin/env bash
# Install the same complete, locked environment locally and in every CI job.
set -euo pipefail
python -m pip install --disable-pip-version-check pip==26.3 uv==0.13.8
uv sync --locked --all-extras
if [[ -n "${GITHUB_PATH:-}" ]]; then
  echo "$PWD/.venv/bin" >> "$GITHUB_PATH"
fi
