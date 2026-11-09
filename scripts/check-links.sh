#!/usr/bin/env bash
# Preserve the lychee-action report/output contract without its installer.
set -euo pipefail
[[ "${LYCHEE_CHECK_DEBUG:-}" != 1 ]] || set -x

report=lychee/out.md
mkdir -p lychee
# Never mistake a previous report for a successful scan.
rm -f "$report"
exit_code=0
lychee --format markdown --output "$report" "$@" || exit_code=$?
echo "exit_code=$exit_code" >> "${GITHUB_OUTPUT:?}"

if [[ ! -s "$report" ]]; then
  echo "::error title=lychee scan::No report was produced (exit $exit_code). Check arguments or scanner errors."
  exit 1
fi
cat "$report"
cat "$report" >> "${GITHUB_STEP_SUMMARY:?}"

# A valid Markdown report must contain a positive link count. Treat malformed
# output as a scanner failure, not as broken links eligible for recovery.
if ! python3 - "$report" <<'PY'
import re
import sys
from pathlib import Path

report = Path(sys.argv[1]).read_text()
match = re.search(r"^\|\s*(?:🔍\s*)?Total\s*\|\s*(\d+)\s*\|", report, re.MULTILINE)
if not match or int(match.group(1)) == 0:
    print("::error title=lychee scan::No links were checked or report total is missing.")
    raise SystemExit(1)
PY
then
  exit 1
fi

# Exit 2 with a report means broken links. Downstream transport retries and
# archive suggestions own that outcome; all other scanner errors fail here.
if [[ "$exit_code" != 0 && "$exit_code" != 2 ]]; then
  echo "::error title=lychee scan::Scanner failed with exit $exit_code."
  exit 1
fi
