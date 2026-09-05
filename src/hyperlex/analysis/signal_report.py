"""signal_report — optional analysis enrichment for Hyperlex results.

Derives compression metrics, typology tags, propagation tags, and a compact
human summary from existing virality / memetics / hyperstition / lineage /
mutation blocks. Pure, fail-open, never emits Brier.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _level(score: float) -> str:
    if score >= 0.72:
        return "High"
    if score >= 0.42:
        return "Medium"
    return "Low"


def build_compression_metrics(
    *,
    virality: Optional[Dict[str, Any]] = None,
    memetic: Optional[Dict[str, Any]] = None,
    lineage: Optional[Dict[str, Any]] = None,
    n_neologisms: int = 0,
    hyper_stage: Optional[str] = None,
) -> Dict[str, str]:
    """Map existing scores into compact density labels."""
    v = virality or {}
    m = memetic or {}
    hybrid = float(v.get("hybrid_score") or 0.0)
    pred = (v.get("prediction") or {}).get("predicted_hybrid")
    if isinstance(pred, (int, float)):
        hybrid = max(hybrid, float(pred))
    mem_score = float(m.get("score") or 0.0)
    conf = float((lineage or {}).get("confidence") or 0.0)
    stage = str(hyper_stage or "").upper()

    semantic = min(1.0, 0.35 + 0.12 * min(5, n_neologisms) + 0.25 * conf)
    emotional = min(1.0, mem_score * 0.85 + (0.15 if stage in ("ACTUALIZING", "EMERGENT") else 0.0))
    virality_p = hybrid
    identity = min(1.0, conf * 0.7 + mem_score * 0.3)
    efficiency = min(1.0, 0.4 + 0.15 * min(4, n_neologisms) + 0.2 * (1.0 if conf >= 0.42 else 0.0))
    drift = 0.55 if stage == "ACTUALIZING" else (0.35 if stage == "EMERGENT" else 0.2)
    if hybrid > 0.7:
        drift = min(1.0, drift + 0.15)

    return {
        "semantic_density": _level(semantic),
        "emotional_density": _level(emotional),
        "virality_potential": _level(virality_p),
        "identity_signaling_strength": _level(identity),
        "compression_efficiency": _level(efficiency),
        "drift_probability": _level(drift),
    }


def build_typology_tags(
    *,
    memetic: Optional[Dict[str, Any]] = None,
    lineage: Optional[Dict[str, Any]] = None,
    variation: Optional[Dict[str, Any]] = None,
    hyper_stage: Optional[str] = None,
) -> List[str]:
    """
    Multi-select tags aligned to Hyperlex typology IDs + drivers.

    Prefer existing typology vocabulary over external role labels.
    """
    tags: List[str] = []
    m = memetic or {}
    primary = str(m.get("typology_primary") or m.get("typology") or "")
    scores = m.get("typology_scores") or {}
    fam = str((lineage or {}).get("family_id") or "")
    drivers = list((variation or {}).get("drivers") or [])
    stage = str(hyper_stage or "").upper()

    if primary and primary not in ("one_off", ""):
        tags.append(primary)

    for tid, sc in sorted(scores.items(), key=lambda kv: -float(kv[1] or 0)):
        if tid == primary:
            continue
        if float(sc or 0) >= 0.45 and tid not in tags:
            tags.append(str(tid))

    if fam and fam not in tags:
        tags.append(f"lineage:{fam}")

    for d in drivers:
        if d and d not in tags:
            tags.append(str(d))

    if stage == "ACTUALIZING" and "hyperstition_actualizing" not in tags:
        tags.append("hyperstition_actualizing")
    elif stage == "EMERGENT" and "hyperstition_emergent" not in tags:
        tags.append("hyperstition_emergent")

    if not tags:
        tags = ["imitation_spread"]
    return tags[:8]


def build_symbolic_roles(*args: Any, **kwargs: Any) -> List[str]:
    return build_typology_tags(*args, **kwargs)


def build_propagation_vector(
    *,
    lineage: Optional[Dict[str, Any]] = None,
    variation: Optional[Dict[str, Any]] = None,
    ingest_source: Optional[str] = None,
) -> List[str]:
    """Platform / community tags derived from lineage + variation + source."""
    tags: List[str] = []
    fam = str((lineage or {}).get("family_id") or "")
    community = str((variation or {}).get("community") or "")
    src = str(ingest_source or "").lower()

    family_map = {
        "betting-sharp": ["x_twitter", "niche"],
        "crypto-degen": ["x_twitter", "discord", "niche"],
        "ai-native": ["x_twitter", "ai_tech", "reddit"],
        "brainrot-aura": ["tiktok", "x_twitter", "niche"],
        "kinship-address": ["x_twitter", "discord"],
        "political-status": ["x_twitter", "reddit"],
        "gaming-meta": ["discord", "twitch", "x_twitter"],
        "workplace-corp": ["linkedin", "x_twitter"],
    }
    for t in family_map.get(fam, ["x_twitter"]):
        if t not in tags:
            tags.append(t)

    if "ai" in community or "machine" in community:
        if "ai_tech" not in tags:
            tags.append("ai_tech")
    if src in ("x_search", "social", "live"):
        if "x_twitter" not in tags:
            tags.append("x_twitter")
    if not tags:
        tags = ["niche"]
    return tags[:6]


def build_signal_report(
    *,
    observed: str,
    inferred: str,
    speculative: str,
    mutation_prediction: Optional[Dict[str, Any]] = None,
    recommendation: Optional[str] = None,
) -> Dict[str, Any]:
    """Compact human-facing summary block (O/I/S + mutations + recs)."""
    gens: List[Any] = []
    mp = mutation_prediction or {}
    for c in (mp.get("candidates") or [])[:5]:
        if isinstance(c, dict) and c.get("form"):
            gens.append({
                "form": c.get("form"),
                "operator": c.get("operator"),
                "confidence": c.get("confidence"),
                "provenance": c.get("provenance", "SPECULATIVE"),
            })
    recs: List[str] = []
    if recommendation:
        recs.append(str(recommendation))
    recs.append("Route high-virality attractors through receipt + forecast extract before settlement.")
    recs.append("Prefer lineage-matched atoms for calibration series continuity.")

    return {
        "observed": observed,
        "inferred": inferred,
        "speculative": speculative,
        "generated_mutations": gens,
        "actionable_recommendations": recs[:5],
    }


def attach_signal_report_fields(
    analysis: Dict[str, Any],
    *,
    observed: str,
    inferred: str,
    speculative: str,
    recommendation: Optional[str] = None,
    ingest_source: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Attach optional enrichment fields onto analysis.
    Fail-open: never raises; leaves existing keys untouched on error.
    """
    try:
        virality = analysis.get("virality") or {}
        memetic = analysis.get("memetics") or {}
        lineage = analysis.get("lineage")
        variation = analysis.get("semantic_variation") or {}
        hyper = analysis.get("hyperstition") or {}
        neos = analysis.get("neologisms") or []
        mp = analysis.get("mutation_prediction")

        if "mutation_trace" not in analysis:
            from .mutation_trace_attach import attach_mutation_trace
            attach_mutation_trace(
                analysis,
                query=str(observed or ""),
                observed="",
                ingest_source=str(ingest_source or "analyze"),
            )

        analysis["compression_metrics"] = build_compression_metrics(
            virality=virality,
            memetic=memetic,
            lineage=lineage,
            n_neologisms=len(neos),
            hyper_stage=hyper.get("loop_stage"),
        )
        analysis["symbolic_role"] = build_typology_tags(
            memetic=memetic,
            lineage=lineage,
            variation=variation,
            hyper_stage=hyper.get("loop_stage"),
        )
        analysis["propagation_vector"] = build_propagation_vector(
            lineage=lineage,
            variation=variation,
            ingest_source=ingest_source,
        )
        if lineage and lineage.get("family_id"):
            analysis["slang_family_tree"] = {
                "root": lineage.get("family_id"),
                "matched_terms": lineage.get("matched_terms") or [],
                "branch_operator": lineage.get("branch_operator"),
                "confidence": lineage.get("confidence"),
                "diagram_ref": lineage.get("diagram_ref"),
                "provenance": "INFERRED",
            }
        analysis["signal_report"] = build_signal_report(
            observed=observed,
            inferred=inferred,
            speculative=speculative,
            mutation_prediction=mp,
            recommendation=recommendation,
        )
    except Exception:
        pass
    return analysis


def build_integrity_header(
    *,
    ingest_source: Optional[str] = None,
    hyper_stage: Optional[str] = None,
) -> Dict[str, str]:
    """Compact integrity note for provenance (optional)."""
    stage = str(hyper_stage or "").upper()
    elevated = stage in ("ACTUALIZING", "EMERGENT")
    risk = "elevated" if elevated else "baseline"
    status = "PARTIAL" if elevated else "PASS"
    return {
        "status": status,
        "determinism": "rule_based_lineage_vector",
        "provenance": f"ingest={ingest_source or 'unknown'};stage={stage or 'none'}",
        "entropy_class": "high" if elevated else "medium",
        "capability_lane": "advisory",
        "method": "rule_based_lineage_vector",
        "ingest_source": ingest_source or "unknown",
        "hyperstition_stage": stage or "none",
        "risk_band": risk,
        "authority": "advisory",
    }


def build_seed_header(*args: Any, **kwargs: Any) -> Dict[str, str]:
    return build_integrity_header(*args, **kwargs)
