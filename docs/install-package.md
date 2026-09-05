# Install Hyperlex as a Python package

Skill install (`bash install.sh` → `~/.hermes/skills/hyperlex`) stays the Hermes path.
This is the importable / console-script path.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
hyperlex version
hyperlex mutation trace "it's giving mid rizz"
hyperlex commands
```

From a clone without editable mode:

```bash
pip install .
```

Optional extras: `runtime` (requests, crawl4ai, chromadb), `schema` (jsonschema), `docs` (mkdocs).

Console scripts after install: `hyperlex`, `hlx` (same entry).

Hermes skill CLI is unchanged. Do not replace `install.sh` with pip-only until the operator wants skill discovery driven by site-packages.
