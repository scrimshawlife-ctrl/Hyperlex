#!/usr/bin/env python3
"""End-to-end Hyperlex Hermes skill case study (offline mock).

Usage:
  python3 scripts/run_case_study.py --out-dir out/case-study
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
# Prefer package src over scripts/ (avoids import hyperlex → scripts/hyperlex.py)
_src = str(SRC)
if _src in sys.path:
    sys.path.remove(_src)
sys.path.insert(0, _src)
# Drop shadowed script module if already loaded
if "hyperlex" in sys.modules:
    mod = sys.modules["hyperlex"]
    mf = getattr(mod, "__file__", "") or ""
    if mf.endswith("scripts/hyperlex.py"):
        del sys.modules["hyperlex"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Hyperlex e2e mock case study")
    ap.add_argument("--out-dir", default=str(ROOT / "out" / "case-study"))
    ap.add_argument("--query", default="nerf buff meta sweaty skill issue smurf")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    from hyperlex import (
        detect_memetic_patterns,
        emit_receipt,
        extract_forecasts,
        build_market_signal,
        build_forecast_pipeline,
        relay_from_result,
        relay_forecasts,
    )
    from hyperlex.diagrams import diagram_from_receipt_files, write_diagram_bundle

    result = detect_memetic_patterns(query=args.query, ingest_source="mock", validate=False)
    assert result["provenance"].get("brier") is None

    receipt_path = emit_receipt(
        result,
        out_dir=out / "receipts",
        append_ledger=False,
    )
    # reload with receipt block
    result = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    forecasts = extract_forecasts(result)
    envelopes = relay_from_result(result) + [relay_forecasts(forecasts)]
    market = build_market_signal(result, domain="gaming")
    pipeline = build_forecast_pipeline(result, forecasts=forecasts, market_signal=market)

    (out / "analyze.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    (out / "forecasts.json").write_text(json.dumps(forecasts, indent=2, sort_keys=True), encoding="utf-8")
    (out / "envelopes.json").write_text(json.dumps(envelopes, indent=2, sort_keys=True), encoding="utf-8")
    (out / "signal.json").write_text(
        json.dumps({"market_signal": market, "forecast_pipeline": pipeline}, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    diagrams = diagram_from_receipt_files([receipt_path])
    written = write_diagram_bundle(diagrams, out / "diagrams", html=True, prefix="case")

    summary = {
        "ok": True,
        "query": args.query,
        "receipt": str(receipt_path),
        "lineage": (result.get("analysis") or {}).get("lineage", {}).get("family_id"),
        "typology": (result.get("analysis") or {}).get("memetics", {}).get("typology_primary"),
        "n_forecasts": len(forecasts),
        "brier": result["provenance"].get("brier"),
        "virality_prediction": (result.get("analysis") or {}).get("virality", {}).get("prediction", {}).get(
            "predicted_hybrid"
        ),
        "diagrams": list(written.keys()),
        "out_dir": str(out),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
