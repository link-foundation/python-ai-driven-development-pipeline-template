The current PyPI metadata for `scriv==1.8.1` declares exact runtime pins, including `click==8.5.0` and `markdown-it-py==4.2.0`. PyPI now serves Click 8.5.1 and markdown-it-py 4.3.0. This prevents a consuming project's universal lock from taking even the newer Click patch release.

Minimal reproduction (resolution only; installs nothing):

```sh
python -m pip install --dry-run scriv==1.8.1 click==8.5.1
python -m pip install --dry-run scriv==1.8.1 markdown-it-py==4.3.0
```

Both constraints conflict with Scriv's exact requirements. The same limits remain after `uv lock --upgrade`. The metadata is available at https://pypi.org/pypi/scriv/1.8.1/json .

Could the published library requirements use tested compatible ranges for its direct dependencies, keeping exact application/development resolutions in Scriv's own lock? For example, after validating the current APIs, `click>=8.5,<9` and `markdown-it-py>=4.2,<5` would permit these releases without consumers overriding Scriv's declared contract. The exact complete transitive list in `Requires-Dist` also merits checking against the project's intended direct runtime dependencies.

Our workaround preserves the published constraints and explicitly records both older versions as upstream-constrained in the dependency inventory; it does not bypass the resolver or hide conflicts. We are updating the full dependency tree in https://github.com/link-foundation/python-ai-driven-development-pipeline-template/pull/152 and will refresh the universal lock when compatible metadata is released.
