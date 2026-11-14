#!/usr/bin/env python3
"""Report stale Dependabot PRs even when Dependabot's scheduled runs succeed."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REBASE_BANNER = "Dependabot is rebasing this PR"


def find_stuck(
    pulls: list[dict],
    *,
    now: dt.datetime,
    max_open_days: int = 14,
    max_rebase_banners: int = 2,
) -> list[tuple[dict, list[str]]]:
    """Select open Dependabot PRs exceeding either independent threshold."""
    stuck = []
    for pull in pulls:
        if (
            pull["state"] != "open"
            or (pull.get("user") or {}).get("login") != "dependabot[bot]"
        ):
            continue
        created = dt.datetime.fromisoformat(pull["created_at"].replace("Z", "+00:00"))
        if created.tzinfo is None:
            msg = f"PR #{pull['number']} has a timestamp without a timezone"
            raise ValueError(msg)
        age = now - created
        reasons = []
        if age > dt.timedelta(days=max_open_days):
            reasons.append(
                f"open for {age.total_seconds() / 86400:.2f} days (limit {max_open_days})"
            )
        banners = (pull.get("body") or "").count(REBASE_BANNER)
        if banners > max_rebase_banners:
            reasons.append(
                f"{banners} unfinished rebase banners (limit {max_rebase_banners})"
            )
        if reasons:
            stuck.append((pull, reasons))
    return stuck


def list_pulls(repository: str) -> list[dict]:
    """Fetch every open-PR page; API errors must never look like healthy scans."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        msg = "Set GITHUB_REPOSITORY or --repo to owner/repository"
        raise ValueError(msg)
    result = subprocess.run(
        [
            "gh",
            "api",
            "--paginate",
            "--slurp",
            f"repos/{repository}/pulls?state=open&per_page=100",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    pages = json.loads(result.stdout)
    if (
        not isinstance(pages, list)
        or not pages
        or any(not isinstance(page, list) for page in pages)
    ):
        msg = "GitHub returned invalid pull-request pages"
        raise ValueError(msg)
    pulls = [pull for page in pages for pull in page]
    if any(not isinstance(pull, dict) for pull in pulls):
        msg = "GitHub returned an invalid pull-request record"
        raise ValueError(msg)
    if os.environ.get("DEPENDABOT_HEALTH_DEBUG") == "1":
        print(
            f"Dependabot health debug: fetched {len(pages)} pages, {len(pulls)} open PRs"
        )
    return pulls


def escape_command(text: str) -> str:
    """Keep API text from injecting GitHub workflow commands."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main(argv: list[str] | None = None) -> int:
    """Return failure with links and repair guidance for every stuck PR."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--max-open-days", type=int, default=14)
    parser.add_argument("--max-rebase-banners", type=int, default=2)
    args = parser.parse_args(argv)
    if args.max_open_days < 0 or args.max_rebase_banners < 0:
        parser.error("thresholds must be non-negative")
    try:
        pulls = list_pulls(args.repo)
        stuck = find_stuck(
            pulls,
            now=dt.datetime.now(dt.timezone.utc),
            max_open_days=args.max_open_days,
            max_rebase_banners=args.max_rebase_banners,
        )
        own = sum(
            (pull.get("user") or {}).get("login") == "dependabot[bot]" for pull in pulls
        )
        lines = [f"Dependabot health: {own} open Dependabot PR(s), {len(stuck)} stuck."]
        for pull, reasons in stuck:
            # Construct the URL from validated repository data and numeric PR ID.
            number = int(pull["number"])
            url = f"https://github.com/{args.repo}/pull/{number}"
            detail = f"#{number}: {'; '.join(reasons)} ({url})"
            lines.append(f"- {detail}")
            print(
                f"::error title=Stuck Dependabot pull request::{escape_command(detail)}"
            )
        if stuck:
            lines.append(
                "Review the failing checks and fix/merge current updates, or close obsolete PRs so Dependabot can propose fresh updates."
            )
        report = "\n".join(lines) + "\n"
        print(report, end="")
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as summary:
                summary.write(report)
        return int(bool(stuck))
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        subprocess.CalledProcessError,
    ) as exc:
        detail = str(exc)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            detail += f": {exc.stderr.strip()}"
        print(f"::error title=Dependabot health scan failed::{escape_command(detail)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
