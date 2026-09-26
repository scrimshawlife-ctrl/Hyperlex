def test_version_not_default_placeholder():
    from hyperlex import PKG_VERSION

    assert PKG_VERSION
    assert PKG_VERSION != "0.1.0"


def test_pyproject_version_matches_VERSION():
    """Lockstep: repo VERSION and pyproject project.version must agree.

    Runtime PKG_VERSION may still prefer an installed wheel via
    importlib.metadata; that is outside this file lock.
    """
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', pyproject)
    assert match is not None
    assert match.group(1) == version


def test_router_loads_from_package_data():
    from hyperlex.command_router import load_router, router_path

    assert router_path().is_file()
    r = load_router()
    assert any(row.get("cmd") == "mutation trace" for row in r.get("research") or [])


def test_mutation_schema_packaged():
    from pathlib import Path
    from hyperlex.schemas import SCHEMAS_DIR

    assert (Path(SCHEMAS_DIR) / "mutation_trace.v0.1.schema.json").is_file()
