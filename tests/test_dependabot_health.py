"""Small offline fixtures for stale PRs, repeated rebases and API failures."""

import datetime as dt
import json
import subprocess
from unittest.mock import Mock

import pytest

from scripts import check_dependabot_health as health
from tests.workflow_helpers import (
    read_workflow,
    workflow_job_block,
    workflow_step_block,
)

NOW = dt.datetime(2026, 11, 14, tzinfo=dt.timezone.utc)


def pull(*, age=0, banners=0, login="dependabot[bot]", state="open", number=135):
    return {
        "state": state,
        "user": {"login": login},
        "number": number,
        "created_at": (NOW - dt.timedelta(days=age)).isoformat(),
        "body": health.REBASE_BANNER * banners,
    }


@pytest.mark.parametrize(
    ("age", "banners", "stuck"),
    [
        (0, 0, False),
        (14, 2, False),
        (14 + 1 / 86400, 0, True),
        (0, 3, True),
        (15, 4, True),
        (-1, 0, False),
    ],
)
def test_independent_thresholds(age, banners, stuck):
    result = health.find_stuck([pull(age=age, banners=banners)], now=NOW)
    assert bool(result) == stuck
    if age == 15:
        assert len(result[0][1]) == 2


def test_closed_and_other_authors_are_ignored():
    pulls = [
        pull(age=99, state="closed"),
        pull(age=99, login="user"),
        {**pull(age=99), "user": None},
    ]
    assert health.find_stuck(pulls, now=NOW) == []


def test_null_body_and_custom_thresholds():
    assert health.find_stuck([{**pull(), "body": None}], now=NOW) == []
    assert health.find_stuck([pull(age=4)], now=NOW, max_open_days=3)
    assert health.find_stuck([pull(banners=1)], now=NOW, max_rebase_banners=0)


@pytest.mark.parametrize("created", ["bad", "2026-01-01T00:00:00"])
def test_invalid_timestamp_fails(created):
    with pytest.raises(ValueError):
        health.find_stuck([{**pull(), "created_at": created}], now=NOW)


def test_all_api_pages_are_inspected(monkeypatch):
    pages = [[pull(number=i) for i in range(1, 101)], [pull(age=99, number=101)]]
    run = Mock(return_value=subprocess.CompletedProcess([], 0, json.dumps(pages)))
    monkeypatch.setattr(health.subprocess, "run", run)
    pulls = health.list_pulls("owner/repo")
    assert len(pulls) == 101
    assert health.find_stuck(pulls, now=NOW)[0][0]["number"] == 101
    command = run.call_args.args[0]
    assert "--paginate" in command and "--slurp" in command
    assert command[-1] == "repos/owner/repo/pulls?state=open&per_page=100"
    assert run.call_args.kwargs["check"] is True


@pytest.mark.parametrize("data", [{}, [], [None], [{"message": "denied"}], [[None]]])
def test_malformed_api_pages_fail(monkeypatch, data):
    monkeypatch.setattr(
        health.subprocess,
        "run",
        Mock(return_value=subprocess.CompletedProcess([], 0, json.dumps(data))),
    )
    with pytest.raises(ValueError):
        health.list_pulls("owner/repo")


@pytest.mark.parametrize(
    "error",
    [
        subprocess.CalledProcessError(1, ["gh"]),
        ValueError("bad JSON"),
        OSError("missing gh"),
        KeyError("created_at"),
    ],
)
def test_cli_errors_fail_visibly(monkeypatch, capsys, error):
    monkeypatch.setattr(health, "list_pulls", Mock(side_effect=error))
    assert health.main(["--repo", "owner/repo"]) == 1
    assert "::error title=Dependabot health scan failed::" in capsys.readouterr().out


@pytest.mark.parametrize("stuck", [False, True])
def test_cli_exit_summary_and_actionable_links(tmp_path, monkeypatch, capsys, stuck):
    summary = tmp_path / "summary.md"
    summary.write_text("previous summary\n")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    record = pull()
    record["created_at"] = (
        dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=15 if stuck else 0)
    ).isoformat()
    monkeypatch.setattr(health, "list_pulls", lambda _: [record])
    assert health.main([]) == int(stuck)
    output = capsys.readouterr().out
    assert f"{int(stuck)} stuck" in output
    assert summary.read_text().startswith("previous summary\nDependabot health:")
    if stuck:
        assert "https://github.com/owner/repo/pull/135" in output
        assert "fix/merge" in output and "close obsolete" in output


def test_empty_repository_is_healthy(monkeypatch):
    monkeypatch.setattr(
        health.subprocess,
        "run",
        Mock(return_value=subprocess.CompletedProcess([], 0, "[[]]")),
    )
    assert health.list_pulls("owner/repo") == []


def test_invalid_repository_does_not_call_api(monkeypatch):
    run = Mock()
    monkeypatch.setattr(health.subprocess, "run", run)
    with pytest.raises(ValueError, match="owner/repository"):
        health.list_pulls("owner/repo?injected")
    run.assert_not_called()


def test_debug_is_opt_in(monkeypatch, capsys):
    monkeypatch.setattr(
        health.subprocess,
        "run",
        Mock(return_value=subprocess.CompletedProcess([], 0, "[[]]")),
    )
    monkeypatch.delenv("DEPENDABOT_HEALTH_DEBUG", raising=False)
    health.list_pulls("owner/repo")
    assert "debug" not in capsys.readouterr().out
    monkeypatch.setenv("DEPENDABOT_HEALTH_DEBUG", "1")
    health.list_pulls("owner/repo")
    assert "fetched 1 pages" in capsys.readouterr().out


def test_workflow_commands_are_escaped():
    assert (
        health.escape_command("%\r\n::error::injected") == "%25%0D%0A::error::injected"
    )


@pytest.mark.parametrize("argument", ["--max-open-days", "--max-rebase-banners"])
def test_cli_rejects_negative_thresholds(argument):
    with pytest.raises(SystemExit) as result:
        health.main([argument, "-1"])
    assert result.value.code == 2


def test_health_workflow_is_scheduled_read_only_and_gated():
    workflow = read_workflow("dependabot-health.yml")
    assert "schedule:" in workflow and "workflow_dispatch:" in workflow
    job = workflow_job_block(workflow, "health")
    assert "pull-requests: read" in job
    assert "write" not in workflow
    scan = workflow_step_block(job, "Report stuck Dependabot pull requests")
    assert "github.event_name != 'pull_request'" in scan
    assert "GH_TOKEN: ${{ github.token }}" in scan
    assert "python3 scripts/check_dependabot_health.py" in scan
    regression = workflow_step_block(job, "Verify health policy in pull requests")
    assert "github.event_name == 'pull_request'" in regression
    assert "pytest tests/test_dependabot_health.py" in regression
    assert "needs: [health]" in workflow_job_block(workflow, "pipeline-status")
