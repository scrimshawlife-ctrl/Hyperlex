def test_version_not_default_placeholder():
    from hyperlex import PKG_VERSION

    assert PKG_VERSION
    assert PKG_VERSION != "0.1.0"


def test_router_loads_from_package_data():
    from hyperlex.command_router import load_router, router_path

    assert router_path().is_file()
    r = load_router()
    assert any(row.get("cmd") == "mutation trace" for row in r.get("research") or [])


def test_mutation_schema_packaged():
    from pathlib import Path
    from hyperlex.schemas import SCHEMAS_DIR

    assert (Path(SCHEMAS_DIR) / "mutation_trace.v0.1.schema.json").is_file()
