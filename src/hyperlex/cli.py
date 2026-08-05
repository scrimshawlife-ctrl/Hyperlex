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

    result = detect_memetic_patterns(
        query=args.query or "slang emergence",
        ingest_source=args.source,
        use_structured_ingest=bool(args.structured_ingest),
        validate=bool(args.validate),
    )
    out: Dict[str, Any] = {"ok": True, "command": "analyze", "result": result}
    if args.receipt:
        path = emit_receipt(result, out_dir=args.receipt_dir or None)
        out["receipt"] = str(path)
        result = json.loads(Path(path).read_text(encoding="utf-8"))
        out["result"] = result
    if args.forecasts:
        out["forecasts"] = extract_forecasts(result)
    if args.relay:
        out["envelopes"] = relay_from_result(result)
    if args.out:
        Path(args.out).write_text(json.dumps(out["result"], indent=2, sort_keys=True), encoding="utf-8")
    _emit(out)
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
        queries = ["sharp steam revenge", "brainrot aura mid"]
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hyperlex", description="Hyperlex memetic emergence engine")
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser("version")
    v.set_defaults(func=cmd_version)

    c = sub.add_parser("check")
    c.set_defaults(func=cmd_check)

    a = sub.add_parser("analyze")
    a.add_argument("--query", default="")
    a.add_argument("--source", default="mock")
    a.add_argument("--structured-ingest", action="store_true")
    a.add_argument("--validate", action="store_true")
    a.add_argument("--forecasts", action="store_true")
    a.add_argument("--receipt", action="store_true")
    a.add_argument("--receipt-dir", default="")
    a.add_argument("--relay", action="store_true")
    a.add_argument("--out", default="")
    a.set_defaults(func=cmd_analyze)

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
