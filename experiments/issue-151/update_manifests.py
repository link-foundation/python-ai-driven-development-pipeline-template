import json
import re
from pathlib import Path

root = Path.cwd()
data = json.loads(
    (root / "dev/log/issues/151/pulls/152/registry-initial.json").read_text()
)
p = root / "pyproject.toml"
s = p.read_text()
s = (
    s.replace('requires = ["hatchling"]', 'requires = ["hatchling==1.33.0"]')
    .replace('license = {text = "Unlicense"}', 'license = "Unlicense"')
    .replace('requires-python = ">=3.9"', 'requires-python = ">=3.15"')
)
s = re.sub(r'    "License :: OSI Approved :: The Unlicense \(Unlicense\)",\n', "", s)
s = re.sub(
    r'    "Programming Language :: Python :: 3\.(?:9|10|11|12|13)",\n', "", s
).replace(
    '    "Programming Language :: Python :: 3",',
    '    "Programming Language :: Python :: 3",\n    "Programming Language :: Python :: 3.15",',
)
for n in [
    "ruff",
    "mypy",
    "pytest",
    "pytest-asyncio",
    "pytest-cov",
    "pre-commit",
    "scriv",
    "sphinx",
    "furo",
    "myst-parser",
]:
    s = re.sub(
        r'"' + re.escape(n) + r'(?:\[toml\])?>=[^"\n]+"',
        f'"{n}>={data["pypi"][n]["version"]}"',
        s,
    )
s = s.replace(
    '"scriv>=1.8.1",', '"scriv>=1.8.1",\n    "packaging>=26.3",\n    "pyyaml>=6.0.3",'
)
s = (
    s.replace(
        "\n[project.urls]",
        "\n# CI and release tooling also participates in the universal lock and audit.\n[project.optional-dependencies.tools]\n",
    )
    if False
    else s
)
s = s.replace(
    "\n[project.urls]",
    "\ntools = [\n"
    + "".join(
        f'    "{n}>={data["pypi"][n]["version"]}",\n'
        for n in [
            "hatchling",
            "build",
            "twine",
            "uv",
            "pip",
            "pip-audit",
            "shellcheck-py",
            "zizmor",
        ]
    )
    + "]\n\n[project.urls]",
)
s = (
    s.replace('target-version = "py39"', 'target-version = "py315"')
    .replace('python_version = "3.9"', 'python_version = "3.15"')
    .replace('minversion = "7.0"', 'minversion = "9.2"')
    .replace(
        'addopts = "-ra -q --strict-markers"',
        'addopts = "-ra -q"\nstrict = true\nasyncio_default_fixture_loop_scope = "fixture-scope"',
    )
)
p.write_text(s)
p = root / "docs/requirements.txt"
p.write_text(
    "# Keep these floors aligned with the docs extra in pyproject.toml.\n"
    + "".join(
        f"{n}>={data['pypi'][n]['version']}\n"
        for n in ["sphinx", "furo", "myst-parser"]
    )
)
p = root / ".pre-commit-config.yaml"
s = (
    p.read_text()
    .replace("v5.0.0", "v6.0.0")
    .replace("v0.8.4", "v0.17.5")
    .replace("v1.13.0", "v2.4.1")
    .replace("id: ruff\n", "id: ruff-check\n")
    .replace(
        "additional_dependencies: [pytest, pytest-asyncio]",
        "additional_dependencies: [pytest==9.2.0, pytest-asyncio==1.5.0]",
    )
)
p.write_text(s)
for p in (root / ".github/workflows").glob("*.yml"):
    s = (
        p.read_text()
        .replace("python-version: '3.13'", "python-version: '3.15.2'")
        .replace('python-version: "3.13"', 'python-version: "3.15.2"')
        .replace("Test (Python 3.13)", "Test (Python 3.15)")
        .replace("node-version: '24'", "node-version: '26.13.1'")
        .replace("secretlint@13.0.7", "secretlint@13.1.0")
        .replace(
            "secretlint-rule-preset-recommend@13.0.7",
            "secretlint-rule-preset-recommend@13.1.0",
        )
        .replace("ZIZMOR_VERSION: '1.30.1'", "ZIZMOR_VERSION: '1.32.0'")
    )
    for repo, info in data["github"].items():
        if repo in ["codecov/codecov-action", "pypa/gh-action-pypi-publish"]:
            continue
        tag = "v4.39.3" if repo == "github/codeql-action" else info["tag_name"]
        s = re.sub(
            r"(uses: " + re.escape(repo) + r"(?:/[\w-]+)?@)v[\d.]+",
            lambda m: m[1] + tag,
            s,
        )
    s = s.replace(
        '              python -m pip install --upgrade pip\n              pip install -e ".[dev]"',
        "              bash scripts/install-python-dependencies.sh",
    )
    s = s.replace(
        '          python -m pip install --upgrade pip\n          pip install build twine "scriv[toml]" uv',
        "          bash scripts/install-python-dependencies.sh",
    )
    s = s.replace(
        "          python -m pip install --upgrade pip\n          pip install build twine",
        '          cd "$PYTHON_ROOT"\n          bash scripts/install-python-dependencies.sh',
    )
    s = s.replace(
        "          python -m pip install --upgrade pip\n          pip install -e .\n          pip install -r docs/requirements.txt",
        "          bash scripts/install-python-dependencies.sh",
    )
    s = s.replace("python -m build\n", "python -m build --no-isolation\n")
    if p.name == "security.yml":
        s = s.replace(
            "        run: python scripts/audit_dependencies.py",
            "        run: |\n          bash scripts/install-python-dependencies.sh\n          python scripts/audit_dependencies.py",
        )
    p.write_text(s)
p = root / "README.md"
s = (
    p.read_text()
    .replace("python-3.9%2B", "python-3.15%2B")
    .replace(
        "**Multi-version Python support**: Works with Python 3.9-3.13",
        "**Current Python support**: Works with Python 3.15+",
    )
    .replace("Python 3.13", "Python 3.15")
)
p.write_text(s)
p = root / "scripts/smoke_test_published_package.py"
s = p.read_text()
s = re.sub(
    r"try:\n    import tomllib\nexcept ModuleNotFoundError:.*?tomllib = None  # type: ignore\[assignment\]\n",
    "import tomllib\n",
    s,
    flags=re.DOTALL,
)
s = re.sub(r"    if tomllib is None:\n.*?\n(?=    [^ ])", "", s, flags=re.DOTALL)
p.write_text(s)
p = root / "tests/test_project_metadata.py"
s = (
    p.read_text()
    .replace(
        "The dev extra must not install mypy versions that reject Python 3.9.",
        "The dev extra must use the current mypy major without a stale ceiling.",
    )
    .replace('assert "1.13.0" in mypy.specifier', 'assert "2.4.1" in mypy.specifier')
    .replace(
        'assert "2.0" not in mypy.specifier',
        'assert "2.4.0" not in mypy.specifier\n    assert "3.0" in mypy.specifier',
    )
)
p.write_text(s)
