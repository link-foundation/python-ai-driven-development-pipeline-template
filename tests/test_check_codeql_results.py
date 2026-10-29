"""Exercise the SARIF gate through its real command-line exit status."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_codeql_results.py"


def report(results=None, **run_fields):
    return {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "CodeQL"}},
                "results": results or [],
                **run_fields,
            }
        ],
    }


def gate(path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


def test_accepts_multiple_clean_reports_and_runs(tmp_path):
    payload = report(invocations=[{"executionSuccessful": True}])
    payload["runs"].append(report()["runs"][0])
    (tmp_path / "python.sarif").write_text(json.dumps(payload))
    (tmp_path / "actions.sarif").write_text(json.dumps(report()))
    assert gate(tmp_path).returncode == 0


@pytest.mark.parametrize("level", ["error", "warning", "note", "none", None])
def test_rejects_every_finding_level_in_later_files_and_runs(tmp_path, level):
    finding = {"ruleId": "example/rule", "message": {"text": "finding"}}
    if level is not None:
        finding["level"] = level
    payload = report()
    payload["runs"].append(report([finding])["runs"][0])
    (tmp_path / "a-clean.sarif").write_text(json.dumps(report()))
    (tmp_path / "z-findings.sarif").write_text(json.dumps(payload))
    result = gate(tmp_path)
    assert result.returncode != 0
    assert "example/rule" in result.stdout


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        [],
        {},
        {"version": "2.1.0", "runs": []},
        {"version": "2.1.0", "runs": [None]},
        report(invocations=[{"executionSuccessful": False}]),
        report(invocations=[{}]),
        report(results="bad"),
        report(tool={}),
    ],
)
def test_rejects_invalid_or_unsuccessful_reports(tmp_path, payload):
    (tmp_path / "invalid.sarif").write_text(
        payload if isinstance(payload, str) else json.dumps(payload)
    )
    assert gate(tmp_path).returncode != 0


def test_rejects_missing_reports(tmp_path):
    assert gate(tmp_path).returncode != 0
    assert gate(tmp_path / "missing").returncode != 0
