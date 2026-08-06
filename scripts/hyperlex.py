#!/usr/bin/env python3
"""Hermes entrypoint for the Hyperlex skill.

The skill can be executed directly from the installed directory with
stdlib tools only. Optional dependencies (e.g. requests/jsonschema) are
used when available but not required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
# Always put package src first so `import hyperlex` cannot resolve to
# scripts/hyperlex.py when this file's directory is on sys.path.
_src = str(SRC_DIR)
if _src in sys.path:
    sys.path.remove(_src)
sys.path.insert(0, _src)


def _read_version() -> str:
    version_file = ROOT / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip() or "0.0.0"
    return "0.0.0"


def _emit(obj: Dict[str, Any]) -> None:
    print(json.dumps(obj, sort_keys=True, indent=2))


@dataclass
class _Check:
    name: str
    ok: bool
    message: str


def _check(condition: bool, name: str, message_ok: str, message_fail: str) -> _Check:
    return _Check(name=name, ok=bool(condition), message=message_ok if condition else message_fail)


def _import_hyperlex():
    try:
        import importlib

        # Drop a shadowed scripts/hyperlex module if present.
        existing = sys.modules.get("hyperlex")
        if existing is not None:
            mod_file = getattr(existing, "__file__", "") or ""
            if mod_file.endswith("scripts/hyperlex.py") or Path(mod_file).name == "hyperlex.py" and "scripts" in mod_file:
                del sys.modules["hyperlex"]

        hyperlex = importlib.import_module("hyperlex")
        if not hasattr(hyperlex, "detect_memetic_patterns"):
            return None, f"imported non-package hyperlex from {getattr(hyperlex, '__file__', '?')}"
        return hyperlex, None
    except Exception as exc:  # pragma: no cover - surfaced as check failure
        return None, str(exc)


def _load_manifest() -> Tuple[Dict[str, Any], bool, str]:
    path = ROOT / "hyperlex.manifest.yaml"
    if not path.exists():
        return {}, False, f"missing manifest: {path}"
    try:
        # Keep parser lightweight to avoid hard dependency on PyYAML.
        try:
            import yaml  # type: ignore

            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            return (data or {}, bool(data), "ok")
        except Exception:
            # Minimal stdlib fallback for key: value lines (no nested structure).
            data: Dict[str, Any] = {}
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                if ":" in line and not line.endswith(":"):
                    key, _, val = line.partition(":")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in data and val:
                        data[key] = val
            return data, bool(data.get("name")), "ok (stdlib yaml fallback)"
    except Exception as exc:
        return {}, False, f"manifest parse failed: {exc}"


def cmd_check(_args: argparse.Namespace) -> int:
    checks: List[_Check] = []
    checks.append(_check((ROOT / "VERSION").exists(), "version_file", "VERSION exists", "VERSION missing"))
    checks.append(_check((ROOT / "SKILL.md").exists(), "skill_contract", "SKILL.md exists", "SKILL.md missing"))
    checks.append(_check((ROOT / "schemas/ingest.v1.schema.json").exists(), "schema_ingest", "ingest schema present", "ingest schema missing"))
    checks.append(_check((ROOT / "schemas/result.v1.schema.json").exists(), "schema_result", "result schema present", "result schema missing"))
    checks.append(_check((ROOT / "schemas/receipt.v1.schema.json").exists(), "schema_receipt", "receipt schema present", "receipt schema missing"))
    manifest, manifest_ok, manifest_msg = _load_manifest()
    checks.append(_check(manifest_ok, "manifest", manifest_msg, manifest_msg))

    import_ok = True
    import_msg = "core package importable"
    try:
        _pkg, err = _import_hyperlex()
        if _pkg is None:
            import_ok = False
            import_msg = f"core package import failed: {err}"
    except Exception as exc:  # pragma: no cover
        import_ok = False
        import_msg = f"import check failed: {exc}"
    checks.append(_check(import_ok, "python_import", import_msg, import_msg))

    if manifest:
        for key in ("name", "description", "version", "entrypoint"):
            checks.append(
                _check(
                    isinstance(manifest, dict) and bool(manifest.get(key)),
                    f"manifest.{key}",
                    f"manifest includes {key}",
                    f"manifest missing {key}",
                )
            )

    result = {
        "ok": all(item.ok for item in checks),
        "version": _read_version(),
        "checks": [item.__dict__ for item in checks],
    }
    _emit(result)
    return 0 if result["ok"] else 2


def cmd_doctor(_args: argparse.Namespace) -> int:
    """Deep Hermes-skill health check (filesystem + import + offline smoke path)."""
    checks: List[_Check] = []

    required_files = [
        "VERSION",
        "SKILL.md",
        "hyperlex.manifest.yaml",
        "scripts/hyperlex.py",
        "src/hyperlex/__init__.py",
        "src/hyperlex/analysis/__init__.py",
        "src/hyperlex/calibration/scoring.py",
        "src/hyperlex/relay/__init__.py",
        "src/hyperlex/compat/abraxas/__init__.py",
        "src/hyperlex/connectors/market_signal.py",
        "src/hyperlex/diagrams/from_receipts.py",
        "src/hyperlex/llm/governed.py",
        "src/hyperlex/simulation/__init__.py",
        "src/hyperlex/vectordb/__init__.py",
        "src/hyperlex/analysis/backfill.py",
        "src/hyperlex/analysis/backprop.py",
        "data/backfill/2026/README.md",
        "docs/phase5.md",
        "docs/modules/simulation.md",
        "schemas/forecast.v1.schema.json",
        "schemas/settlement.v1.schema.json",
        "schemas/brier_series.v1.schema.json",
        "schemas/rune_envelope.v1.schema.json",
        "examples/receipts/golden/MANIFEST.json",
        "examples/case-studies/e2e-mock-scan.md",
        "scripts/run_case_study.py",
        "mkdocs.yml",
        "STATUS.md",
        "src/hyperlex/receipt/stats.py",
    ]
    for rel in required_files:
        p = ROOT / rel
        checks.append(_check(p.exists(), f"file:{rel}", f"present: {rel}", f"missing: {rel}"))

    golden = ROOT / "examples" / "receipts" / "golden"
    golden_json = [p for p in golden.glob("*.json") if p.name != "MANIFEST.json"] if golden.is_dir() else []
    checks.append(
        _check(
            len(golden_json) >= 7,
            "golden_corpus",
            f"golden receipts: {len(golden_json)}",
            f"golden corpus thin: {len(golden_json)}",
        )
    )

    pkg, err = _import_hyperlex()
    checks.append(_check(pkg is not None, "import_hyperlex", "hyperlex importable", f"import failed: {err}"))

    analyze_ok = False
    brier_null = False
    lineage_ok = False
    pred_ok = False
    if pkg is not None:
        try:
            result = pkg.detect_memetic_patterns(
                query="sharp steam revenge",
                ingest_source="mock",
                validate=False,
            )
            analyze_ok = True
            brier_null = result.get("provenance", {}).get("brier") is None
            lineage_ok = bool((result.get("analysis") or {}).get("lineage"))
            pred = ((result.get("analysis") or {}).get("virality") or {}).get("prediction")
            pred_ok = isinstance(pred, dict) and "predicted_hybrid" in pred
            api = getattr(pkg, "API_V1", None)
            if api is None:
                checks.append(_check(False, "api_v1", "", "API_V1 missing"))
            else:
                missing = [n for n in api if not hasattr(pkg, n)]
                checks.append(
                    _check(
                        not missing,
                        "api_v1",
                        f"API_V1 n={len(api)}",
                        f"API_V1 missing: {missing}",
                    )
                )
        except Exception as exc:
            checks.append(_check(False, "analyze_exception", "", f"analyze failed: {exc}"))

    checks.append(_check(analyze_ok, "analyze_mock", "mock analyze ok", "mock analyze failed"))
    checks.append(_check(brier_null, "brier_null", "open brier is null", "open brier is not null"))
    checks.append(_check(lineage_ok, "lineage_match", "lineage attached on sharp query", "lineage missing on sharp query"))
    checks.append(_check(pred_ok, "virality_prediction", "virality.prediction present", "virality.prediction missing"))

    if pkg is not None:
        try:
            from hyperlex.compat import abraxas as abx

            checks.append(
                _check(
                    len(abx.list_hlx_runes()) >= 4,
                    "compat_abraxas",
                    "compat.abraxas runes ok",
                    "compat.abraxas weak",
                )
            )
        except Exception as exc:
            checks.append(_check(False, "compat_abraxas", "", f"compat import failed: {exc}"))
        try:
            from hyperlex.llm import llm_enabled

            checks.append(
                _check(True, "llm_module", f"llm module ok (enabled={llm_enabled()})", "llm module missing")
            )
        except Exception as exc:
            checks.append(_check(False, "llm_module", "", str(exc)))
        try:
            from hyperlex.simulation import run_phase5_scenario

            sc = run_phase5_scenario("rizz", domain="ai", include_phylogeny=True)
            checks.append(
                _check(
                    sc.get("brier") is None and sc.get("schema") == "hyperlex.phase5_scenario.v1",
                    "phase5_simulate",
                    f"phase5 ok tier={((sc.get('hyperstition_risk') or {}).get('tier'))}",
                    "phase5 scenario failed or invented brier",
                )
            )
        except Exception as exc:
            checks.append(_check(False, "phase5_simulate", "", f"phase5 failed: {exc}"))
        try:
            from hyperlex.vectordb import VectorStore, seed_from_registry, vector_search
            import tempfile
            from pathlib import Path as _P

            tdb = _P(tempfile.mkdtemp()) / "doctor_vector.db"
            with VectorStore(tdb) as store:
                seed_from_registry(store)
                n = store.count("term")
            hits = vector_search("rizz locked in", path=tdb, kind="term", top_k=3)
            checks.append(
                _check(
                    n >= 8 and hits.get("ok") and hits.get("brier") is None,
                    "vector_db",
                    f"vector db ok n_terms={n} hits={hits.get('n_hits')}",
                    "vector db seed/search failed",
                )
            )
        except Exception as exc:
            checks.append(_check(False, "vector_db", "", f"vector db failed: {exc}"))

    packs = list((ROOT / "data" / "backfill" / "2026").glob("2026-*.json")) if (ROOT / "data" / "backfill" / "2026").is_dir() else []
    checks.append(
        _check(
            len(packs) >= 8,
            "backfill_packs",
            f"YTD packs: {len(packs)}",
            f"YTD packs thin: {len(packs)}",
        )
    )

    home_hx = Path.home() / ".hyperlex"
    checks.append(
        _check(True, "operator_home", f"~/.hyperlex exists={home_hx.is_dir()} path={home_hx}", "")
    )

    ok = all(c.ok for c in checks)
    _emit({
        "ok": ok,
        "command": "doctor",
        "version": _read_version(),
        "skill_root": str(ROOT),
        "n_checks": len(checks),
        "n_failed": sum(1 for c in checks if not c.ok),
        "checks": [c.__dict__ for c in checks],
        "posture": "hermes_skill_python_package_repo",
    })
    return 0 if ok else 2


def cmd_sources(args: argparse.Namespace) -> int:
    from hyperlex.intake.sources import list_sources, resolve_source

    catalog = list_sources(include_aliases=not bool(getattr(args, "no_aliases", False)))
    out: Dict[str, Any] = {"ok": True, "command": "sources", **catalog}
    # Optional resolve preview: sources --route live  or  sources --source real
    if getattr(args, "route", None) or getattr(args, "source", None):
        out["resolve"] = resolve_source(
            getattr(args, "source", None) or None,
            route=getattr(args, "route", None) or None,
        )
    _emit(out)
    return 0


def cmd_signal(args: argparse.Namespace) -> int:
    """Emit generic market_signal + forecast_pipeline packets."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    payload, load_error = _get_input_payload(args.input)
    if load_error:
        _emit({"ok": False, "error": load_error})
        return 2
    if payload is None:
        _emit({"ok": False, "error": "input required"})
        return 2

    result = payload.get("result") if isinstance(payload.get("result"), dict) and "analysis" not in payload else payload
    from hyperlex.connectors import build_market_signal, build_forecast_pipeline

    series = None
    if args.with_series:
        series = pkg.recompute_series(
            path=_resolve_log_path(args) if hasattr(args, "log") else None,
            signal_key=args.signal_key or None,
        )

    market = build_market_signal(result, domain=args.domain or "narrative")
    pipeline = build_forecast_pipeline(result, market_signal=market, series=series)
    out = {"ok": True, "command": "signal", "market_signal": market, "forecast_pipeline": pipeline}
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    _emit(out)
    return 0


