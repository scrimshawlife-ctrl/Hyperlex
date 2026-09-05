def test_load_router_has_mutation_noun():
    from hyperlex.command_router import load_router

    r = load_router()
    cmds = [row.get("cmd") for row in (r.get("research") or [])]
    assert "mutation trace" in cmds
    assert r.get("invoke", {}).get("mutation") == "scripts/hlx-mutation"
    traces = [row for row in r["research"] if row.get("cmd") == "mutation trace"]
    assert traces and traces[0]["forecast_eligible"] is False
