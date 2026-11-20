"""Read execution budgets and check networked installs in Actions YAML."""

from __future__ import annotations

import re
import shlex
from collections.abc import Iterator
from io import StringIO
from pathlib import Path

import yaml

from tests.workflow_helpers import ROOT

WRAPPER = "run-with-budget-warning.sh"
SEPARATORS = "\n;&|()"
INSTALL_SUBCOMMANDS = {
    "npm": {"ci", "install", "i", "add"},
    "pip": {"install"},
    "pip3": {"install"},
    "pipx": {"install", "run"},
    "uv": {"sync", "pip"},
}
INSTALL_SCRIPTS = {"install-python-dependencies.sh", "install-lychee.sh"}


def read_yaml(path: Path) -> dict:
    """Load a workflow or local action manifest."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class ShellInput(StringIO):
    """Keep command boundaries when shlex consumes a shell comment."""

    def readline(self, size: int = -1) -> str:
        line = super().readline(size)
        if line.endswith("\n"):
            self.seek(self.tell() - 1)
        return line


def shell_commands(script: str) -> Iterator[list[str]]:
    """Yield shell commands with continuations and comments removed."""
    lexer = shlex.shlex(
        ShellInput(script.replace("\\\n", "")), posix=True, punctuation_chars=SEPARATORS
    )
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    command: list[str] = []
    for token in lexer:
        if token and all(char in SEPARATORS for char in token):
            if command:
                yield command
                command = []
        else:
            command.append(token)
    if command:
        yield command


def is_network_install(command: list[str]) -> bool:
    """Identify network commands and package installs that need a wrapper."""
    executable, *args = command
    if executable in ({"curl", "wget"} | INSTALL_SCRIPTS):
        return True
    if executable in {"npm", "npx", "uv"} and "--offline" in args:
        return False
    if executable in {"pip", "pip3", "uv"} and "--no-index" in args:
        return False
    if executable == "npx":
        return bool({"--yes", "-y"}.intersection(args[:2]))
    if executable == "uv" and args[:1] == ["pip"]:
        return args[1:2] == ["install"]
    return bool(args and args[0] in INSTALL_SUBCOMMANDS.get(executable, ()))


def budget_seconds(value: str, env: dict, context: str) -> int:
    """Resolve a literal or a shell variable through the effective env."""
    variable = re.fullmatch(r"\$(?:\{([A-Za-z_]\w*)\}|([A-Za-z_]\w*))", value)
    if variable:
        value = str(env.get(variable[1] or variable[2], ""))
    assert re.fullmatch(r"[0-9]+", value) and int(value) > 0, (
        f"{context}: budget must resolve to a positive integer, got {value!r}"
    )
    return int(value)


def command_budgets(
    command: list[str],
    env: dict,
    context: str,
    *,
    wrapped: bool = False,
    check_deadlines: bool = True,
) -> Iterator[tuple[str, int]]:
    """Check an individual command and descend into literal shell scripts."""
    while command and (
        command[0]
        in {"if", "then", "elif", "else", "do", "!", "sudo", "env", "command"}
        or re.match(r"^[A-Za-z_]\w*=", command[0])
    ):
        command = command[1:]
    if not command:
        return

    executable = Path(command[0]).name
    args = command[1:]
    if executable in {"bash", "sh"}:
        shell_args = iter(args)
        for arg in shell_args:
            if arg == "--":
                arg = next(shell_args, "")
            elif arg.startswith("-"):
                flags = arg[1:] if not arg.startswith("--") else ""
                if "c" in flags:
                    for child in shell_commands(next(shell_args, "")):
                        yield from command_budgets(
                            child,
                            env,
                            context,
                            wrapped=wrapped,
                            check_deadlines=check_deadlines,
                        )
                    return
                if flags.endswith(("o", "O")):
                    next(shell_args, None)
                continue
            candidate = Path(arg).name
            if candidate in (INSTALL_SCRIPTS | {WRAPPER}):
                executable, args = candidate, list(shell_args)
            break

    if executable == WRAPPER:
        assert len(args) >= 3, f"{context}: incomplete {WRAPPER} invocation"
        if check_deadlines:
            yield args[1], budget_seconds(args[0], env, context)
        yield from command_budgets(
            args[2:], env, context, wrapped=True, check_deadlines=check_deadlines
        )
        return

    if executable in {"python", "python3"} and args[:1] == ["-m"] and len(args) > 1:
        executable, *args = args[1:]
    assert wrapped or not is_network_install([executable, *args]), (
        f"{context}: network command needs {WRAPPER}: {shlex.join([executable, *args])}"
    )


def composite_steps(path: Path) -> list[dict]:
    """Read a local action's shell steps if it is composite."""
    if path.is_dir():
        manifest = next(
            (
                path / name
                for name in ("action.yml", "action.yaml")
                if (path / name).is_file()
            ),
            None,
        )
        if manifest is None:
            return []
        path = manifest
    runs = read_yaml(path)["runs"]
    return runs["steps"] if runs["using"] == "composite" else []


def step_budgets(
    steps: list[dict],
    env: dict,
    context: str,
    *,
    root: Path = ROOT,
    actions: tuple[Path, ...] = (),
    check_deadlines: bool = True,
) -> Iterator[tuple[str, int]]:
    """Count step and nested composite budgets against the calling job."""
    for step in steps:
        name = step.get("name", step.get("id", step.get("uses", "run")))
        scope = f"{context} / {name}"
        step_env = env | step.get("env", {})
        deadlines = [
            deadline
            for command in shell_commands(step.get("run", ""))
            for deadline in command_budgets(
                command, step_env, scope, check_deadlines=check_deadlines
            )
        ]
        uses = step.get("uses", "")
        if uses.startswith(("./", "$/")):
            action = (root / uses[2:]).resolve()
            assert action not in actions, f"{scope}: recursive composite action"
            deadlines.extend(
                step_budgets(
                    composite_steps(action),
                    step_env,
                    scope,
                    root=root,
                    actions=(*actions, action),
                    check_deadlines=check_deadlines,
                )
            )
        if check_deadlines and "timeout-minutes" in step:
            timeout = budget_seconds(str(step["timeout-minutes"]), step_env, scope) * 60
            # A runner timeout and wrappers in the same step share one clock.
            # A larger declared wrapper must still count against the job.
            if timeout > sum(seconds for _, seconds in deadlines):
                deadlines = [(f"{name} timeout-minutes", timeout)]
        yield from deadlines