def cmd_feedback(args: argparse.Namespace) -> int:
    """Hyperstition (or series) feedback → advisory mapping for future forecasts."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    from hyperlex.connectors import hyperstition_feedback_from_series

    log_path = _resolve_log_path(args)
    series = pkg.recompute_series(path=log_path, signal_key=args.signal_key or "hyperstition.stage")
    feedback = hyperstition_feedback_from_series(series)
    _emit({
        "ok": True,
        "command": "feedback",
        "log_path": str(log_path),
        "series": {
            "status": series.get("status"),
            "n": series.get("n"),
            "series_brier": series.get("series_brier"),
        },
        "feedback": feedback,
    })
    return 0


def cmd_diagram(args: argparse.Namespace) -> int:
    """Generate Mermaid diagrams from receipt ledger and/or receipt files."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    from hyperlex.diagrams import (
        diagram_from_ledger,
        diagram_from_receipt_files,
        write_diagram_bundle,
        diagram_receipt_flow,
    )
    import glob as _glob

    diagrams: Dict[str, str] = {}
    sources: List[str] = []
    paths: List[Path] = [Path(p) for p in (args.input or [])]
    if args.from_golden:
        golden = ROOT / "examples" / "receipts" / "golden"
        paths.extend(sorted(golden.glob("*.json")))
    if args.glob:
        paths.extend(Path(g) for g in _glob.glob(args.glob))

    use_ledger = bool(args.from_ledger)
    if not use_ledger and not paths:
        # default: golden corpus if present, else receipt ledger
        golden = ROOT / "examples" / "receipts" / "golden"
        if golden.is_dir() and any(golden.glob("*.json")):
            paths.extend(sorted(golden.glob("*.json")))
            sources.append("default:golden")
        else:
            use_ledger = True

    if use_ledger:
        ledger = Path(args.ledger) if args.ledger else pkg.default_ledger_path()
        diagrams.update(
            diagram_from_ledger(
                ledger_path=ledger,
                limit=int(args.limit),
                lineage_family=args.lineage_family or None,
            )
        )
        sources.append(f"ledger:{ledger}")

    seen: set = set()
    uniq: List[Path] = []
    for p in paths:
        if not p.exists() or p.suffix != ".json" or p.name == "MANIFEST.json":
            continue
        rp = str(p.resolve())
        if rp in seen:
            continue
        seen.add(rp)
        uniq.append(p)

    if uniq:
        diagrams.update(diagram_from_receipt_files(uniq))
        sources.append(f"files:{len(uniq)}")

    if not diagrams or all(k == "meta" for k in diagrams):
        _emit({"ok": False, "error": "no diagrams; pass --from-ledger, --from-golden, --input, or --glob"})
        return 2

    written = {}
    out_dir = args.out_dir or str(ROOT / "out" / "diagrams")
    written = write_diagram_bundle(
        diagrams,
        out_dir,
        html=not args.no_html,
        prefix=args.prefix or "hyperlex",
    )

    _emit({
        "ok": True,
        "command": "diagram",
        "sources": sources,
        "n_diagrams": len([k for k in diagrams if k != "meta"]),
        "out_dir": out_dir,
        "files": written,
        "kinds": [k for k in diagrams.keys() if k != "meta"],
    })
    return 0


def cmd_relay(args: argparse.Namespace) -> int:
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    if args.list_runes:
        _emit({"ok": True, "command": "relay", "runes": pkg.list_runes()})
        return 0

    payload, load_error = _get_input_payload(args.input)
    if load_error:
        _emit({"ok": False, "error": load_error})
        return 2
    if payload is None:
        _emit({"ok": False, "error": "input required (analysis result JSON) unless --list-runes"})
        return 2

    result = payload.get("result") if isinstance(payload.get("result"), dict) and "analysis" not in payload else payload
    envelopes = pkg.relay_from_result(
        result,
        include_signal=not args.no_signal,
        include_scan=not args.no_scan,
    )

    if args.forecasts:
        fcs = pkg.extract_forecasts(result)
        envelopes.append(pkg.relay_forecasts(fcs))

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(envelopes, sort_keys=True, indent=2), encoding="utf-8")

    _emit({
        "ok": True,
        "command": "relay",
        "n_envelopes": len(envelopes),
        "envelopes": envelopes,
    })
    return 0


def _resolve_cli_source(args: argparse.Namespace) -> Tuple[str, Dict[str, Any]]:
    """Shared --source / --route resolution for ingest, analyze, run, scan."""
    from hyperlex.intake.sources import pick_source

    route = getattr(args, "route", None) or None
    source = getattr(args, "source", None) or "mock"
    return pick_source(source, route=route)


def _build_ingest_result(pkg, args: argparse.Namespace) -> Dict[str, Any]:
    # Pass original --source/--route into package so offline force keeps intended_source
    route = getattr(args, "route", None) or None
    requested = getattr(args, "source", None) or "mock"
    # Always structured by default; --raw for string-only legacy shape
    if getattr(args, "raw", False) and not getattr(args, "structured", True):
        raw = pkg.ingest_signal(query=args.query, source=requested, route=route)
        from hyperlex.intake.sources import pick_source

        source, resolved = pick_source(requested, route=route)
        return {
            "query": args.query,
            "source": source,
            "raw_signal": raw,
            "raw_len": len(raw),
            "route": resolved,
        }
    max_terms = int(getattr(args, "max_terms", 8) or 8)
    return pkg.fetch_ingest(
        query=args.query,
        source=requested,
        structured=True,
        max_terms=max_terms,
        route=route,
    )


def cmd_ingest(args: argparse.Namespace) -> int:
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    # Default: full automatic backend (ingest → results). --raw-only for signal only.
    if not bool(getattr(args, "raw_only", False)):
        # Map ingest positional `query` onto pipeline query_pos
        if not getattr(args, "query_pos", None):
            args.query_pos = getattr(args, "query", None) or ""
        args.command_label = "ingest"
        if not getattr(args, "route", None):
            args.route = "offline"  # auto backend defaults safe
        return cmd_pipeline(args)

    result = _build_ingest_result(pkg, args)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, sort_keys=True, indent=2), encoding="utf-8")
    _emit({
        "ok": True,
        "command": "ingest",
        "mode": "raw_only",
        "source": result.get("source"),
        "route": (result.get("route") or {}).get("route") if isinstance(result.get("route"), dict) else None,
        "result": result,
    })
    return 0


def _get_input_payload(path: str | None) -> Tuple[Dict[str, Any] | None, str | None]:
    if not path:
        return None, None
    fp = Path(path)
    if not fp.exists():
        return None, f"input file missing: {fp}"
    try:
        with fp.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if not isinstance(payload, dict):
            return None, "input file must contain a JSON object"
        return payload, None
    except Exception as exc:
        return None, f"failed to load JSON input: {exc}"


def _resolve_log_path(args: argparse.Namespace) -> Path:
    """CLI log path: --log > HYPERLEX_SCORE_LOG > ~/.hyperlex/score_log.jsonl > repo out/."""
    log_arg = getattr(args, "log", None) or ""
    if log_arg:
        return Path(log_arg).expanduser().resolve()
    from hyperlex.calibration.score_log import default_log_path, repo_log_path

    # Prefer env / home; if --repo-log, use out/calibration/
    if getattr(args, "repo_log", False):
        return repo_log_path(ROOT)
    return default_log_path()


def cmd_analyze(args: argparse.Namespace) -> int:
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    payload, load_error = _get_input_payload(args.input)
    if load_error:
        _emit({"ok": False, "error": load_error})
        return 2

    # Positional query preferred; --query remains for scripts
    query = (getattr(args, "query_pos", None) or args.query or "").strip()
    if payload is not None:
        query = query or str(payload.get("query") or "")
        # Prefer explicit CLI source/route; else inherit from ingest JSON
        if not getattr(args, "route", None) and (not args.source or args.source == "mock"):
            if payload.get("source"):
                args.source = str(payload.get("source"))

    if not query:
        query = "slang emergence"

    # Pass original source/route so resolve keeps intended_source under offline
    requested = getattr(args, "source", None) or "mock"
    route = getattr(args, "route", None) or None
    source, resolved = _resolve_cli_source(args)

    result = pkg.detect_memetic_patterns(
        query=query,
        ingest_source=requested,
        use_structured_ingest=True,
        validate=args.validate,
        ingest_route=route,
    )

    forecasts = None
    log_records = None
    receipt_path = None
    if getattr(args, "receipt", False):
        out_dir = Path(args.receipt_dir) if getattr(args, "receipt_dir", "") else None
        ledger = None
        if getattr(args, "ledger", ""):
            ledger = Path(args.ledger)
        receipt_path = pkg.emit_receipt(
            result,
            out_dir=out_dir,
            validate=bool(args.validate),
            append_ledger=not getattr(args, "no_ledger", False),
            ledger_path=ledger,
        )
        # reload so result carries receipt block for forecast anchoring
        try:
            result = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
        except Exception:
            pass

    if getattr(args, "forecasts", False):
        receipt_ref = None
        if isinstance(result.get("receipt"), dict):
            receipt_ref = {
                "integrity": result["receipt"].get("integrity"),
                "path": str(receipt_path) if receipt_path else None,
            }
        forecasts = pkg.extract_forecasts(result, receipt_ref=receipt_ref)
        if getattr(args, "append_log", False) and forecasts:
            log_path = _resolve_log_path(args)
            log_records = []
            for fc in forecasts:
                log_records.append(pkg.append_forecast(fc, path=log_path))

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, sort_keys=True, indent=2), encoding="utf-8")

    payload_out: Dict[str, Any] = {
        "ok": True,
        "command": getattr(args, "command_label", None) or "analyze",
        "query": query,
        "source": source,
        "route": resolved.get("route"),
        "result": result,
    }
    if receipt_path is not None:
        payload_out["receipt"] = str(receipt_path)
    if forecasts is not None:
        payload_out["forecasts"] = forecasts
        payload_out["n_forecasts"] = len(forecasts)
    if log_records is not None:
        payload_out["log_path"] = str(_resolve_log_path(args))
        payload_out["logged"] = len(log_records)
    _emit(payload_out)
    return 0


