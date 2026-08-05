"""Hyperstition risk forecasting for real-world systems.

Composes stage, virality, transmission, and multi-agent cascade into a
SPECULATIVE risk packet. Never emits Brier; never auto-settles.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


_TIER_CUTS = (
    (0.75, "CRITICAL"),
    (0.55, "ELEVATED"),
    (0.35, "MODERATE"),
    (0.0, "LOW"),
)


def _tier(score: float) -> str:
    s = max(0.0, min(1.0, score))
    for cut, name in _TIER_CUTS:
        if s >= cut:
            return name
    return "LOW"


def forecast_hyperstition_risk(
    *,
    hyperstition_stage: Optional[str] = None,
    virality_hybrid: float = 0.0,
    virality_predicted: Optional[float] = None,
    lineage_confidence: Optional[float] = None,
    memetic_score: Optional[float] = None,
    transmission_peak: Optional[float] = None,
    transmission_reach: Optional[float] = None,
    agent_cascade_success: Optional[bool] = None,
    agent_adoption_rate: Optional[float] = None,
    domain: str = "general",
    seed_term: Optional[str] = None,
    lineage_family: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Composite hyperstition risk for operator / research review.

    All inputs optional; missing inputs contribute 0 with transparency.
    """
    stage = str(hyperstition_stage or "").upper()
    stage_score = 0.85 if stage == "ACTUALIZING" else (0.45 if stage == "EMERGENT" else 0.15)

    vh = max(0.0, min(1.0, float(virality_hybrid or 0.0)))
    vp = max(0.0, min(1.0, float(virality_predicted))) if virality_predicted is not None else vh
    lc = max(0.0, min(1.0, float(lineage_confidence or 0.0)))
    ms = max(0.0, min(1.0, float(memetic_score or 0.0)))
    tp = max(0.0, min(1.0, float(transmission_peak))) if transmission_peak is not None else None
    tr = max(0.0, min(1.0, float(transmission_reach))) if transmission_reach is not None else None
    ar = max(0.0, min(1.0, float(agent_adoption_rate))) if agent_adoption_rate is not None else None

    drivers: List[Dict[str, Any]] = [
        {"id": "hyperstition_stage", "weight": 0.28, "value": stage_score, "raw": stage or None},
        {"id": "virality_hybrid", "weight": 0.14, "value": vh},
        {"id": "virality_predicted", "weight": 0.12, "value": vp},
        {"id": "lineage_confidence", "weight": 0.10, "value": lc},
        {"id": "memetic_score", "weight": 0.08, "value": ms},
    ]
    if tp is not None:
        drivers.append({"id": "transmission_peak", "weight": 0.12, "value": tp})
    if tr is not None:
        drivers.append({"id": "transmission_reach", "weight": 0.08, "value": tr})
    if ar is not None:
        drivers.append({"id": "agent_adoption_rate", "weight": 0.08, "value": ar})
    if agent_cascade_success is True:
        drivers.append({"id": "agent_cascade_success", "weight": 0.10, "value": 1.0})
    elif agent_cascade_success is False:
        drivers.append({"id": "agent_cascade_success", "weight": 0.10, "value": 0.15})

    # normalize weights that are present
    wsum = sum(d["weight"] for d in drivers) or 1.0
    risk = sum(d["weight"] * d["value"] for d in drivers) / wsum
    risk = round(max(0.0, min(0.98, risk)), 3)
    tier = _tier(risk)

    # domain-specific note (not changing score hard)
    domain_notes = {
        "markets": "Narrative→price loops; confirm with settlement before acting.",
        "ai": "Model-culture loops; quality + agency framing may self-reinforce.",
        "politics": "Tribal signaling high mutation; risk of runaway irony.",
        "general": "Cross-domain abstract risk; map to a real system before action.",
    }

    # confidence in the *risk estimate* itself
    n_inputs = sum(
        1
        for x in (stage, vh, lc, ms, tp, tr, ar, agent_cascade_success)
        if x is not None and x != "" and x != 0.0
    )
    conf = round(min(0.72, 0.28 + 0.06 * n_inputs), 3)

    return {
        "schema": "hyperlex.hyperstition_risk.v1",
        "seed_term": seed_term,
        "lineage_family": lineage_family,
        "domain": domain,
        "risk_score": risk,
        "tier": tier,
        "confidence": conf,
        "drivers": drivers,
        "domain_note": domain_notes.get(domain, domain_notes["general"]),
        "action_hints": _action_hints(tier, stage),
        "provenance": "SPECULATIVE",
        "brier": None,
        "note": (
            "Forward-looking hyperstition risk composite. Not a settled forecast. "
            "Do not treat as Brier-eligible without operator settlement design."
        ),
    }


def _action_hints(tier: str, stage: str) -> List[str]:
    hints = [
        "Label claims OBSERVED/INFERRED/SPECULATIVE; this packet is SPECULATIVE.",
        "Do not invent Brier; settle forecasts only with operator authority.",
    ]
    if tier in ("ELEVATED", "CRITICAL"):
        hints.append("Increase scan frequency; archive receipts; prepare settlement criteria.")
    if stage == "ACTUALIZING":
        hints.append("Loop may already couple narrative to external confirmation — verify evidence.")
    if tier == "LOW":
        hints.append("Monitor only; transmission may remain niche.")
    return hints


def risk_from_analysis(
    result: Dict[str, Any],
    *,
    transmission: Optional[Dict[str, Any]] = None,
    multi_agent: Optional[Dict[str, Any]] = None,
    domain: str = "general",
) -> Dict[str, Any]:
    """Derive risk packet from a detect_memetic_patterns result (+ optional sims)."""
    analysis = result.get("analysis") or {}
    hyper = analysis.get("hyperstition") or {}
    vir = analysis.get("virality") or {}
    pred = vir.get("prediction") or {}
    lin = analysis.get("lineage") or {}
    mem = analysis.get("memetics") or {}
    tsum = (transmission or {}).get("summary") or {}
    asum = (multi_agent or {}).get("summary") or {}

    return forecast_hyperstition_risk(
        hyperstition_stage=hyper.get("loop_stage") or (result.get("provenance") or {}).get("hyperstition_risk"),
        virality_hybrid=float(vir.get("hybrid_score") or 0.0),
        virality_predicted=pred.get("predicted_hybrid"),
        lineage_confidence=lin.get("confidence"),
        memetic_score=mem.get("score"),
        transmission_peak=tsum.get("peak_mean_adoption"),
        transmission_reach=tsum.get("final_reach_fraction"),
        agent_cascade_success=asum.get("cascade_success"),
        agent_adoption_rate=asum.get("final_adoption_rate"),
        domain=domain,
        seed_term=(result.get("query") or analysis.get("seed_term")),
        lineage_family=lin.get("family_id"),
    )
