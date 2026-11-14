"""Regressions for documentation builds with the current Sphinx release."""

import importlib.util
import warnings
from pathlib import Path

from sphinx.ext.autodoc._directive_options import _AutoDocumenterOptions
from sphinx.ext.napoleon import Config
from sphinx.ext.napoleon.docstring import GoogleDocstring


def test_napoleon_uses_attribute_options_without_mapping_deprecations(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "docs/sphinx_compat.py"
    spec = importlib.util.spec_from_file_location("sphinx_compat", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Restore the class after this test; never change another test's options.
    monkeypatch.setattr(
        _AutoDocumenterOptions, "__bool__", lambda self: True, raising=False
    )
    monkeypatch.delattr(_AutoDocumenterOptions, "__bool__")
    module.fix_napoleon_options_truthiness()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = GoogleDocstring(
            "Add numbers.\n\nArgs:\n    a: First number\n",
            Config(),
            options=_AutoDocumenterOptions(no_index=True),
        )
    assert ":param a: First number" in result.lines()
    assert result._no_index is True