def cmd_pipeline(args: argparse.Namespace) -> int:
    """Automatic backend: ingest → analyze → receipt → forecasts → results (no settle)."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    from hyperlex.pipeline import run_pipeline

    q = (getattr(args, "query_pos", None) or getattr(args, "query", None) or getattr(args, "term", None) or "").strip()
    queries = None
    if getattr(args, "queries", None):
        queries = [p.strip() for p in str(args.queries).split(",") if p.strip()]
    if not q and not queries:
        _emit({"ok": False, "error": "pipeline requires a query (positional / --query) or --queries"})
        return 2

    log_path = _resolve_log_path(args) if getattr(args, "log", None) or getattr(args, "repo_log", False) else None
    packet = run_pipeline(
        q or (queries[0] if queries else ""),
        route=getattr(args, "route", None) or "offline",
        source=getattr(args, "source", None) or "mock",
        expand_terms=not bool(getattr(args, "no_expand", False)),
        receipt=not bool(getattr(args, "no_receipt", False)),
        forecasts=not bool(getattr(args, "no_forecasts", False)),
        append_log=not bool(getattr(args, "no_append_log", False)),
        phase5=not bool(getattr(args, "no_phase5", False)),
        domain=getattr(args, "domain", None) or "general",
        log_path=log_path,
        receipt_dir=getattr(args, "receipt_dir", None) or None,
        validate=bool(getattr(args, "validate", False)),
        queries=queries,
    )
    packet["command"] = getattr(args, "command_label", None) or "pipeline"
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")
        packet["written"] = args.out
    # compact multi-atom CLI unless verbose
    if not getattr(args, "verbose", False) and int(packet.get("n_atoms") or 0) > 1:
        compact = dict(packet)
        slim = []
        for u in compact.get("results") or []:
            slim.append({
                "query": u.get("query"),
                "ok": u.get("ok"),
                "primary_term": u.get("primary_term"),
                "lineage_family": u.get("lineage_family"),
                "risk_tier": u.get("risk_tier"),
                "receipt": u.get("receipt"),
                "n_forecasts": u.get("n_forecasts"),
                "forecast_ids": u.get("forecast_ids"),
                "phase5": u.get("phase5"),
                "brier": None,
                "error": u.get("error"),
            })
        compact["results"] = slim
        compact["hint"] = "pass --verbose for full analysis bodies; --out always writes full JSON"
        _emit(compact)
    else:
        _emit(packet)
    return 0 if packet.get("ok") else 1


def cmd_run(args: argparse.Namespace) -> int:
    """Automatic backend (alias of pipeline): ingest → results."""
    args.command_label = "run"
    if not getattr(args, "route", None):
        args.route = "offline"
    return cmd_pipeline(args)


def cmd_commands(_args: argparse.Namespace) -> int:
    """Print simplified command map (operator / calibration / research / maintenance)."""
    map_obj = {
        "schema": "hyperlex.command_map.v1",
        "version": _read_version(),
        "note": (
            "Prefer short daily path. ANN vector backend deferred until corpus grows. "
            "Risk→cron is advisory only. Never invent Brier."
        ),
        "daily_ops": [
            {"cmd": "pipeline \"rizz\"", "why": "AUTO backend: ingest→analyze→receipt→forecasts→phase5 risk"},
            {"cmd": "ingest \"rizz\"", "why": "Same as pipeline (default); use --raw-only for signal only"},
            {"cmd": "run \"rizz\" --route offline", "why": "Alias of pipeline (safe burn-in)"},
            {"cmd": "run \"sigma rizz locked in\"", "why": "Auto-expands to atoms; one full result each"},
            {"cmd": "scan --route offline --receipt --forecasts --append-log", "why": "Multi-query LIVE_EMERGENCE_SCAN"},
            {"cmd": "risk-schedule --tier MODERATE --schedule-out /tmp/hlx-cron", "why": "Advisory cron envelope"},
        ],
        "calibration": [
            {"cmd": "pending", "why": "List open (unsettled) forecasts from score log"},
            {"cmd": "settle --forecast-id <id> --decision TRUE|FALSE|VOID", "why": "Operator settlement"},
            {"cmd": "score-series --mean-shift --verify-chain", "why": "Brier series after settlements"},
        ],
        "ingest_routing": [
            {"cmd": "sources", "why": "Catalog + routes (offline|live|default|glossary|social)"},
            {"cmd": "sources --route live", "why": "Preview resolve for a route"},
            {"cmd": "ingest \"<query>\" --route offline", "why": "Ingest only (structured + fingerprint)"},
            {"cmd": "analyze \"<query>\" --route offline", "why": "Analyze without auto-receipt"},
        ],
        "research": [
            {"cmd": "simulate --term <t> --mode scenario", "why": "Phase 5 research (SPECULATIVE, brier null)"},
            {"cmd": "simulate --mode schedule --tier ELEVATED", "why": "Risk→scan plan"},
            {"cmd": "vector-search \"…\"", "why": "Local vector DB"},
            {"cmd": "archive-export --history", "why": "Sanitized Pages run history"},
        ],
        "maintenance": [
            {"cmd": "doctor", "why": "Health check"},
            {"cmd": "check / smoke", "why": "Packaging readiness"},
            {"cmd": "list-receipts / ledger-stats", "why": "Local ledger review"},
        ],
        "operator_burn_in": [
            "1. run \"…\" --route offline  (repeat on cron via risk-schedule MODERATE)",
            "2. pending → settle a few forecasts",
            "3. score-series --verify-chain",
            "4. Only then consider --route live or higher risk tiers",
        ],
        "deferred": [
            "ANN vector backend — wait until vector corpus is large enough to need it",
            "More Phase 5 modes — research surface is dense enough",
            "Public PyPI / Abraxas hard import — out of scope",
        ],
    }
    _emit({"ok": True, "command": "commands", **map_obj})
    return 0


def cmd_pending(args: argparse.Namespace) -> int:
    """List open (unsettled) forecasts from the score log."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    from hyperlex.calibration.score_log import index_forecasts, index_settlements, read_log

    log_path = _resolve_log_path(args)
    records = read_log(log_path)
    forecasts = index_forecasts(records)
    settled_ids = set(index_settlements(records).keys())

    open_fcs = []
    for fid, fc in forecasts.items():
        if fid in settled_ids:
            continue
        open_fcs.append({
            "forecast_id": fid,
            "signal_key": fc.get("signal_key"),
            "probability": fc.get("probability") or fc.get("p"),
            "claim": fc.get("claim") or fc.get("statement"),
            "created_at": fc.get("created_at") or fc.get("extracted_at"),
        })
    limit = int(getattr(args, "limit", 50) or 50)
    open_fcs = open_fcs[:limit]
    _emit({
        "ok": True,
        "command": "pending",
        "log_path": str(log_path),
        "n_forecasts_indexed": len(forecasts),
        "n_open": len(open_fcs),
        "open": open_fcs,
        "note": "Settle with: settle --forecast-id <id> --decision TRUE|FALSE|VOID",
        "brier": None,
    })
    return 0


def cmd_emit_receipt(args: argparse.Namespace) -> int:
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    payload, load_error = _get_input_payload(args.input)
    if load_error:
        _emit({"ok": False, "error": load_error})
        return 2
    if payload is None:
        _emit({"ok": False, "error": "input required"})
        return 2

    # strip existing receipt block so integrity is recomputed over analysis body
    body = {k: v for k, v in payload.items() if k != "receipt"}
    out_dir = Path(args.out_dir) if args.out_dir else None
    ledger = Path(args.ledger) if args.ledger else None
    path = pkg.emit_receipt(
        body,
        out_dir=out_dir,
        validate=bool(args.validate),
        append_ledger=not args.no_ledger,
        ledger_path=ledger,
    )
    _emit({
        "ok": True,
        "command": "emit-receipt",
        "receipt": str(path),
        "ledger_path": str(ledger or pkg.default_ledger_path()),
    })
    return 0


def cmd_ledger_diff(args: argparse.Namespace) -> int:
    """Diff two receipt JSON files (integrity, lineage, typology, virality)."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    a, err_a = _get_input_payload(args.a)
    b, err_b = _get_input_payload(args.b)
    if err_a or err_b or a is None or b is None:
        _emit({"ok": False, "error": err_a or err_b or "need --a and --b receipt JSON"})
        return 2

    def snap(r: Dict[str, Any]) -> Dict[str, Any]:
        prov = r.get("provenance") or {}
        analysis = r.get("analysis") or {}
        lin = analysis.get("lineage") or {}
        mem = analysis.get("memetics") or {}
        vir = analysis.get("virality") or {}
        rec = r.get("receipt") or {}
        return {
            "integrity": rec.get("integrity"),
            "canonical_hash": prov.get("canonical_hash"),
            "ingest_source": prov.get("ingest_source"),
            "brier": prov.get("brier"),
            "lineage_family": lin.get("family_id"),
            "lineage_confidence": lin.get("confidence"),
            "typology": mem.get("typology_primary") or mem.get("typology"),
            "virality_hybrid": vir.get("hybrid_score"),
            "virality_predicted": (vir.get("prediction") or {}).get("predicted_hybrid"),
            "hyperstition": (analysis.get("hyperstition") or {}).get("loop_stage"),
            "n_neologisms": len(analysis.get("neologisms") or []),
        }

    sa, sb = snap(a), snap(b)
    deltas = {k: {"a": sa.get(k), "b": sb.get(k)} for k in sa if sa.get(k) != sb.get(k)}
    _emit({
        "ok": True,
        "command": "ledger-diff",
        "a": sa,
        "b": sb,
        "changed_fields": sorted(deltas.keys()),
        "deltas": deltas,
        "same_integrity": sa.get("integrity") == sb.get("integrity"),
    })
    return 0


def cmd_list_receipts(args: argparse.Namespace) -> int:
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    ledger = Path(args.ledger) if args.ledger else pkg.default_ledger_path()
    entries = pkg.list_receipts(
        path=ledger,
        limit=int(args.limit),
        lineage_family=args.lineage_family or None,
    )
    _emit({
        "ok": True,
        "command": "list-receipts",
        "ledger_path": str(ledger),
        "n": len(entries),
        "receipts": entries,
    })
    return 0


def cmd_archive_export(args: argparse.Namespace) -> int:
    """Export sanitized long-term analysis archive (for docs/Pages static run history)."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    from hyperlex.archive import export_analysis_archive, export_run_history

    receipt_dirs: List[str] = []
    if args.receipt_dir:
        receipt_dirs.append(args.receipt_dir)
    if args.include_home_receipts:
        receipt_dirs.append(str(Path.home() / ".hyperlex" / "receipts"))
    if args.include_golden:
        receipt_dirs.append(str(ROOT / "examples" / "receipts" / "golden"))

    ledger = Path(args.ledger) if args.ledger else None
    phase5 = None
    if args.phase5:
        raw = json.loads(Path(args.phase5).read_text(encoding="utf-8"))
        # allow full CLI simulate wrapper or raw scenario
        if isinstance(raw, dict) and "scenario" in raw and isinstance(raw["scenario"], dict):
            phase5 = raw["scenario"]
        else:
            phase5 = raw

    use_history = bool(args.history) or bool(args.phase5) or not args.out_dir
    if use_history and not args.no_history:
        archive_root = Path(args.archive_root) if args.archive_root else (ROOT / "docs" / "archive")
        result = export_run_history(
            archive_root=archive_root,
            ledger_path=ledger,
            receipt_dirs=receipt_dirs or None,
            include_ledger_index=not args.no_ledger_index,
            snapshot_id=args.snapshot_id or None,
            update_latest=not bool(args.no_latest) and phase5 is None,
            notes=args.notes or "",
            phase5_scenario=phase5,
        )
    else:
        out_dir = Path(args.out_dir) if args.out_dir else (ROOT / "docs" / "archive" / "latest")
        result = export_analysis_archive(
            out_dir=out_dir,
            ledger_path=ledger,
            receipt_dirs=receipt_dirs or None,
            include_ledger_index=not args.no_ledger_index,
            snapshot_id=args.snapshot_id or None,
            notes=args.notes or "",
        )
    _emit({"ok": True, "command": "archive-export", **result})
    return 0


