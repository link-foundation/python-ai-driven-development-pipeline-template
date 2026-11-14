"""Reproduce the Sphinx 9.2.0 builtin Napoleon deprecation without a build."""

import argparse
import sys
import warnings
from pathlib import Path

from sphinx.ext.autodoc._directive_options import _AutoDocumenterOptions
from sphinx.ext.napoleon import Config
from sphinx.ext.napoleon.docstring import GoogleDocstring

parser = argparse.ArgumentParser()
parser.add_argument("--apply-fix", action="store_true")
args = parser.parse_args()
if args.apply_fix:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "docs"))
    from sphinx_compat import fix_napoleon_options_truthiness

    fix_napoleon_options_truthiness()
with warnings.catch_warnings():
    warnings.simplefilter("error")
    result = GoogleDocstring(
        "Add numbers.\n\nArgs:\n    a: First number\n",
        Config(),
        options=_AutoDocumenterOptions(no_index=True),
    )
assert ":param a: First number" in result.lines()
assert result._no_index is True
print("Google docstrings render without deprecated mapping calls; no-index preserved")
