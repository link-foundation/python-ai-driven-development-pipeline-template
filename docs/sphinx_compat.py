"""Temporary compatibility for a Sphinx 9.2.0 Napoleon regression."""


def fix_napoleon_options_truthiness() -> None:
    """Keep Napoleon's attribute access from invoking the deprecated mapping API.

    Sphinx 9.2.0's options always have public attributes, so their old length
    check is always true. Napoleon still performs that check before reading
    no_index/noindex. Give those options ordinary object truthiness until the
    bundled extension uses ``options is not None`` upstream. No warning filter
    or legacy autodoc implementation is enabled.
    """
    import sphinx

    if sphinx.__version__ == "9.2.0":
        from sphinx.ext.autodoc._directive_options import _AutoDocumenterOptions

        if "__bool__" not in _AutoDocumenterOptions.__dict__:
            _AutoDocumenterOptions.__bool__ = lambda self: True