def cmd_archive_catalog(args: argparse.Namespace) -> int:
    """Rebuild docs/archive catalog index for Pages run history."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    from hyperlex.archive import rebuild_archive_catalog

    root = Path(args.archive_root) if args.archive_root else (ROOT / "docs" / "archive")
    catalog = rebuild_archive_catalog(root)
    _emit({
        "ok": True,
        "command": "archive-catalog",
        "n_runs": catalog.get("n_runs"),
        "latest_snapshot_id": catalog.get("latest_snapshot_id"),
        "catalog": str(root / "catalog.json"),
        "index": str(root / "index.md"),
    })
    return 0


def cmd_vector_seed(args: argparse.Namespace) -> int:
    """Seed local SQLite vector DB from registry, backfill, and/or receipts."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    from hyperlex.vectordb import seed_all

    receipt_dirs = []
    if args.receipt_dir:
        receipt_dirs.append(args.receipt_dir)
    if args.include_golden:
        receipt_dirs.append(str(ROOT / "examples" / "receipts" / "golden"))

    report = seed_all(
        path=Path(args.db) if args.db else None,
        year=int(args.year),
        through=args.through or "2026-08",
        backfill_root=Path(args.root) if args.root else (ROOT / "data" / "backfill"),
        receipt_dirs=receipt_dirs or None,
        include_home=bool(args.include_home),
        include_registry=not bool(args.no_registry),
        include_backfill=not bool(args.no_backfill),
        include_receipts=not bool(args.no_receipts),
        backend=getattr(args, "backend", None),
    )
    _emit({"ok": True, "command": "vector-seed", **report})
    return 0


def cmd_vector_search(args: argparse.Namespace) -> int:
    """Cosine search over local vector DB."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    from hyperlex.vectordb import vector_search

    out = vector_search(
        args.query,
        path=Path(args.db) if args.db else None,
        kind=args.kind or None,
        family_id=args.family or None,
        top_k=int(args.top_k),
        min_score=float(args.min_score),
        backend=getattr(args, "backend", None),
    )
    _emit({"ok": bool(out.get("ok")), "command": "vector-search", **out})
    return 0 if out.get("ok") else 2


def cmd_vector_stats(args: argparse.Namespace) -> int:
    """Stats for vector DB (sqlite or chroma)."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    backend = getattr(args, "backend", None) or __import__("os").environ.get("HYPERLEX_VECTOR_BACKEND", "sqlite")
    if backend == "chroma":
        from hyperlex.vectordb.chroma import ChromaVectorStore
        store = ChromaVectorStore()
        stats = store.stats()
        _emit({"ok": True, "command": "vector-stats", "backend": "chroma", **stats})
    else:
        from hyperlex.vectordb import VectorStore
        with VectorStore(Path(args.db) if args.db else None) as store:
            stats = store.stats()
        _emit({"ok": True, "command": "vector-stats", "backend": "sqlite", **stats})
    return 0


def cmd_lineage_backfill(args: argparse.Namespace) -> int:
    """List / inventory / merge YTD slang backfill packs (non-mutating receipts)."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    from hyperlex.analysis.backfill import apply_backfill, inventory_backfill, list_backfill_packs

    root = Path(args.root) if args.root else (ROOT / "data" / "backfill")
    year = int(args.year)
    through = args.through or None

    if args.list or args.inventory:
        inv = inventory_backfill(year, root=root, through=through)
        # drop full term dump unless --verbose
        if not args.verbose:
            inv = {k: v for k, v in inv.items() if k != "terms"}
            inv["terms_omitted"] = True
            inv["hint"] = "pass --verbose to include full term list"
        _emit({"ok": True, "command": "lineage-backfill", "mode": "inventory", **inv})
        return 0

    report = apply_backfill(year, through=through, root=root)
    # default: strip full merged_registry from CLI noise
    if not args.verbose:
        report = {k: v for k, v in report.items() if k != "merged_registry"}
        report["merged_registry_omitted"] = True
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        report["written"] = args.out
    _emit({"ok": True, "command": "lineage-backfill", "mode": "apply", **report})
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    """Phase 5: cultural transmission / multi-agent / risk / full scenario."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    from hyperlex.simulation import (
        TIER_POLICY,
        build_domain_phylogeny,
        build_family_phylogeny,
        calibrate_transmission_params,
        compare_scenarios,
        export_research_packet,
        forecast_hyperstition_risk,
        list_domain_packs,
        list_scenario_presets,
        plan_scan_from_term,
        plan_scan_from_tier,
        run_multi_agent_memetics,
        run_named_scenario,
        run_phase5_scenario,
        simulate_cultural_transmission,
        write_scan_plan,
    )

    term = (args.term or args.query or "slang signal").strip()
    domain = args.domain or "general"
    mode = (args.mode or "scenario").lower()

    analysis = None
    if args.from_analyze:
        analysis = pkg.detect_memetic_patterns(
            query=term,
            ingest_source=args.source or "mock",
        )
        lin = (analysis.get("analysis") or {}).get("lineage") or {}
        if not args.family and lin.get("family_id"):
            args.family = lin.get("family_id")

    if mode == "transmission":
        out = simulate_cultural_transmission(
            term,
            n_communities=int(args.communities),
            steps=int(args.steps),
            lineage_family=args.family or None,
            virality_hybrid=float(args.virality),
        )
    elif mode == "agents":
        out = run_multi_agent_memetics(
            term,
            n_agents=int(args.agents),
            steps=int(args.steps),
            lineage_family=args.family or None,
            memetic_score=float(args.memetic),
        )
    elif mode == "risk":
        if analysis:
            from hyperlex.simulation import risk_from_analysis

            out = risk_from_analysis(analysis, domain=domain)
        else:
            out = forecast_hyperstition_risk(
                hyperstition_stage=args.stage or None,
                virality_hybrid=float(args.virality),
                memetic_score=float(args.memetic),
                domain=domain,
                seed_term=term,
                lineage_family=args.family or None,
            )
    elif mode == "phylogeny":
        if args.list_domains:
            out = {"schema": "hyperlex.domain_phylogeny_index.v1", "domains": list_domain_packs()}
        elif args.domain and args.domain not in {"general", "markets", "ai", "politics"}:
            out = build_domain_phylogeny(args.domain)
        else:
            fam = args.family or "brainrot-aura"
            out = build_family_phylogeny(fam)
    elif mode == "calibrate":
        golden = Path(args.golden) if args.golden else (ROOT / "examples" / "calibration" / "settled_series.v1.json")
        out = calibrate_transmission_params(
            golden_path=golden if golden.is_file() else None,
            signal_key_contains=args.signal_key or None,
        )
    elif mode == "compare":
        if args.list_scenarios:
            out = {"schema": "hyperlex.scenario_library_index.v1", "scenarios": list_scenario_presets()}
        elif args.scenario:
            out = run_named_scenario(args.scenario, term, lineage_family=args.family or None)
            # drop full agent dump
            if isinstance(out.get("full"), dict):
                out = {k: v for k, v in out.items() if k != "full"}
        else:
            out = compare_scenarios(term, lineage_family=args.family or None)
    elif mode == "export":
        # load payload from --input or run a compare packet
        if args.input:
            raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
            payload = raw.get("scenario") if isinstance(raw.get("scenario"), dict) else raw
        else:
            payload = compare_scenarios(term, lineage_family=args.family or None)
        dest = Path(args.export_dir) if args.export_dir else (ROOT / "out" / "research")
        out = export_research_packet(payload, out_dir=dest, title=args.export_title or "hyperlex-research")
    elif mode == "schedule":
        # Risk-tier → advisory LIVE_EMERGENCE_SCAN / Hermes cron plan
        if getattr(args, "list_tiers", False):
            out = {
                "schema": "hyperlex.tier_policy_index.v1",
                "tiers": {k: {"cron": v["cron"], "interval_hours": v["interval_hours"], "max_queries": v["max_queries"]} for k, v in TIER_POLICY.items()},
                "brier": None,
                "provenance": "SPECULATIVE",
            }
        elif getattr(args, "tier", None):
            out = plan_scan_from_tier(str(args.tier), job_name=getattr(args, "job_name", None) or None)
        else:
            out = plan_scan_from_term(
                term,
                domain=domain,
                analysis_result=analysis,
                use_phase5=not bool(getattr(args, "no_phase5", False)),
            )
        if getattr(args, "schedule_out", None):
            written = write_scan_plan(out, out_dir=Path(args.schedule_out))
            out = {**out, "written": written}
    else:
        out = run_phase5_scenario(
            term,
            lineage_family=args.family or None,
            virality_hybrid=float(args.virality),
            memetic_score=float(args.memetic),
            hyperstition_stage=args.stage or None,
            domain=domain,
            analysis_result=analysis if not bool(getattr(args, "expand_terms", True)) else (
                # multi-term expand ignores bag analysis to avoid density-stack bias
                analysis if not term or " " not in term.strip() else None
            ),
            n_communities=int(args.communities),
            transmission_steps=int(args.steps),
            n_agents=int(args.agents),
            include_phylogeny=not bool(args.no_phylogeny),
            expand_terms=not bool(getattr(args, "no_expand", False)),
        )

    payload = {"ok": True, "command": "simulate", "mode": mode, "scenario": out}
    # assert never invents brier
    if out.get("brier") is not None:
        payload["ok"] = False
        payload["error"] = "simulation must keep brier null"
        _emit(payload)
        return 2
    # multi-term: nested scenarios must also keep brier null
    for nested in out.get("scenarios") or []:
        if isinstance(nested, dict) and nested.get("brier") is not None:
            payload["ok"] = False
            payload["error"] = "simulation must keep brier null"
            _emit(payload)
            return 2
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
        payload["written"] = args.out
    if not args.verbose and mode == "scenario":
        sc = dict(out)
        if sc.get("schema") == "hyperlex.phase5_multi_term.v1":
            # compact multi-term: summaries only unless --verbose
            sc.pop("scenarios", None)
            sc["scenarios_omitted"] = True
            sc["hint"] = "multi-term: one scenario per lexicon atom; --verbose or --out for full"
            payload["scenario"] = sc
            payload["terms"] = out.get("terms")
            payload["multi_term"] = True
        else:
            # compact CLI: drop full agent list / long trajectory tails
            if isinstance(sc.get("transmission"), dict):
                t = dict(sc["transmission"])
                traj = t.get("trajectory") or []
                t["trajectory"] = traj[:2] + ([{"_omitted_middle": len(traj) - 4}] if len(traj) > 4 else []) + traj[-2:]
                sc["transmission"] = t
            if isinstance(sc.get("multi_agent"), dict):
                m = dict(sc["multi_agent"])
                m.pop("agents", None)
                m["agents_omitted"] = True
                sc["multi_agent"] = m
            if isinstance(sc.get("phylogeny"), dict):
                p = dict(sc["phylogeny"])
                p.pop("nodes", None)
                p.pop("edges", None)
                p["graph_omitted"] = True
                sc["phylogeny"] = p
            payload["scenario"] = sc
            payload["hint"] = "pass --verbose for full trajectories; --out always writes full JSON"
    _emit(payload)
    return 0


