With the current PyPI Sphinx 9.2.0, Python 3.15.2, and the default new autodoc implementation, the bundled Napoleon extension raises `RemovedInSphinx11Warning` while processing ordinary Google docstrings. No third-party extension is needed.

Minimal reproduction after installing `sphinx==9.2.0`:

```python
import warnings
from sphinx.ext.autodoc._directive_options import _AutoDocumenterOptions
from sphinx.ext.napoleon import Config
from sphinx.ext.napoleon.docstring import GoogleDocstring

with warnings.catch_warnings():
    warnings.simplefilter("error")
    GoogleDocstring(
        "Add numbers.\n\nArgs:\n    a: First number\n",
        Config(),
        options=_AutoDocumenterOptions(no_index=True),
    )
```

`GoogleDocstring.__init__` executes `if options:` at `sphinx/ext/napoleon/docstring.py:362`. This invokes `_AutoDocumenterOptions.__len__`, which warns that the mapping interface is deprecated. A real `python -W error -m sphinx -W -b html docs build` fails at `autodoc-process-docstring` for the same reason.

Suggested fix: use `if options is not None:` before the existing attribute access (`options.no_index or options.noindex`). Cover default/empty options and `no_index=True` with warnings treated as errors. The new options object has public attributes even when no directive flags are set, so truthiness through its deprecated length API does not add useful validation.

Our temporary, exactly-9.2.0 workaround gives `_AutoDocumenterOptions` ordinary truthiness through `__bool__` if it has no such implementation. This avoids copying the parser or switching to legacy autodoc; no warning filters are applied. We retain an automated Google parameter/no-index regression and before/after minimal scripts in https://github.com/link-foundation/python-ai-driven-development-pipeline-template/pull/152 and can remove the workaround when the bundled caller is updated.
