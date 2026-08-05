"""Package CLI entry for PyPI / `python -m hyperlex`.

Full Hermes skill CLI remains at scripts/hyperlex.py (skill tree).
This entrypoint covers the public operator surface with the installed package.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional


def _emit(obj: Dict[str, Any]) -> None:
    print(json.dumps(obj, sort_keys=True, indent=2))


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be object")
    return data


def cmd_version(_: argparse.Namespace) -> int:
    from hyperlex import PKG_VERSION

    _emit({"ok": True, "version": PKG_VERSION, "package": "hyperlex"})
    return 0


def cmd_check(_: argparse.Namespace) -> int:
    from hyperlex import PKG_VERSION, detect_memetic_patterns, list_runes

    checks = []
    try:
        r = detect_memetic_patterns("check", ingest_source="mock")
        checks.append({"name": "analyze_mock", "ok": r.get("provenance", {}).get("brier") is None})
    except Exception as exc:
        checks.append({"name": "analyze_mock", "ok": False, "error": str(exc)})
    try:
        checks.append({"name": "runes", "ok": len(list_runes()) >= 4})
    except Exception as exc:
        checks.append({"name": "runes", "ok": False, "error": str(exc)})
    ok = all(c.get("ok") for c in checks)
    _emit({"ok": ok, "version": PKG_VERSION, "checks": checks})
    return 0 if ok else 2


def cmd_analyze(args: argparse.Namespace) -> int:
    from hyperlex import detect_memetic_patterns, extract_forecasts, emit_receipt, relay_from_result
    from hyperlex.intake.sources import pick_source

    query = (getattr(args, "query_pos", None) or args.query or "").strip() or "slang emergence"
    source, resolved = pick_source(args.source, route=getattr(args, "route", None) or None)
    result = detect_memetic_patterns(
        query=query,
        ingest_source=source,
        use_structured_ingest=True,
        validate=bool(args.validate),
        ingest_route=resolved.get("route"),
    )
    out: Dict[str, Any] = {
        "ok": True,
        "command": getattr(args, "command_label", None) or "analyze",
        "query": query,
        "source": source,
        "route": resolved.get("route"),
        "result": result,
    }
    if args.receipt:
        path = emit_receipt(result, out_dir=args.receipt_dir or None)
        out["receipt"] = str(path)
        result = json.loads(Path(path).read_text(encoding="utf-8"))
        out["result"] = result
    if args.forecasts:
        out["forecasts"] = extract_forecasts(result)
    if getattr(args, "relay", False):
        out["envelopes"] = relay_from_result(result)
    if args.out:
        Path(args.out).write_text(json.dumps(out["result"], indent=2, sort_keys=True), encoding="utf-8")
    _emit(out)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    args.command_label = "run"
    args.receipt = not bool(getattr(args, "no_receipt", False))
    args.forecasts = not bool(getattr(args, "no_forecasts", False))
    args.relay = False
    return cmd_analyze(args)


def cmd_sources(args: argparse.Namespace) -> int:
    from hyperlex.intake.sources import list_sources, resolve_source

    catalog = list_sources()
    out: Dict[str, Any] = {"ok": True, "command": "sources", **catalog}
    if getattr(args, "route", None) or getattr(args, "source", None):
        out["resolve"] = resolve_source(
            getattr(args, "source", None) or None,
            route=getattr(args, "route", None) or None,
        )
    _emit(out)
    return 0


def cmd_commands(_: argparse.Namespace) -> int:
    from hyperlex import PKG_VERSION

    _emit({
        "ok": True,
        "command": "commands",
        "version": PKG_VERSION,
        "daily": [
            'run "<query>" --route offline',
            "pending → settle → score-series",
            "scan --route offline --receipt --forecasts --append-log",
        ],
        "routes": ["offline", "mock", "default", "live", "glossary", "social"],
        "docs": "docs/operator-loop.md · docs/commands.md",
    })
    return 0


def cmd_relay(args: argparse.Namespace) -> int:
    from hyperlex import list_runes, relay_from_result, extract_forecasts, relay_forecasts

    if args.list_runes:
        _emit({"ok": True, "runes": list_runes()})
        return 0
    result = _load_json(args.input)
    if "analysis" not in result and isinstance(result.get("result"), dict):
        result = result["result"]
    envs = relay_from_result(result)
    if args.forecasts:
        envs.append(relay_forecasts(extract_forecasts(result)))
    _emit({"ok": True, "n_envelopes": len(envs), "envelopes": envs})
    return 0


def cmd_settle(args: argparse.Namespace) -> int:
    from hyperlex import settle_and_log, default_log_path
    from hyperlex.calibration.score_log import index_forecasts, read_log

    log = Path(args.log) if args.log else default_log_path()
    forecast = None
    if args.forecast_file:
        data = _load_json(args.forecast_file)
        if "forecast_id" in data:
            forecast = data
        elif isinstance(data.get("forecasts"), list):
            for fc in data["forecasts"]:
                if not args.forecast_id or fc.get("forecast_id") == args.forecast_id:
                    forecast = fc
                    break
    if forecast is None and args.forecast_id:
        forecast = index_forecasts(read_log(log)).get(args.forecast_id)
    if forecast is None:
        _emit({"ok": False, "error": "forecast not found"})
        return 2
    decision = args.decision.upper()
    outcome = float(args.outcome) if args.outcome is not None else (1.0 if decision == "TRUE" else 0.0)
    out = settle_and_log(
        forecast,
        outcome_value=outcome,
        settlement_decision=decision,
        path=log,
    )
    _emit({"ok": True, "command": "settle", "score": out["score"], "settlement": out["settlement"]})
    return 0


def cmd_score_series(args: argparse.Namespace) -> int:
    from hyperlex import recompute_series, default_log_path

    log = Path(args.log) if args.log else default_log_path()
    series = recompute_series(path=log, signal_key=args.signal_key or None)
    _emit({"ok": True, "command": "score-series", "series": series})
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    from hyperlex import detect_memetic_patterns, extract_forecasts, emit_receipt

    queries = [q.strip() for q in (args.queries or "").split(",") if q.strip()]
    if args.query:
        queries.insert(0, args.query)
    if not queries:
        queries = ["sharp money", "rizz", "locked in", "agentic slop"]
    rows = []
    for q in queries:
        result = detect_memetic_patterns(query=q, ingest_source=args.source)
        receipt = None
        if args.receipt:
            receipt = str(emit_receipt(result))
        fcs = extract_forecasts(result) if args.forecasts else []
        rows.append({
            "query": q,
            "receipt": receipt,
            "n_forecasts": len(fcs),
            "brier": result.get("provenance", {}).get("brier"),
            "source_fingerprint": (result.get("provenance") or {}).get("source_fingerprint", {}).get("fingerprint_id"),
        })
    _emit({"ok": True, "command": "scan", "rune": "LIVE_EMERGENCE_SCAN", "results": rows})
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from hyperlex.simulation import (
        build_family_phylogeny,
        forecast_hyperstition_risk,
        run_multi_agent_memetics,
        run_phase5_scenario,
        simulate_cultural_transmission,
    )
    from hyperlex import detect_memetic_patterns

    term = (args.term or args.query or "slang signal").strip()
    mode = (args.mode or "scenario").lower()
    analysis = None
    family = args.family or None
    if args.from_analyze:
        analysis = detect_memetic_patterns(query=term, ingest_source=args.source or "mock")
        lin = (analysis.get("analysis") or {}).get("lineage") or {}
        family = family or lin.get("family_id")

    if mode == "transmission":
        out = simulate_cultural_transmission(
            term, n_communities=int(args.communities), steps=int(args.steps),
            lineage_family=family, virality_hybrid=float(args.virality),
        )
    elif mode == "agents":
        out = run_multi_agent_memetics(
            term, n_agents=int(args.agents), steps=int(args.steps),
            lineage_family=family, memetic_score=float(args.memetic),
        )
    elif mode == "risk":
        out = forecast_hyperstition_risk(
            hyperstition_stage=args.stage or None,
            virality_hybrid=float(args.virality),
            memetic_score=float(args.memetic),
            domain=args.domain or "general",
            seed_term=term,
            lineage_family=family,
        )
    elif mode == "phylogeny":
        out = build_family_phylogeny(family or "brainrot-aura")
    else:
        out = run_phase5_scenario(
            term,
            lineage_family=family,
            virality_hybrid=float(args.virality),
            memetic_score=float(args.memetic),
            hyperstition_stage=args.stage or None,
            domain=args.domain or "general",
            analysis_result=analysis,
            n_communities=int(args.communities),
            transmission_steps=int(args.steps),
            n_agents=int(args.agents),
        )
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    _emit({"ok": True, "command": "simulate", "mode": mode, "scenario": out, "written": args.out or None})
    return 0


def cmd_lineage_backfill(args: argparse.Namespace) -> int:
    from hyperlex.analysis.backfill import apply_backfill, inventory_backfill

    root = Path(args.root) if args.root else None
    year = int(args.year)
    through = args.through or None
    if args.list:
        inv = inventory_backfill(year, root=root, through=through)
        if not args.verbose:
            inv = {k: v for k, v in inv.items() if k != "terms"}
        _emit({"ok": True, "command": "lineage-backfill", "mode": "inventory", **inv})
        return 0
    report = apply_backfill(year, through=through, root=root)
    if not args.verbose:
        report = {k: v for k, v in report.items() if k != "merged_registry"}
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        report["written"] = args.out
    _emit({"ok": True, "command": "lineage-backfill", "mode": "apply", **report})
    return 0


def cmd_lineage_backprop(args: argparse.Namespace) -> int:
    from hyperlex.analysis.backprop import backpropagate_lineage

    report = backpropagate_lineage(
        year=int(args.year),
        through=args.through or None,
        backfill_root=Path(args.root) if args.root else None,
        from_golden=bool(args.from_golden),
        from_archive=bool(args.from_archive),
        receipt_dirs=[args.receipt_dir] if args.receipt_dir else None,
        inputs=list(args.input or []) or None,
        include_home=bool(args.include_home),
        use_backfill=not bool(args.no_backfill),
    )
    out_obj = dict(report)
    if not args.verbose:
        out_obj.pop("rows", None)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        out_obj["written"] = args.out
    _emit({"ok": True, "command": "lineage-backprop", **out_obj})
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hyperlex", description="Hyperlex memetic emergence engine")
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser("version")
    v.set_defaults(func=cmd_version)

    c = sub.add_parser("check")
    c.set_defaults(func=cmd_check)

    src = sub.add_parser("sources", help="List sources + routes")
    src.add_argument("--route", default="")
    src.add_argument("--source", default="")
    src.set_defaults(func=cmd_sources)

    cmds = sub.add_parser("commands", help="Simplified command map")
    cmds.set_defaults(func=cmd_commands)

    a = sub.add_parser("analyze")
    a.add_argument("query_pos", nargs="?", default="")
    a.add_argument("--query", default="")
    a.add_argument("--source", default="mock")
    a.add_argument("--route", default="")
    a.add_argument("--structured-ingest", action="store_true", default=True)
    a.add_argument("--validate", action="store_true")
    a.add_argument("--forecasts", action="store_true")
    a.add_argument("--receipt", action="store_true")
    a.add_argument("--receipt-dir", default="")
    a.add_argument("--relay", action="store_true")
    a.add_argument("--out", default="")
    a.set_defaults(func=cmd_analyze)

    run = sub.add_parser("run", help="One-shot: analyze + receipt + forecasts")
    run.add_argument("query_pos", nargs="?", default="")
    run.add_argument("--query", default="")
    run.add_argument("--source", default="mock")
    run.add_argument("--route", default="offline")
    run.add_argument("--no-receipt", action="store_true")
    run.add_argument("--no-forecasts", action="store_true")
    run.add_argument("--receipt-dir", default="")
    run.add_argument("--out", default="")
    run.add_argument("--validate", action="store_true")
    run.set_defaults(func=cmd_run)

    r = sub.add_parser("relay")
    r.add_argument("--input", default="")
    r.add_argument("--list-runes", action="store_true")
    r.add_argument("--forecasts", action="store_true")
    r.set_defaults(func=cmd_relay)

    s = sub.add_parser("settle")
    s.add_argument("--forecast-id", default="")
    s.add_argument("--forecast-file", default="")
    s.add_argument("--decision", required=True)
    s.add_argument("--outcome", type=float, default=None)
    s.add_argument("--log", default="")
    s.set_defaults(func=cmd_settle)

    ss = sub.add_parser("score-series")
    ss.add_argument("--log", default="")
    ss.add_argument("--signal-key", default="")
    ss.set_defaults(func=cmd_score_series)

    sc = sub.add_parser("scan")
    sc.add_argument("--query", default="")
    sc.add_argument("--queries", default="")
    sc.add_argument("--source", default="mock")
    sc.add_argument("--receipt", action="store_true")
    sc.add_argument("--forecasts", action="store_true")
    sc.set_defaults(func=cmd_scan)

    sim = sub.add_parser("simulate", help="Phase 5 simulation / risk")
    sim.add_argument("--term", default="")
    sim.add_argument("--query", default="")
    sim.add_argument("--mode", default="scenario")
    sim.add_argument("--family", default="")
    sim.add_argument("--domain", default="general")
    sim.add_argument("--stage", default="")
    sim.add_argument("--virality", type=float, default=0.5)
    sim.add_argument("--memetic", type=float, default=0.5)
    sim.add_argument("--communities", type=int, default=6)
    sim.add_argument("--agents", type=int, default=20)
    sim.add_argument("--steps", type=int, default=12)
    sim.add_argument("--from-analyze", action="store_true")
    sim.add_argument("--source", default="mock")
    sim.add_argument("--out", default="")
    sim.set_defaults(func=cmd_simulate)

    lbf = sub.add_parser("lineage-backfill", help="YTD slang backfill packs")
    lbf.add_argument("--year", type=int, default=2026)
    lbf.add_argument("--through", default="")
    lbf.add_argument("--root", default="")
    lbf.add_argument("--list", action="store_true")
    lbf.add_argument("--verbose", action="store_true")
    lbf.add_argument("--out", default="")
    lbf.set_defaults(func=cmd_lineage_backfill)

    lbp = sub.add_parser("lineage-backprop", help="Non-mutating lineage rematch")
    lbp.add_argument("--year", type=int, default=2026)
    lbp.add_argument("--through", default="")
    lbp.add_argument("--root", default="")
    lbp.add_argument("--from-golden", action="store_true")
    lbp.add_argument("--from-archive", action="store_true")
    lbp.add_argument("--include-home", action="store_true")
    lbp.add_argument("--receipt-dir", default="")
    lbp.add_argument("--input", action="append", default=[])
    lbp.add_argument("--no-backfill", action="store_true")
    lbp.add_argument("--verbose", action="store_true")
    lbp.add_argument("--out", default="")
    lbp.set_defaults(func=cmd_lineage_backprop)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        _emit({"ok": False, "error": "interrupted"})
        return 130
    except Exception as exc:
        traceback.print_exc()
        _emit({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
