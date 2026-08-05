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


def cmd_sources(_args: argparse.Namespace) -> int:
    sources = [
        {"name": "mock", "kind": "deterministic", "real": False, "description": "No network, deterministic fixture output"},
        {"name": "real", "kind": "web", "real": True, "description": "Action Network betting glossary"},
        {"name": "glossary", "kind": "web", "real": True, "description": "Action Network glossary alias"},
        {"name": "glossary_expanded", "kind": "web", "real": True, "description": "Multi-glossary pack (AN + wiki slang + urban)"},
        {"name": "web", "kind": "web", "real": True, "description": "Action Network glossary alias"},
        {"name": "reddit", "kind": "web", "real": True, "description": "Reddit keyword search"},
        {"name": "urban", "kind": "web", "real": True, "description": "Urban Dictionary public API"},
        {"name": "wikipedia", "kind": "web", "real": True, "description": "Wikipedia page summary"},
        {"name": "x_search", "kind": "social", "real": True, "description": "X/Twitter via API bearer, xurl CLI, or structured stub"},
        {"name": "firecrawl", "kind": "web", "real": True, "description": "Crawl4AI-backed web crawl signal"},
        {"name": "crawl4ai", "kind": "web", "real": True, "description": "Explicit Crawl4AI-backed web crawl signal"},
        {"name": "combined", "kind": "composed", "real": True, "description": "glossary+urban+reddit+wiki+x+crawl4ai with graceful fallback"},
    ]
    _emit({"ok": True, "sources": sources})
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


def _build_ingest_result(pkg, args: argparse.Namespace) -> Dict[str, Any]:
    if args.structured:
        return pkg.fetch_ingest(query=args.query, source=args.source, structured=True, max_terms=args.max_terms)
    raw = pkg.ingest_signal(query=args.query, source=args.source)
    return {
        "query": args.query,
        "source": args.source,
        "raw_signal": raw,
        "raw_len": len(raw),
    }


def cmd_ingest(args: argparse.Namespace) -> int:
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    result = _build_ingest_result(pkg, args)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, sort_keys=True, indent=2), encoding="utf-8")
    _emit({"ok": True, "command": "ingest", "result": result})
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

    query = args.query
    source = args.source
    if payload is not None:
        query = query or payload.get("query", "")
        source = source or payload.get("source", source)

    if not query:
        query = "slang emergence"

    result = pkg.detect_memetic_patterns(
        query=query,
        ingest_source=source,
        use_structured_ingest=args.use_structured_ingest,
        validate=args.validate,
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

    payload_out: Dict[str, Any] = {"ok": True, "command": "analyze", "result": result}
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
    """Export sanitized long-term analysis archive (for docs/Pages)."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2

    from hyperlex.archive import export_analysis_archive

    out_dir = Path(args.out_dir) if args.out_dir else (ROOT / "docs" / "archive" / "latest")
    receipt_dirs: List[str] = []
    if args.receipt_dir:
        receipt_dirs.append(args.receipt_dir)
    if args.include_home_receipts:
        receipt_dirs.append(str(Path.home() / ".hyperlex" / "receipts"))
    if args.include_golden:
        receipt_dirs.append(str(ROOT / "examples" / "receipts" / "golden"))

    ledger = Path(args.ledger) if args.ledger else None
    result = export_analysis_archive(
        out_dir=out_dir,
        ledger_path=ledger,
        receipt_dirs=receipt_dirs,
        include_ledger_index=not args.no_ledger_index,
        snapshot_id=args.snapshot_id or None,
    )
    _emit({"ok": True, "command": "archive-export", **result})
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

    source = args.source or "mock"
    results: List[Dict[str, Any]] = []
    n_forecasts = 0
    n_receipts = 0
    errors: List[Dict[str, str]] = []

    for q in queries:
        try:
            result = pkg.detect_memetic_patterns(
                query=q,
                ingest_source=source,
                use_structured_ingest=bool(getattr(args, "structured_ingest", False)),
                validate=bool(args.validate),
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

    summary = {
        "ok": len(errors) == 0,
        "command": "scan",
        "rune": "LIVE_EMERGENCE_SCAN",
        "source": source,
        "n_queries": len(queries),
        "n_ok": len(results),
        "n_errors": len(errors),
        "n_receipts": n_receipts,
        "n_forecasts": n_forecasts,
        "results": results,
        "errors": errors,
        "note": "Brier remains null until operator settlement",
    }

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, sort_keys=True, indent=2), encoding="utf-8")
        summary["out"] = str(out)

    _emit(summary)
    return 0 if summary["ok"] else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 scripts/hyperlex.py", description="Hyperlex Hermes skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="Validate package and manifest readiness")
    check_parser.set_defaults(func=cmd_check)

    doctor_parser = subparsers.add_parser("doctor", help="Deep Hermes-skill health check")
    doctor_parser.set_defaults(func=cmd_doctor)

    sources_parser = subparsers.add_parser("sources", help="List supported ingest sources")
    sources_parser.set_defaults(func=cmd_sources)

    ingest_parser = subparsers.add_parser("ingest", help="Run ingest only")
    ingest_parser.add_argument("query")
    ingest_parser.add_argument("--source", default="mock")
    ingest_parser.add_argument("--structured", action="store_true", default=False)
    ingest_parser.add_argument("--max-terms", type=int, default=8)
    ingest_parser.add_argument("--out", default="")
    ingest_parser.set_defaults(func=cmd_ingest)

    analyze_parser = subparsers.add_parser("analyze", help="Run analysis")
    analyze_parser.add_argument("--query")
    analyze_parser.add_argument("--source", "--ingest-source", default="mock", dest="source")
    analyze_parser.add_argument("--input", help="Optional ingest JSON payload")
    analyze_parser.add_argument("--structured-ingest", dest="use_structured_ingest", action="store_true", default=False)
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
        help="Export sanitized analysis archive for long-term review / GitHub Pages",
    )
    ar_parser.add_argument("--out-dir", default="", help="Default: docs/archive/latest")
    ar_parser.add_argument("--ledger", default="")
    ar_parser.add_argument("--receipt-dir", default="", help="Directory of full receipt JSON files")
    ar_parser.add_argument("--include-home-receipts", action="store_true", default=False)
    ar_parser.add_argument("--include-golden", action="store_true", default=False)
    ar_parser.add_argument("--no-ledger-index", action="store_true", default=False)
    ar_parser.add_argument("--snapshot-id", default="")
    ar_parser.set_defaults(func=cmd_archive_export)

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
    scan_parser.add_argument("--structured-ingest", dest="structured_ingest", action="store_true", default=False)
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
