"""Compatibility follows upstream data, rather than a hard-coded action tag."""

import base64
import json
import subprocess
from unittest.mock import Mock

import pytest

from scripts import check_zizmor_compatibility as check


def workflow(ref="v0.6.4", version="1.30.1"):
    return f"env:\n  ZIZMOR_VERSION: '{version}'\njobs:\n  zizmor:\n    steps:\n      - uses: zizmorcore/zizmor-action@{ref}\n"


@pytest.mark.parametrize("ref", ["v0.6.4", "v0.8.1", "v99.0.0", "a" * 40])
@pytest.mark.parametrize("layout", ["digest", "lock"])
def test_compatibility_uses_selected_action_table(monkeypatch, ref, layout):
    path = (
        "support/versions" if layout == "digest" else "support/locks/zizmor-1.30.1.txt"
    )
    tree = {"truncated": False, "tree": [{"path": path, "type": "blob"}]}
    table = {
        "content": base64.b64encode(f"1.30.1 sha256:{'a' * 64}\n".encode()).decode()
    }
    run = Mock(
        side_effect=[
            subprocess.CompletedProcess([], 0, json.dumps(data))
            for data in (tree, table)
        ]
    )
    monkeypatch.setattr(check.subprocess, "run", run)
    assert check.check_compatibility(workflow(ref)) == (ref, "1.30.1")
    assert f"/git/trees/{ref}?recursive=1" in run.call_args_list[0].args[0][-1]
    if layout == "digest":
        assert run.call_args_list[1].args[0][-1].endswith(f"?ref={ref}")
    else:
        assert run.call_count == 1


@pytest.mark.parametrize(
    "paths", [[], ["support/locks/zizmor-1.30.10.txt"], ["support/versions"]]
)
def test_unsupported_combination_has_clear_diagnostic(monkeypatch, paths):
    table = {
        "content": base64.b64encode(f"1.30.10 sha256:{'a' * 64}\n".encode()).decode()
    }
    lookup = Mock(
        side_effect=[
            {"truncated": False, "tree": [{"path": p, "type": "blob"} for p in paths]},
            table,
        ]
    )
    monkeypatch.setattr(check, "gh_json", lookup)
    with pytest.raises(
        ValueError, match=r"zizmor-action@v0.6.4 does not support ZIZMOR_VERSION=1.30.1"
    ):
        check.check_compatibility(workflow())


def test_incomplete_tree_fails(monkeypatch):
    monkeypatch.setattr(check, "gh_json", lambda _: {"truncated": True})
    with pytest.raises(ValueError, match="incomplete"):
        check.check_compatibility(workflow())


@pytest.mark.parametrize(
    "text", ["", workflow(version="latest"), workflow() + workflow()]
)
def test_ambiguous_or_floating_pins_fail(text):
    with pytest.raises(ValueError, match="Expected one"):
        check.read_pins(text)


@pytest.mark.parametrize(
    "error",
    [
        subprocess.CalledProcessError(1, ["gh"]),
        ValueError("invalid response"),
        KeyError("tree"),
    ],
)
def test_cli_lookup_errors_fail(tmp_path, monkeypatch, capsys, error):
    source = tmp_path / "workflow.yml"
    source.write_text(workflow())
    monkeypatch.setattr(check, "check_compatibility", Mock(side_effect=error))
    assert check.main(["--workflow", str(source)]) == 1
    assert "compatibility check failed" in capsys.readouterr().err


def test_cli_success(tmp_path, monkeypatch, capsys):
    source = tmp_path / "workflow.yml"
    source.write_text(workflow())
    monkeypatch.setattr(check, "check_compatibility", lambda _: ("v0.8.1", "1.30.1"))
    assert check.main(["--workflow", str(source)]) == 0
    assert "supports ZIZMOR_VERSION=1.30.1" in capsys.readouterr().out
