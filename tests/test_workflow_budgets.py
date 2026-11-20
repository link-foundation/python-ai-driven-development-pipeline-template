"""Regression fixtures for the execution-budget policy."""

import pytest

from tests.workflow_budgets import step_budgets


@pytest.mark.parametrize(
    "command",
    [
        "npm ci",
        "npm install example",
        "npx --yes example",
        "pipx install example",
        "pipx run example",
        "bash scripts/install-python-dependencies.sh",
        "bash scripts/install-lychee.sh",
        "python -m pip install example",
        "uv pip install example",
        "uv sync",
        "curl https://example.invalid/",
        "wget https://example.invalid/",
        "echo ready # comment\nnpm ci",
        "echo ready; npm ci",
        'bash scripts/run-with-budget-warning.sh 90 "one" true && npm ci',
        'bash -c "npm ci"',
        'bash -euo pipefail -c "npm ci"',
    ],
)
def test_network_command_needs_its_own_wrapper(command: str) -> None:
    with pytest.raises(AssertionError, match="network command needs"):
        list(step_budgets([{"run": command}], {}, "test"))


def test_literals_env_precedence_and_offline_installs() -> None:
    steps = [
        {"run": 'bash scripts/run-with-budget-warning.sh 99999 "literal" true'},
        {"run": 'bash "$ROOT/scripts/run-with-budget-warning.sh" "$LIMIT" "job" true'},
        {
            "run": 'bash "$ROOT/scripts/run-with-budget-warning.sh" "${LIMIT}" "step" \\\n'
            '  bash -euo pipefail -c "npm ci"',
            "env": {"LIMIT": 123},
        },
        {"run": 'bash scripts/run-with-budget-warning.sh "$WORKFLOW" "workflow" true'},
        {
            "run": 'pip install --no-index example\nnpm ci --offline # accepted\necho "npm ci"'
        },
    ]
    env = {"WORKFLOW": "11", "LIMIT": 6} | {"LIMIT": 42}
    assert list(step_budgets(steps, env, "test")) == [
        ("literal", 99999),
        ("job", 42),
        ("step", 123),
        ("workflow", 11),
    ]


@pytest.mark.parametrize("value", ["$MISSING", "${LIMIT}", "2.5", "0"])
def test_unresolved_or_invalid_budget_is_an_error(value: str) -> None:
    steps = [{"run": f'bash scripts/run-with-budget-warning.sh "{value}" "bad" true'}]
    with pytest.raises(AssertionError, match="positive integer"):
        list(step_budgets(steps, {"LIMIT": "invalid"}, "test"))


def test_composite_budgets_are_charged_per_invocation(tmp_path) -> None:
    outer = tmp_path / "outer"
    outer.mkdir()
    (outer / "action.yml").write_text(
        """runs:
  using: composite
  steps:
    - uses: $/inner
"""
    )
    inner = tmp_path / "inner"
    inner.mkdir()
    (inner / "action.yaml").write_text(
        """runs:
  using: composite
  steps:
    - run: bash "${{ github.action_path }}/run-with-budget-warning.sh" "$LIMIT" "inner" npm ci
      shell: bash
"""
    )
    steps = [{"uses": "./outer"}, {"uses": "$/outer", "env": {"LIMIT": 20}}]
    assert list(step_budgets(steps, {"LIMIT": 10}, "test", root=tmp_path)) == [
        ("inner", 10),
        ("inner", 20),
    ]
    (inner / "action.yaml").write_text(
        "runs: {using: composite, steps: [{run: npm ci}]}"
    )
    with pytest.raises(AssertionError, match="outer.*inner.*network command needs"):
        list(step_budgets(steps, {"LIMIT": 10}, "test", root=tmp_path))
