"""Automatic backend pipeline: ingest → results.

One call runs the full operator path without manual chaining:

  resolve route → (expand multi-term) → analyze → receipt → forecasts → score log
  → optional Phase 5 risk digest → result packet

Never auto-settles. Never invents Brier. Fail-open on optional side effects
(vector, phase5) so core analysis always returns.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .analysis import detect_memetic_patterns
from .analysis.terms import split_seed_terms
from .calibration.score_log import append_forecast, default_log_path
from .calibration.forecast import extract_forecasts
from .intake.sources import pick_source
from .receipt import emit_receipt


PIPELINE_SCHEMA = "hyperlex.pipeline_result.v1"


def _atom_list(query: str, *, expand_terms: bool) -> List[str]:
    q = (query or "").strip()
    if not q:
        return []
    if not expand_terms:
        return [q]
    split = split_seed_terms(q)
    terms = [str(t).strip() for t in (split.get("terms") or []) if str(t).strip()]
    return terms if terms else [q]


def run_one(
    query: str,
    *,
    route: Optional[str] = "offline",
    source: str = "mock",
    receipt: bool = True,
    forecasts: bool = True,
    append_log: bool = True,
    phase5: bool = True,
    domain: str = "general",
    log_path: Optional[Path | str] = None,
    receipt_dir: Optional[Path | str] = None,
    validate: bool = False,
) -> Dict[str, Any]:
    """Run full backend for a single atomic query. Returns one result unit."""
    source_canon, resolved = pick_source(source, route=route)
    unit: Dict[str, Any] = {
        "query": query,
        "source": source_canon,
        "route": resolved.get("route"),
        "requested_source": resolved.get("requested"),
        "ok": True,
        "brier": None,
        "steps": [],
    }

    try:
        result = detect_memetic_patterns(
            query=query,
            ingest_source=source_canon,
            use_structured_ingest=True,
            validate=validate,
            ingest_route=resolved.get("route"),
        )
        unit["steps"].append("analyze")
        unit["result"] = result
        unit["lineage_family"] = ((result.get("analysis") or {}).get("lineage") or {}).get("family_id")
        unit["primary_term"] = (result.get("analysis") or {}).get("primary_term") or query
        unit["ingest"] = {
            "source": (result.get("ingest") or result.get("provenance") or {}).get("ingest_source")
            or source_canon,
            "fingerprint_id": (
                ((result.get("provenance") or {}).get("source_fingerprint") or {}).get("fingerprint_id")
            ),
        }
    except Exception as exc:
        unit["ok"] = False
        unit["error"] = f"analyze failed: {exc}"
        return unit

    receipt_path = None
    if receipt:
        try:
            receipt_path = emit_receipt(
                result,
                out_dir=Path(receipt_dir) if receipt_dir else None,
                validate=validate,
                append_ledger=True,
            )
            unit["steps"].append("receipt")
            unit["receipt"] = str(receipt_path)
            # reload so forecasts can anchor to receipt block
            try:
                import json

                result = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
                unit["result"] = result
            except Exception:
                pass
        except Exception as exc:
            unit["receipt_error"] = str(exc)

    fcs: List[Dict[str, Any]] = []
    if forecasts:
        try:
            receipt_ref = None
            if isinstance(result.get("receipt"), dict):
                receipt_ref = {
                    "integrity": result["receipt"].get("integrity"),
                    "path": str(receipt_path) if receipt_path else None,
                }
            fcs = extract_forecasts(result, receipt_ref=receipt_ref)
            unit["steps"].append("forecasts")
            unit["forecasts"] = fcs
            unit["n_forecasts"] = len(fcs)
            unit["forecast_ids"] = [f.get("forecast_id") for f in fcs]
            if append_log and fcs:
                path = Path(log_path) if log_path else default_log_path()
                for fc in fcs:
                    append_forecast(fc, path=path)
                unit["steps"].append("score_log")
                unit["log_path"] = str(path)
        except Exception as exc:
            unit["forecast_error"] = str(exc)

    if phase5:
        try:
            from .simulation import run_phase5_scenario

            # single atomic — expand_terms False
            sc = run_phase5_scenario(
                query,
                domain=domain,
                analysis_result=result,
                include_phylogeny=False,
                expand_terms=False,
            )
            risk = sc.get("hyperstition_risk") or {}
            unit["phase5"] = {
                "schema": sc.get("schema"),
                "seed_term": sc.get("seed_term"),
                "risk_tier": risk.get("tier"),
                "risk_score": risk.get("risk_score"),
                "transmission_peak": (sc.get("transmission") or {}).get("summary", {}).get(
                    "peak_mean_adoption"
                ),
                "cascade_success": (sc.get("multi_agent") or {}).get("summary", {}).get(
                    "cascade_success"
                ),
                "brier": None,
                "provenance": "SPECULATIVE",
            }
            unit["risk_tier"] = risk.get("tier")
            unit["steps"].append("phase5")
        except Exception as exc:
            unit["phase5_error"] = str(exc)

    # provenance brier must stay null
    if (unit.get("result") or {}).get("provenance", {}).get("brier") is not None:
        unit["ok"] = False
        unit["error"] = "pipeline must keep provenance.brier null"

    return unit


def run_pipeline(
    query: str,
    *,
    route: Optional[str] = "offline",
    source: str = "mock",
    expand_terms: bool = True,
    receipt: bool = True,
    forecasts: bool = True,
    append_log: bool = True,
    phase5: bool = True,
    domain: str = "general",
    log_path: Optional[Path | str] = None,
    receipt_dir: Optional[Path | str] = None,
    validate: bool = False,
    queries: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """
    Automatic backend: ingest → full results packet.

    Multi-term free text expands into one unit per lexicon atom by default.
    """
    started = datetime.now(timezone.utc).isoformat()
    if queries:
        atoms: List[str] = []
        seen = set()
        for q in queries:
            for a in _atom_list(str(q), expand_terms=expand_terms):
                k = a.lower()
                if k not in seen:
                    seen.add(k)
                    atoms.append(a)
    else:
        atoms = _atom_list(query, expand_terms=expand_terms)

    if not atoms:
        return {
            "schema": PIPELINE_SCHEMA,
            "ok": False,
            "error": "empty query",
            "brier": None,
            "command": "pipeline",
        }

    units: List[Dict[str, Any]] = []
    for atom in atoms:
        units.append(
            run_one(
                atom,
                route=route,
                source=source,
                receipt=receipt,
                forecasts=forecasts,
                append_log=append_log,
                phase5=phase5,
                domain=domain,
                log_path=log_path,
                receipt_dir=receipt_dir,
                validate=validate,
            )
        )

    n_ok = sum(1 for u in units if u.get("ok"))
    n_forecasts = sum(int(u.get("n_forecasts") or 0) for u in units)
    n_receipts = sum(1 for u in units if u.get("receipt"))
    families = sorted({u.get("lineage_family") for u in units if u.get("lineage_family")})
    tiers = [u.get("risk_tier") for u in units if u.get("risk_tier")]

    # post-batch advisory from lineage coverage
    advisory = None
    try:
        from .simulation import aggregate_scan_risk

        rows = [
            {
                "query": u.get("query"),
                "lineage_family": u.get("lineage_family"),
            }
            for u in units
        ]
        advisory = aggregate_scan_risk(rows)
    except Exception as exc:
        advisory = {"ok": False, "error": str(exc), "brier": None}

    packet = {
        "schema": PIPELINE_SCHEMA,
        "ok": n_ok == len(units) and n_ok > 0,
        "command": "pipeline",
        "created_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "input": query if not queries else list(queries),
        "atoms": atoms,
        "n_atoms": len(atoms),
        "expand_terms": expand_terms,
        "route": route,
        "source": source,
        "domain": domain,
        "n_ok": n_ok,
        "n_errors": len(units) - n_ok,
        "n_receipts": n_receipts,
        "n_forecasts": n_forecasts,
        "families": families,
        "risk_tiers": tiers,
        "results": units,
        "scan_risk_advisory": advisory,
        "pending_hint": "pipeline never settles; run: pending → settle → score-series",
        "brier": None,
        "note": (
            "Automatic backend pipeline. Ingest→analyze→receipt→forecasts→score_log"
            + ("→phase5" if phase5 else "")
            + ". Brier remains null until operator settlement. Multi-term bags expand to atoms."
        ),
    }

    # single-atom convenience: hoist primary result to top level
    if len(units) == 1 and units[0].get("ok"):
        packet["result"] = units[0].get("result")
        packet["receipt"] = units[0].get("receipt")
        packet["forecasts"] = units[0].get("forecasts")
        packet["phase5"] = units[0].get("phase5")

    return packet
