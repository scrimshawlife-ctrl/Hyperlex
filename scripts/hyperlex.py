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
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


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
        import hyperlex

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
        except Exception:  # pragma: no cover
            return {"raw": path.read_text(encoding="utf-8")}, True, "ok"

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return (data or {}, bool(data), "ok")
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


def cmd_sources(_args: argparse.Namespace) -> int:
    sources = [
        {"name": "mock", "kind": "deterministic", "real": False, "description": "No network, deterministic fixture output"},
        {"name": "real", "kind": "web", "real": True, "description": "Action Network betting glossary"},
        {"name": "glossary", "kind": "web", "real": True, "description": "Action Network glossary alias"},
        {"name": "web", "kind": "web", "real": True, "description": "Action Network glossary alias"},
        {"name": "reddit", "kind": "web", "real": True, "description": "Reddit keyword search"},
        {"name": "urban", "kind": "web", "real": True, "description": "Urban Dictionary public API"},
        {"name": "wikipedia", "kind": "web", "real": True, "description": "Wikipedia page summary"},
        {"name": "x_search", "kind": "stub", "real": False, "description": "Placeholder X/Twitter adapter signal"},
        {"name": "firecrawl", "kind": "web", "real": True, "description": "Crawl4AI-backed web crawl signal"},
        {"name": "crawl4ai", "kind": "web", "real": True, "description": "Explicit Crawl4AI-backed web crawl signal"},
        {"name": "combined", "kind": "composed", "real": True, "description": "Combined real adapters with graceful fallback"},
    ]
    _emit({"ok": True, "sources": sources})
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
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, sort_keys=True, indent=2), encoding="utf-8")
    _emit({"ok": True, "command": "analyze", "result": result})
    return 0


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
    receipt_path = pkg.emit_receipt(sample, out_dir=ROOT / "out" / "smoke", validate=False)
    _emit({"ok": True, "stage": "smoke", "sample": sample["analysis"]["memetics"], "receipt": str(receipt_path)})
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 scripts/hyperlex.py", description="Hyperlex Hermes skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="Validate package and manifest readiness")
    check_parser.set_defaults(func=cmd_check)

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
    analyze_parser.add_argument("--out")
    analyze_parser.set_defaults(func=cmd_analyze)

    validate_parser = subparsers.add_parser("validate", help="Validate artifact against runtime schema")
    validate_parser.add_argument("path")
    validate_parser.set_defaults(func=cmd_validate)

    verify_parser = subparsers.add_parser("verify-receipt", help="Verify receipt integrity")
    verify_parser.add_argument("path")
    verify_parser.set_defaults(func=cmd_receipt_verify)

    smoke_parser = subparsers.add_parser("smoke", help="Run fast smoke check")
    smoke_parser.set_defaults(func=cmd_smoke)

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