def cmd_terms_split(args: argparse.Namespace) -> int:
    """Split free-text seed into atomic lexicon terms."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    from hyperlex.analysis.terms import per_term_lineage, split_seed_terms

    text = (getattr(args, "text_pos", None) or args.text or args.query or args.term or "").strip()
    if not text:
        _emit({"ok": False, "error": "pass text to split (positional or --text)"})
        return 2
    split = split_seed_terms(text, include_backfill=not bool(args.no_backfill))
    per = per_term_lineage(split.get("terms") or []) if not args.no_lineage else []
    _emit({
        "ok": True,
        "command": "terms-split",
        "split": split,
        "per_term": per,
        "note": "Each term is an independent lexicon atom — do not Phase-5 as one blended seed.",
        "brier": None,
    })
    return 0


def cmd_lineage_backprop(args: argparse.Namespace) -> int:
    """Non-mutating lineage rematch of historical receipts (backpropagation report)."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    from hyperlex.analysis.backprop import backpropagate_lineage

    receipt_dirs: List[str] = []
    if args.receipt_dir:
        receipt_dirs.append(args.receipt_dir)

    report = backpropagate_lineage(
        year=int(args.year),
        through=args.through or None,
        backfill_root=Path(args.root) if args.root else (ROOT / "data" / "backfill"),
        from_golden=bool(args.from_golden),
        from_archive=bool(args.from_archive),
        receipt_dirs=receipt_dirs or None,
        inputs=list(args.input or []) or None,
        repo_root=ROOT,
        include_home=bool(args.include_home),
        use_backfill=not bool(args.no_backfill),
    )
    # compact CLI: omit full rows unless verbose
    out_obj = dict(report)
    if not args.verbose:
        out_obj.pop("rows", None)
        out_obj["rows_omitted"] = True
        out_obj["hint"] = "pass --verbose for per-receipt rows; --out always writes full report"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        out_obj["written"] = args.out
    _emit({"ok": True, "command": "lineage-backprop", **out_obj})
    return 0


def cmd_ledger_stats(args: argparse.Namespace) -> int:
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    from hyperlex.receipt import ledger_stats

    ledger = Path(args.ledger) if args.ledger else pkg.default_ledger_path()
    stats = ledger_stats(path=ledger, limit=int(args.limit) if args.limit else 0)
    _emit({"ok": True, "command": "ledger-stats", **stats})
    return 0 if stats.get("chain_ok", True) else 2


def cmd_verify_receipt_ledger(args: argparse.Namespace) -> int:
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    ledger = Path(args.ledger) if args.ledger else pkg.default_ledger_path()
    chain = pkg.verify_ledger_chain(ledger)
    _emit({
        "ok": bool(chain.get("ok")),
        "command": "verify-receipt-ledger",
        "ledger_path": str(ledger),
        "chain": chain,
    })
    return 0 if chain.get("ok") else 2


def cmd_extract_forecasts(args: argparse.Namespace) -> int:
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    payload, load_error = _get_input_payload(args.input)
    if load_error:
        _emit({"ok": False, "error": load_error})
        return 2
    if payload is None:
        _emit({"ok": False, "error": "input required (analysis result or receipt JSON)"})
        return 2

    # Accept bare result or receipt-wrapped result
    result = payload
    receipt_ref = None
    if "analysis" not in result and isinstance(result.get("result"), dict):
        result = result["result"]
    if isinstance(payload.get("receipt"), dict):
        receipt_ref = {
            "integrity": payload["receipt"].get("integrity"),
            "path": str(args.input),
        }
    elif isinstance(result.get("receipt"), dict):
        receipt_ref = {
            "integrity": result["receipt"].get("integrity"),
            "path": str(args.input),
        }

    forecasts = pkg.extract_forecasts(result, receipt_ref=receipt_ref)
    log_path = None
    logged = 0
    if args.append_log:
        log_path = _resolve_log_path(args)
        for fc in forecasts:
            pkg.append_forecast(fc, path=log_path)
            logged += 1

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(forecasts, sort_keys=True, indent=2), encoding="utf-8")

    _emit({
        "ok": True,
        "command": "extract-forecasts",
        "n_forecasts": len(forecasts),
        "forecasts": forecasts,
        "log_path": str(log_path) if log_path else None,
        "logged": logged,
    })
    return 0


def _find_forecast_in_log(pkg, forecast_id: str, log_path: Path) -> Dict[str, Any] | None:
    from hyperlex.calibration.score_log import index_forecasts, read_log

    return index_forecasts(read_log(log_path)).get(forecast_id)


def cmd_settle(args: argparse.Namespace) -> int:
    """Operator settlement path: settle forecast → append score log → atomic score."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    forecast: Dict[str, Any] | None = None

    if args.forecast_file:
        payload, load_error = _get_input_payload(args.forecast_file)
        if load_error:
            _emit({"ok": False, "error": load_error})
            return 2
        if payload is None:
            _emit({"ok": False, "error": "empty forecast file"})
            return 2
        # file may be a single forecast, a list, or {forecasts: [...]}
        if "forecast_id" in payload and "probability" in payload:
            forecast = payload
        elif isinstance(payload.get("forecasts"), list):
            wanted = args.forecast_id
            for fc in payload["forecasts"]:
                if not wanted or fc.get("forecast_id") == wanted:
                    forecast = fc
                    break
        elif isinstance(payload, dict) and isinstance(payload.get("forecast"), dict):
            forecast = payload["forecast"]

    log_path = _resolve_log_path(args)

    if forecast is None and args.forecast_id:
        forecast = _find_forecast_in_log(pkg, args.forecast_id, log_path)

    if forecast is None:
        _emit({
            "ok": False,
            "error": "forecast not found; pass --forecast-file and/or --forecast-id present in score log",
        })
        return 2

    if args.forecast_id and forecast.get("forecast_id") != args.forecast_id:
        _emit({
            "ok": False,
            "error": f"forecast_id mismatch: file has {forecast.get('forecast_id')}, flag has {args.forecast_id}",
        })
        return 2

    decision = args.decision.upper()
    # Infer outcome from decision when not explicit
    if args.outcome is not None:
        outcome = float(args.outcome)
    elif decision == "TRUE":
        outcome = 1.0
    elif decision == "FALSE":
        outcome = 0.0
    else:
        # VOID / CONFLICT still need a placeholder 0.0; not scored
        outcome = 0.0

    try:
        result = pkg.settle_and_log(
            forecast,
            outcome_value=outcome,
            settlement_decision=decision,
            authority_kind=args.authority_kind,
            authority_ref=args.authority_ref or None,
            authority_note=args.authority_note or None,
            evidence_ref=args.evidence_ref or None,
            path=log_path,
        )
    except ValueError as exc:
        _emit({"ok": False, "error": str(exc)})
        return 2

    ledger = None
    if args.export_ledger and result["score"].get("status") == "SCORED":
        from hyperlex.calibration.export import to_brier_ledger_entry

        ledger = to_brier_ledger_entry(
            forecast,
            result["score"],
            settlement=result["settlement"],
        )

    _emit({
        "ok": True,
        "command": "settle",
        "log_path": str(log_path),
        "settlement": result["settlement"],
        "score": result["score"],
        "scorable": result["scorable"],
        "ledger_entry": ledger,
    })
    return 0


def cmd_score_series(args: argparse.Namespace) -> int:
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    log_path = _resolve_log_path(args)
    series = pkg.recompute_series(
        path=log_path,
        signal_key=args.signal_key or None,
        reference=args.reference,
    )

    mean_shift = None
    if args.mean_shift:
        from hyperlex.calibration.recalibrate import mean_shift_from_series

        mean_shift = mean_shift_from_series(series)

    chain = None
    if args.verify_chain:
        from hyperlex.calibration.score_log import verify_chain

        chain = verify_chain(log_path)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(series, sort_keys=True, indent=2), encoding="utf-8")

    _emit({
        "ok": True,
        "command": "score-series",
        "log_path": str(log_path),
        "series": series,
        "mean_shift": mean_shift,
        "chain": chain,
    })
    # Fail-closed: NOT_COMPUTABLE is still a successful recompute (no pairs yet)
    return 0


def cmd_verify_score_log(args: argparse.Namespace) -> int:
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    from hyperlex.calibration.score_log import verify_chain

    log_path = _resolve_log_path(args)
    chain = verify_chain(log_path)
    _emit({"ok": bool(chain.get("ok")), "command": "verify-score-log", "log_path": str(log_path), "chain": chain})
    return 0 if chain.get("ok") else 2


def cmd_validate(args: argparse.Namespace) -> int:
    payload, load_error = _get_input_payload(args.path)
    if load_error:
        _emit({"ok": False, "error": load_error})
        return 2

    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    schemas = pkg.schemas
    schema_name = "unknown"
    valid = False
    msg = "no schema matcher"

    if isinstance(payload, dict) and payload.get("receipt") is not None and payload.get("observed") is not None:
        schema_name = "receipt"
        valid, msg = schemas.validate_receipt(payload)
    elif isinstance(payload, dict) and set(["query", "source", "raw_signal", "extracted_terms"]).issubset(payload.keys()):
        schema_name = "ingest"
        valid, msg = schemas.validate_ingest(payload)
    elif isinstance(payload, dict) and all(k in payload for k in ["observed", "inferred", "speculative", "provenance"]):
        schema_name = "result"
        valid, msg = schemas.validate_result(payload)

    _emit({"ok": bool(valid), "schema": schema_name, "message": msg})
    return 0 if valid else 2


def cmd_receipt_verify(args: argparse.Namespace) -> int:
    payload, load_error = _get_input_payload(args.path)
    if load_error:
        _emit({"ok": False, "error": load_error})
        return 2

    receipt = payload.get("receipt") if isinstance(payload, dict) else None
    if not isinstance(receipt, dict):
        _emit({"ok": False, "error": "missing receipt block"})
        return 2
    expected = str(receipt.get("integrity", "")).strip()
    if not expected:
        _emit({"ok": False, "error": "receipt.integrity missing"})
        return 2

    canonical = json.dumps({k: payload[k] for k in payload if k != "receipt"}, sort_keys=True, separators=(",", ":"))
    actual = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
    ok = actual == expected
    _emit({"ok": ok, "path": str(args.path), "expected": expected, "actual": actual})
    return 0 if ok else 2


def cmd_smoke(_args: argparse.Namespace) -> int:
    # Minimal smoke command used by CI.
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "stage": "import", "error": err})
        return 2

    sample = pkg.detect_memetic_patterns("smoke test", ingest_source="mock", use_structured_ingest=False, validate=False)
    receipt_path = pkg.emit_receipt(
        sample,
        out_dir=ROOT / "out" / "smoke",
        validate=False,
        append_ledger=False,  # smoke should not pollute operator ledger
    )
    _emit({"ok": True, "stage": "smoke", "sample": sample["analysis"]["memetics"], "receipt": str(receipt_path)})
    return 0


def _load_scan_queries(args: argparse.Namespace) -> List[str]:
    queries: List[str] = []
    if getattr(args, "query", None):
        queries.append(str(args.query))
    if getattr(args, "queries", None):
        for part in str(args.queries).split(","):
            part = part.strip()
            if part:
                queries.append(part)
    if getattr(args, "config", None):
        cfg_path = Path(args.config)
        if not cfg_path.exists():
            # try relative to skill root
            alt = ROOT / args.config
            if alt.exists():
                cfg_path = alt
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("queries"), list):
                queries.extend(str(q) for q in data["queries"] if str(q).strip())
            elif isinstance(data, list):
                queries.extend(str(q) for q in data if str(q).strip())
    # dedupe preserve order
    seen = set()
    out: List[str] = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def cmd_scan(args: argparse.Namespace) -> int:
    """LIVE_EMERGENCE_SCAN — multi-query analyze for cron / autonomous monitoring."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    queries = _load_scan_queries(args)
    if not queries:
        # default pack
        default_cfg = ROOT / "examples" / "cron" / "scan-queries.json"
        if default_cfg.exists():
            data = json.loads(default_cfg.read_text(encoding="utf-8"))
            queries = list(data.get("queries") or [])
    if not queries:
        _emit({"ok": False, "error": "no queries; pass --query, --queries, or --config"})
        return 2

    requested = getattr(args, "source", None) or "mock"
    route = getattr(args, "route", None) or None
    source, resolved = _resolve_cli_source(args)
    results: List[Dict[str, Any]] = []
    n_forecasts = 0
    n_receipts = 0
    errors: List[Dict[str, str]] = []

    for q in queries:
        try:
            result = pkg.detect_memetic_patterns(
                query=q,
                ingest_source=requested,
                use_structured_ingest=True,
                validate=bool(args.validate),
                ingest_route=route,
            )
            receipt_path = None
            if args.receipt:
                out_dir = Path(args.receipt_dir) if args.receipt_dir else None
                ledger = Path(args.ledger) if args.ledger else None
                receipt_path = pkg.emit_receipt(
                    result,
                    out_dir=out_dir,
                    validate=bool(args.validate),
                    append_ledger=not args.no_ledger,
                    ledger_path=ledger,
                )
                result = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
                n_receipts += 1

            forecasts: List[Dict[str, Any]] = []
            if args.forecasts:
                receipt_ref = None
                if isinstance(result.get("receipt"), dict):
                    receipt_ref = {
                        "integrity": result["receipt"].get("integrity"),
                        "path": str(receipt_path) if receipt_path else None,
                    }
                forecasts = pkg.extract_forecasts(result, receipt_ref=receipt_ref)
                if args.append_log and forecasts:
                    log_path = _resolve_log_path(args)
                    for fc in forecasts:
                        pkg.append_forecast(fc, path=log_path)
                n_forecasts += len(forecasts)

            lineage = (result.get("analysis") or {}).get("lineage")
            results.append({
                "query": q,
                "receipt": str(receipt_path) if receipt_path else None,
                "lineage_family": (lineage or {}).get("family_id"),
                "lineage_confidence": (lineage or {}).get("confidence"),
                "n_forecasts": len(forecasts),
                "forecast_ids": [f.get("forecast_id") for f in forecasts],
                "brier": (result.get("provenance") or {}).get("brier"),
                "hyperstition_risk": (result.get("provenance") or {}).get("hyperstition_risk"),
            })
        except Exception as exc:
            errors.append({"query": q, "error": str(exc)})

    summary: Dict[str, Any] = {
        "ok": len(errors) == 0,
        "command": "scan",
        "rune": "LIVE_EMERGENCE_SCAN",
        "source": source,
        "route": resolved.get("route"),
        "n_queries": len(queries),
        "n_ok": len(results),
        "n_errors": len(errors),
        "n_receipts": n_receipts,
        "n_forecasts": n_forecasts,
        "results": results,
        "errors": errors,
        "note": "Brier remains null until operator settlement",
    }

    # Post-scan advisory: lineage coverage → recommended next scan cadence
    try:
        from hyperlex.simulation import aggregate_scan_risk

        summary["scan_risk_advisory"] = aggregate_scan_risk(results)
    except Exception as exc:  # fail-open — scan still succeeds
        summary["scan_risk_advisory"] = {
            "ok": False,
            "error": str(exc),
            "brier": None,
            "provenance": "SPECULATIVE",
        }

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, sort_keys=True, indent=2), encoding="utf-8")
        summary["out"] = str(out)

    _emit(summary)
    return 0 if summary["ok"] else 1


def cmd_risk_schedule(args: argparse.Namespace) -> int:
    """Advisory risk-tier → LIVE_EMERGENCE_SCAN / Hermes cron plan."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    from hyperlex.simulation import (
        TIER_POLICY,
        plan_scan_from_term,
        plan_scan_from_tier,
        write_scan_plan,
    )

    if args.list_tiers:
        out = {
            "ok": True,
            "command": "risk-schedule",
            "schema": "hyperlex.tier_policy_index.v1",
            "tiers": {
                k: {
                    "cron": v["cron"],
                    "interval_hours": v["interval_hours"],
                    "max_queries": v["max_queries"],
                    "source_recommend": v["source_recommend"],
                    "operator_note": v["operator_note"],
                }
                for k, v in TIER_POLICY.items()
            },
            "brier": None,
            "provenance": "SPECULATIVE",
        }
        _emit(out)
        return 0

    term = (args.term or args.query or "").strip()
    analysis = None
    if args.from_analyze and term:
        analysis = pkg.detect_memetic_patterns(
            query=term,
            ingest_source=args.source or "mock",
        )

    if args.tier:
        plan = plan_scan_from_tier(str(args.tier), job_name=args.job_name or None)
    elif term:
        plan = plan_scan_from_term(
            term,
            domain=args.domain or "general",
            analysis_result=analysis,
            use_phase5=not bool(args.no_phase5),
        )
    else:
        _emit({
            "ok": False,
            "error": "pass --tier LOW|MODERATE|ELEVATED|CRITICAL, or --term / --query",
            "brier": None,
        })
        return 2

    payload: Dict[str, Any] = {
        "ok": True,
        "command": "risk-schedule",
        "plan": plan,
        "brier": None,
        "note": "ADVISORY only — does not auto-register Hermes cron.",
    }
    if plan.get("brier") is not None:
        payload["ok"] = False
        payload["error"] = "schedule plan must keep brier null"
        _emit(payload)
        return 2

    if args.schedule_out or args.out_dir:
        dest = Path(args.schedule_out or args.out_dir)
        written = write_scan_plan(plan, out_dir=dest)
        payload["written"] = written

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")
        payload["out"] = args.out

    _emit(payload)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 scripts/hyperlex.py", description="Hyperlex Hermes skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="Validate package and manifest readiness")
    check_parser.set_defaults(func=cmd_check)

    doctor_parser = subparsers.add_parser("doctor", help="Deep Hermes-skill health check")
    doctor_parser.set_defaults(func=cmd_doctor)

    sources_parser = subparsers.add_parser(
        "sources",
        help="List ingest sources + routes (offline|live|default|glossary|social)",
    )
    sources_parser.add_argument("--route", default="", help="Preview resolve for a named route")
    sources_parser.add_argument("--source", default="", help="Preview resolve for a source alias")
    sources_parser.add_argument("--no-aliases", action="store_true", default=False)
    sources_parser.set_defaults(func=cmd_sources)

    commands_parser = subparsers.add_parser(
        "commands",
        help="Simplified command map (daily ops / calibration / research)",
    )
    commands_parser.set_defaults(func=cmd_commands)

    def _add_pipeline_args(p: argparse.ArgumentParser, *, default_route: str = "offline") -> None:
        p.add_argument("query_pos", nargs="?", default="", help="Query text (positional)")
        p.add_argument("--query", default="", help="Query text (flag form)")
        p.add_argument("--queries", default="", help="Comma-separated queries (each expands to atoms)")
        p.add_argument("--term", default="", help="Alias for --query")
        p.add_argument("--source", default="mock")
        p.add_argument(
            "--route",
            default=default_route,
            help="Operator route: offline|mock|default|live|glossary|social",
        )
        p.add_argument("--domain", default="general")
        p.add_argument("--no-expand", action="store_true", default=False, help="Do not split multi-term bags")
        p.add_argument("--no-receipt", action="store_true", default=False)
        p.add_argument("--no-forecasts", action="store_true", default=False)
        p.add_argument("--no-append-log", action="store_true", default=False)
        p.add_argument("--no-phase5", action="store_true", default=False, help="Skip Phase 5 risk digest")
        p.add_argument("--validate", action="store_true", default=False)
        p.add_argument("--log", default="")
        p.add_argument("--repo-log", action="store_true", default=False)
        p.add_argument("--receipt-dir", default="")
        p.add_argument("--verbose", action="store_true", default=False)
        p.add_argument("--out", default="")

    pipe_parser = subparsers.add_parser(
        "pipeline",
        help="AUTO backend: ingest → analyze → receipt → forecasts → phase5 risk (results packet)",
    )
    _add_pipeline_args(pipe_parser, default_route="offline")
    pipe_parser.set_defaults(func=cmd_pipeline, command_label="pipeline")

    ingest_parser = subparsers.add_parser(
        "ingest",
        help="AUTO backend by default (same as pipeline). Use --raw-only for signal-only ingest.",
    )
    ingest_parser.add_argument("query", nargs="?", default="", help="Query (positional)")
    ingest_parser.add_argument("--source", default="mock", help="Source or alias")
    ingest_parser.add_argument(
        "--route",
        default="",
        help="offline|live|… (default offline for auto pipeline; empty uses --source + HYPERLEX_OFFLINE)",
    )
    ingest_parser.add_argument("--queries", default="")
    ingest_parser.add_argument("--domain", default="general")
    ingest_parser.add_argument("--no-expand", action="store_true", default=False)
    ingest_parser.add_argument("--no-receipt", action="store_true", default=False)
    ingest_parser.add_argument("--no-forecasts", action="store_true", default=False)
    ingest_parser.add_argument("--no-append-log", action="store_true", default=False)
    ingest_parser.add_argument("--no-phase5", action="store_true", default=False)
    ingest_parser.add_argument("--validate", action="store_true", default=False)
    ingest_parser.add_argument("--log", default="")
    ingest_parser.add_argument("--repo-log", action="store_true", default=False)
    ingest_parser.add_argument("--receipt-dir", default="")
    ingest_parser.add_argument("--verbose", action="store_true", default=False)
    ingest_parser.add_argument(
        "--raw-only",
        action="store_true",
        default=False,
        help="Signal-only ingest (no analyze/receipt/forecasts)",
    )
    ingest_parser.add_argument(
        "--structured",
        action="store_true",
        default=True,
        help="With --raw-only: structured fingerprint (default on)",
    )
    ingest_parser.add_argument("--raw", action="store_true", default=False, help="Legacy raw string shape")
    ingest_parser.add_argument("--max-terms", type=int, default=8)
    ingest_parser.add_argument("--out", default="")
    ingest_parser.set_defaults(func=cmd_ingest, command_label="ingest")

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analysis only (no auto receipt). Prefer `pipeline` / `run` / `ingest` for full results.",
    )
    analyze_parser.add_argument("query_pos", nargs="?", default="", help="Query text (positional)")
    analyze_parser.add_argument("--query", default="", help="Query text (flag form)")
    analyze_parser.add_argument("--source", "--ingest-source", default="mock", dest="source")
    analyze_parser.add_argument(
        "--route",
        default="",
        help="Operator route: offline|mock|default|live|glossary|social",
    )
    analyze_parser.add_argument("--input", help="Optional ingest JSON payload")
    analyze_parser.add_argument(
        "--structured-ingest",
        dest="use_structured_ingest",
        action="store_true",
        default=True,
        help="Always on; kept for API compat",
    )
    analyze_parser.add_argument("--validate", action="store_true", default=False)
    analyze_parser.add_argument("--forecasts", action="store_true", default=False, help="Also extract calibration forecasts")
    analyze_parser.add_argument("--append-log", action="store_true", default=False, help="Append forecasts to score log")
    analyze_parser.add_argument("--log", default="", help="Score log path (default ~/.hyperlex/score_log.jsonl)")
    analyze_parser.add_argument("--repo-log", action="store_true", default=False, help="Use out/calibration/score_log.jsonl")
    analyze_parser.add_argument("--receipt", action="store_true", default=False, help="Emit receipt + append receipt ledger")
    analyze_parser.add_argument("--receipt-dir", default="", help="Directory for receipt JSON files")
    analyze_parser.add_argument("--ledger", default="", help="Receipt ledger path (default ~/.hyperlex/receipt_ledger.jsonl)")
    analyze_parser.add_argument("--no-ledger", action="store_true", default=False, help="Skip receipt ledger append")
    analyze_parser.add_argument("--out")
    analyze_parser.set_defaults(func=cmd_analyze)

    run_parser = subparsers.add_parser(
        "run",
        help="AUTO backend (alias of pipeline): ingest → full results packet",
    )
    _add_pipeline_args(run_parser, default_route="offline")
    run_parser.set_defaults(func=cmd_run, command_label="run")

    pending_parser = subparsers.add_parser(
        "pending",
        help="List open (unsettled) forecasts from score log",
    )
    pending_parser.add_argument("--log", default="")
    pending_parser.add_argument("--repo-log", action="store_true", default=False)
    pending_parser.add_argument("--limit", type=int, default=50)
    pending_parser.set_defaults(func=cmd_pending)

    emit_parser = subparsers.add_parser("emit-receipt", help="Emit receipt from analysis result JSON")
    emit_parser.add_argument("--input", required=True)
    emit_parser.add_argument("--out-dir", default="", help="Receipt directory (default ~/.hyperlex/receipts)")
    emit_parser.add_argument("--ledger", default="")
    emit_parser.add_argument("--no-ledger", action="store_true", default=False)
    emit_parser.add_argument("--validate", action="store_true", default=False)
    emit_parser.set_defaults(func=cmd_emit_receipt)

    list_parser = subparsers.add_parser("list-receipts", help="List receipt ledger index entries")
    list_parser.add_argument("--ledger", default="")
    list_parser.add_argument("--limit", type=int, default=50)
    list_parser.add_argument("--lineage-family", default="")
    list_parser.set_defaults(func=cmd_list_receipts)

    ld_parser = subparsers.add_parser("ledger-diff", help="Diff two receipt JSON snapshots")
    ld_parser.add_argument("--a", required=True, help="Receipt A JSON path")
    ld_parser.add_argument("--b", required=True, help="Receipt B JSON path")
    ld_parser.set_defaults(func=cmd_ledger_diff)

    ls_parser = subparsers.add_parser("ledger-stats", help="Aggregate stats over receipt ledger")
    ls_parser.add_argument("--ledger", default="")
    ls_parser.add_argument("--limit", type=int, default=0, help="0 = all entries")
    ls_parser.set_defaults(func=cmd_ledger_stats)

    ar_parser = subparsers.add_parser(
        "archive-export",
        help="Export sanitized run snapshot for Pages static history (docs/archive/runs/)",
    )
    ar_parser.add_argument("--out-dir", default="", help="Single-dir export (disables history unless --history)")
    ar_parser.add_argument("--archive-root", default="", help="Default: docs/archive")
    ar_parser.add_argument("--history", action="store_true", default=False, help="Write runs/<id>/ + catalog (+ latest)")
    ar_parser.add_argument("--no-history", action="store_true", default=False, help="Force single out-dir only")
    ar_parser.add_argument("--no-latest", action="store_true", default=False, help="Do not refresh latest/")
    ar_parser.add_argument("--ledger", default="")
    ar_parser.add_argument("--receipt-dir", default="", help="Directory of full receipt JSON files")
    ar_parser.add_argument("--include-home-receipts", action="store_true", default=False)
    ar_parser.add_argument("--include-golden", action="store_true", default=False)
    ar_parser.add_argument("--no-ledger-index", action="store_true", default=False)
    ar_parser.add_argument("--snapshot-id", default="")
    ar_parser.add_argument("--notes", default="", help="Free-text note stored on snapshot")
    ar_parser.add_argument("--phase5", default="", help="Path to phase5 scenario JSON to archive")
    ar_parser.set_defaults(func=cmd_archive_export)

    ac_parser = subparsers.add_parser(
        "archive-catalog",
        help="Rebuild docs/archive catalog + index for Pages run history",
    )
    ac_parser.add_argument("--archive-root", default="")
    ac_parser.set_defaults(func=cmd_archive_catalog)

    vs = subparsers.add_parser(
        "vector-seed",
        help="Seed vector DB (sqlite or chroma via --backend or HYPERLEX_VECTOR_BACKEND)",
    )
    vs.add_argument("--db", default="", help="Default: ~/.hyperlex/vector.db")
    vs.add_argument("--year", type=int, default=2026)
    vs.add_argument("--through", default="2026-08")
    vs.add_argument("--root", default="", help="data/backfill root")
    vs.add_argument("--receipt-dir", default="")
    vs.add_argument("--include-golden", action="store_true", default=False)
    vs.add_argument("--include-home", dest="include_home", action="store_true", default=True)
    vs.add_argument("--no-home", dest="include_home", action="store_false")
    vs.add_argument("--no-registry", action="store_true", default=False)
    vs.add_argument("--no-backfill", action="store_true", default=False)
    vs.add_argument("--no-receipts", action="store_true", default=False)
    vs.add_argument("--backend", default="", help="sqlite (default) or chroma")
    vs.set_defaults(func=cmd_vector_seed)

    vq = subparsers.add_parser("vector-search", help="Cosine search over vector DB (sqlite/chroma)")
    vq.add_argument("query", help="Query text")
    vq.add_argument("--db", default="")
    vq.add_argument("--kind", default="", help="term | receipt")
    vq.add_argument("--family", default="")
    vq.add_argument("--top-k", type=int, default=10)
    vq.add_argument("--min-score", type=float, default=0.15)
    vq.add_argument("--backend", default="", help="sqlite (default) or chroma")
    vq.set_defaults(func=cmd_vector_search)

    vst = subparsers.add_parser("vector-stats", help="Vector DB stats (sqlite or chroma)")
    vst.add_argument("--db", default="")
    vst.add_argument("--backend", default="", help="sqlite (default) or chroma")
    vst.set_defaults(func=cmd_vector_stats)

    lbf = subparsers.add_parser(
        "lineage-backfill",
        help="Load YTD slang backfill packs; inventory or merge into registry overlay",
    )
    lbf.add_argument("--year", type=int, default=2026)
    lbf.add_argument("--through", default="", help="Cap packs at YYYY-MM (e.g. 2026-08)")
    lbf.add_argument("--root", default="", help="data/backfill root (default: repo data/backfill)")
    lbf.add_argument("--list", action="store_true", default=False, help="List packs / inventory")
    lbf.add_argument("--inventory", action="store_true", default=False, help="Alias for --list")
    lbf.add_argument("--verbose", action="store_true", default=False, help="Include full term list / registry")
    lbf.add_argument("--out", default="", help="Write apply report JSON")
    lbf.set_defaults(func=cmd_lineage_backfill)

    sim_parser = subparsers.add_parser(
        "simulate",
        help="Phase 5: cultural transmission / multi-agent / hyperstition risk / phylogeny",
    )
    sim_parser.add_argument("--term", default="", help="Seed term / phrase")
    sim_parser.add_argument("--query", default="", help="Alias for --term")
    sim_parser.add_argument(
        "--mode",
        default="scenario",
        choices=[
            "scenario",
            "transmission",
            "agents",
            "risk",
            "phylogeny",
            "calibrate",
            "compare",
            "export",
            "schedule",
        ],
    )
    sim_parser.add_argument("--family", default="", help="lineage family_id")
    sim_parser.add_argument(
        "--domain",
        default="general",
        help="risk domain (markets|ai|politics|general) or phylogeny pack id (finance|ai-native|political|regional)",
    )
    sim_parser.add_argument(
        "--list-domains",
        action="store_true",
        default=False,
        help="With --mode phylogeny: list data/phylogeny packs",
    )
    sim_parser.add_argument("--list-scenarios", action="store_true", default=False)
    sim_parser.add_argument("--scenario", default="", help="Named multi-agent scenario id")
    sim_parser.add_argument("--golden", default="", help="Settled series JSON for calibrate")
    sim_parser.add_argument("--signal-key", default="", help="Filter pairs for calibrate")
    sim_parser.add_argument("--export-dir", default="", help="Research export directory")
    sim_parser.add_argument("--export-title", default="")
    sim_parser.add_argument("--input", default="", help="JSON payload for export mode")
    sim_parser.add_argument("--stage", default="", help="EMERGENT|ACTUALIZING for risk mode")
    sim_parser.add_argument("--virality", type=float, default=0.5)
    sim_parser.add_argument("--memetic", type=float, default=0.5)
    sim_parser.add_argument("--communities", type=int, default=6)
    sim_parser.add_argument("--agents", type=int, default=20)
    sim_parser.add_argument("--steps", type=int, default=12)
    sim_parser.add_argument("--from-analyze", action="store_true", default=False, help="Seed from mock analyze")
    sim_parser.add_argument("--source", default="mock")
    sim_parser.add_argument("--no-phylogeny", action="store_true", default=False)
    sim_parser.add_argument(
        "--tier",
        default="",
        help="With --mode schedule: direct tier LOW|MODERATE|ELEVATED|CRITICAL",
    )
    sim_parser.add_argument(
        "--list-tiers",
        action="store_true",
        default=False,
        help="With --mode schedule: list TIER_POLICY",
    )
    sim_parser.add_argument(
        "--schedule-out",
        default="",
        help="With --mode schedule: write job/queries/plan JSON to directory",
    )
    sim_parser.add_argument(
        "--job-name",
        default="",
        help="With --mode schedule: override Hermes job name",
    )
    sim_parser.add_argument(
        "--no-phase5",
        action="store_true",
        default=False,
        help="With --mode schedule: skip full Phase 5 when deriving risk from term",
    )
    sim_parser.add_argument(
        "--no-expand",
        action="store_true",
        default=False,
        help="Do not split multi-term seeds (force single blended scenario)",
    )
    sim_parser.add_argument("--verbose", action="store_true", default=False)
    sim_parser.add_argument("--out", default="")
    sim_parser.set_defaults(func=cmd_simulate)

    ts_parser = subparsers.add_parser(
        "terms-split",
        help="Split free-text into atomic lexicon terms (sigma | rizz | locked in)",
    )
    ts_parser.add_argument("text_pos", nargs="?", default="", help="Text to split")
    ts_parser.add_argument("--text", default="", help="Text to split (flag form)")
    ts_parser.add_argument("--query", default="")
    ts_parser.add_argument("--term", default="")
    ts_parser.add_argument("--no-backfill", action="store_true", default=False)
    ts_parser.add_argument("--no-lineage", action="store_true", default=False)
    ts_parser.set_defaults(func=cmd_terms_split)

    rs_parser = subparsers.add_parser(
        "risk-schedule",
        help="Advisory risk-tier → LIVE_EMERGENCE_SCAN / Hermes cron plan (does not auto-register)",
    )
    rs_parser.add_argument("--term", default="", help="Seed term for Phase 5 risk → plan")
    rs_parser.add_argument("--query", default="", help="Alias for --term")
    rs_parser.add_argument(
        "--tier",
        default="",
        choices=["", "LOW", "MODERATE", "ELEVATED", "CRITICAL", "low", "moderate", "elevated", "critical"],
        help="Direct tier (skips simulation)",
    )
    rs_parser.add_argument("--list-tiers", action="store_true", default=False, help="List TIER_POLICY")
    rs_parser.add_argument("--domain", default="general")
    rs_parser.add_argument("--from-analyze", action="store_true", default=False)
    rs_parser.add_argument("--source", default="mock")
    rs_parser.add_argument("--no-phase5", action="store_true", default=False)
    rs_parser.add_argument("--job-name", default="")
    rs_parser.add_argument(
        "--schedule-out",
        default="",
        help="Write job JSON + queries + plan under this directory",
    )
    rs_parser.add_argument("--out-dir", default="", help="Alias for --schedule-out")
    rs_parser.add_argument("--out", default="", help="Write full plan JSON to path")
    rs_parser.set_defaults(func=cmd_risk_schedule)

    lbp = subparsers.add_parser(
        "lineage-backprop",
        help="Non-mutating lineage rematch of historical receipts (backpropagation report)",
    )
    lbp.add_argument("--year", type=int, default=2026)
    lbp.add_argument("--through", default="", help="Cap backfill packs at YYYY-MM")
    lbp.add_argument("--root", default="", help="data/backfill root")
    lbp.add_argument("--from-golden", action="store_true", default=False)
    lbp.add_argument("--from-archive", action="store_true", default=False)
    lbp.add_argument("--include-home", action="store_true", default=False)
    lbp.add_argument("--receipt-dir", default="")
    lbp.add_argument("--input", action="append", default=[], help="Receipt JSON (repeatable)")
    lbp.add_argument("--no-backfill", action="store_true", default=False, help="Use base registry only")
    lbp.add_argument("--verbose", action="store_true", default=False)
    lbp.add_argument("--out", default="", help="Write full backprop report JSON")
    lbp.set_defaults(func=cmd_lineage_backprop)

    vrl_parser = subparsers.add_parser("verify-receipt-ledger", help="Verify receipt ledger hash chain")
    vrl_parser.add_argument("--ledger", default="")
    vrl_parser.set_defaults(func=cmd_verify_receipt_ledger)

    ef_parser = subparsers.add_parser("extract-forecasts", help="Extract forecasts from analysis result JSON")
    ef_parser.add_argument("--input", required=True, help="Analysis result or receipt JSON")
    ef_parser.add_argument("--append-log", action="store_true", default=False)
    ef_parser.add_argument("--log", default="")
    ef_parser.add_argument("--repo-log", action="store_true", default=False)
    ef_parser.add_argument("--out", default="")
    ef_parser.set_defaults(func=cmd_extract_forecasts)

    settle_parser = subparsers.add_parser("settle", help="Settle a forecast and append score log")
    settle_parser.add_argument("--forecast-id", default="", help="Forecast id (from log or file)")
    settle_parser.add_argument("--forecast-file", default="", help="JSON forecast object or {forecasts:[...]}")
    settle_parser.add_argument("--decision", required=True, choices=["TRUE", "FALSE", "VOID", "CONFLICT", "true", "false", "void", "conflict"])
    settle_parser.add_argument("--outcome", type=float, default=None, help="0.0 or 1.0 (default from decision)")
    settle_parser.add_argument("--authority-kind", default="operator", choices=["operator", "automated_rule", "external_oracle"])
    settle_parser.add_argument("--authority-ref", default="")
    settle_parser.add_argument("--authority-note", default="")
    settle_parser.add_argument("--evidence-ref", default="")
    settle_parser.add_argument("--export-ledger", action="store_true", default=False, help="Emit Abraxas-compatible BrierLedgerEntry")
    settle_parser.add_argument("--log", default="")
    settle_parser.add_argument("--repo-log", action="store_true", default=False)
    settle_parser.set_defaults(func=cmd_settle)

    ss_parser = subparsers.add_parser("score-series", help="Recompute Brier series from score log")
    ss_parser.add_argument("--signal-key", default="", help="Filter by signal_key")
    ss_parser.add_argument("--reference", default="climatology", choices=["climatology", "persistence"])
    ss_parser.add_argument("--mean-shift", action="store_true", default=False, help="Advisory mean-shift diagnostic")
    ss_parser.add_argument("--verify-chain", action="store_true", default=False)
    ss_parser.add_argument("--log", default="")
    ss_parser.add_argument("--repo-log", action="store_true", default=False)
    ss_parser.add_argument("--out", default="")
    ss_parser.set_defaults(func=cmd_score_series)

    vsl_parser = subparsers.add_parser("verify-score-log", help="Verify score log hash chain")
    vsl_parser.add_argument("--log", default="")
    vsl_parser.add_argument("--repo-log", action="store_true", default=False)
    vsl_parser.set_defaults(func=cmd_verify_score_log)

    validate_parser = subparsers.add_parser("validate", help="Validate artifact against runtime schema")
    validate_parser.add_argument("path")
    validate_parser.set_defaults(func=cmd_validate)

    verify_parser = subparsers.add_parser("verify-receipt", help="Verify receipt integrity")
    verify_parser.add_argument("path")
    verify_parser.set_defaults(func=cmd_receipt_verify)

    smoke_parser = subparsers.add_parser("smoke", help="Run fast smoke check")
    smoke_parser.set_defaults(func=cmd_smoke)

    scan_parser = subparsers.add_parser(
        "scan",
        help="LIVE_EMERGENCE_SCAN — multi-query analyze for cron/autonomous monitoring",
    )
    scan_parser.add_argument("--query", default="", help="Single query")
    scan_parser.add_argument("--queries", default="", help="Comma-separated queries")
    scan_parser.add_argument("--config", default="", help="JSON file with {queries: [...]}")
    scan_parser.add_argument("--source", default="mock")
    scan_parser.add_argument(
        "--route",
        default="",
        help="Operator route: offline|mock|default|live|glossary|social",
    )
    scan_parser.add_argument("--structured-ingest", dest="structured_ingest", action="store_true", default=True)
    scan_parser.add_argument("--validate", action="store_true", default=False)
    scan_parser.add_argument("--receipt", action="store_true", default=False)
    scan_parser.add_argument("--receipt-dir", default="")
    scan_parser.add_argument("--ledger", default="")
    scan_parser.add_argument("--no-ledger", action="store_true", default=False)
    scan_parser.add_argument("--forecasts", action="store_true", default=False)
    scan_parser.add_argument("--append-log", action="store_true", default=False)
    scan_parser.add_argument("--log", default="")
    scan_parser.add_argument("--repo-log", action="store_true", default=False)
    scan_parser.add_argument("--out", default="", help="Write scan summary JSON")
    scan_parser.add_argument("--json", action="store_true", default=True, help="JSON output (default)")
    scan_parser.set_defaults(func=cmd_scan)

    relay_parser = subparsers.add_parser("relay", help="Emit rune / signal-relay envelopes from analysis JSON")
    relay_parser.add_argument("--input", default="", help="Analysis result JSON")
    relay_parser.add_argument("--list-runes", action="store_true", default=False)
    relay_parser.add_argument("--no-signal", action="store_true", default=False)
    relay_parser.add_argument("--no-scan", action="store_true", default=False)
    relay_parser.add_argument("--forecasts", action="store_true", default=False, help="Also emit forecast rune envelope")
    relay_parser.add_argument("--out", default="")
    relay_parser.set_defaults(func=cmd_relay)

    sig_parser = subparsers.add_parser("signal", help="Build market_signal + forecast_pipeline packets")
    sig_parser.add_argument("--input", required=True, help="Analysis result JSON")
    sig_parser.add_argument("--domain", default="narrative")
    sig_parser.add_argument("--with-series", action="store_true", default=False)
    sig_parser.add_argument("--signal-key", default="")
    sig_parser.add_argument("--log", default="")
    sig_parser.add_argument("--repo-log", action="store_true", default=False)
    sig_parser.add_argument("--out", default="")
    sig_parser.set_defaults(func=cmd_signal)

    fb_parser = subparsers.add_parser("feedback", help="Hyperstition/series feedback for future forecast maps")
    fb_parser.add_argument("--signal-key", default="hyperstition.stage")
    fb_parser.add_argument("--log", default="")
    fb_parser.add_argument("--repo-log", action="store_true", default=False)
    fb_parser.set_defaults(func=cmd_feedback)

    diag_parser = subparsers.add_parser("diagram", help="Generate Mermaid diagrams from receipts/ledger")
    diag_parser.add_argument("--from-ledger", action="store_true", default=False, help="Use receipt ledger")
    diag_parser.add_argument("--from-golden", action="store_true", default=False, help="Use examples/receipts/golden")
    diag_parser.add_argument("--input", action="append", default=[], help="Receipt JSON (repeatable)")
    diag_parser.add_argument("--glob", default="", help="Glob of receipt JSON files")
    diag_parser.add_argument("--ledger", default="", help="Receipt ledger path")
    diag_parser.add_argument("--lineage-family", default="")
    diag_parser.add_argument("--limit", type=int, default=50)
    diag_parser.add_argument("--out-dir", default="", help="Write .mmd/.html bundle here")
    diag_parser.add_argument("--no-html", action="store_true", default=False)
    diag_parser.add_argument("--prefix", default="hyperlex")
    diag_parser.set_defaults(func=cmd_diagram)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = _build_parser()
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
