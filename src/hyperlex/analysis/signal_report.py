"""signal_report — Companion LIVE_EMERGENCE_SCAN parity helpers.

Derives optional analysis fields from existing virality / memetics /
hyperstition / lineage / mutation blocks. Pure, fail-open, never emits Brier.
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
    """Map existing scores into Companion-style compression labels."""
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


def build_symbolic_roles(
    *,
    memetic: Optional[Dict[str, Any]] = None,
    lineage: Optional[Dict[str, Any]] = None,
    variation: Optional[Dict[str, Any]] = None,
    hyper_stage: Optional[str] = None,
) -> List[str]:
    """Derive multi-select symbolic roles from typology + lineage."""
    roles: List[str] = []
    m = memetic or {}
    primary = str(m.get("typology_primary") or m.get("typology") or "")
    fam = str((lineage or {}).get("family_id") or "")
    sense = str((variation or {}).get("sense") or "")
    stage = str(hyper_stage or "").upper()

    mapping = {
        "tactical_edge": ["Memetic Weapon", "Status Signal"],
        "risk_identity": ["Tribal Marker", "Belief Reinforcement"],
        "platform_agency": ["Attention Hook", "Dissociation Layer"],
        "labor_identity": ["Tribal Marker", "Irony Shield"],
        "status_radiation": ["Status Signal", "Emotional Compression"],
        "irony_inversion": ["Irony Shield", "Emotional Compression"],
        "kinship_address": ["Tribal Marker", "Ritual Phrase"],
        "imitation_spread": ["Attention Hook", "Memetic Weapon"],
    }
    for r in mapping.get(primary, []):
        if r not in roles:
            roles.append(r)

    if fam in ("brainrot-aura", "political-status"):
        for r in ("Irony Shield", "Emotional Compression"):
            if r not in roles:
                roles.append(r)
    if fam in ("betting-sharp", "crypto-degen"):
        for r in ("Memetic Weapon", "Belief Reinforcement"):
            if r not in roles:
                roles.append(r)
    if "status" in sense or "irony" in sense:
        if "Status Signal" not in roles:
            roles.append("Status Signal")
    if stage == "ACTUALIZING":
        if "Belief Reinforcement" not in roles:
            roles.append("Belief Reinforcement")

    if not roles:
        roles = ["Attention Hook"]
    return roles[:6]


def build_propagation_vector(
    *,
    lineage: Optional[Dict[str, Any]] = None,
    variation: Optional[Dict[str, Any]] = None,
    ingest_source: Optional[str] = None,
) -> List[str]:
    """Platform / demographic tags."""
    tags: List[str] = []
    fam = str((lineage or {}).get("family_id") or "")
    community = str((variation or {}).get("community") or "")
    src = str(ingest_source or "").lower()

    family_map = {
        "betting-sharp": ["X/Twitter", "Niche Internet"],
        "crypto-degen": ["X/Twitter", "Discord", "Niche Internet"],
        "ai-native": ["X/Twitter", "AI/Tech", "Reddit"],
        "brainrot-aura": ["TikTok", "X/Twitter", "Niche Internet"],
        "kinship-address": ["X/Twitter", "Discord"],
        "political-status": ["X/Twitter", "Reddit"],
        "gaming-meta": ["Discord", "Twitch", "X/Twitter"],
        "workplace-corp": ["LinkedIn", "X/Twitter"],
    }
    for t in family_map.get(fam, ["X/Twitter"]):
        if t not in tags:
            tags.append(t)

    if "ai" in community or "machine" in community:
        if "AI/Tech" not in tags:
            tags.append("AI/Tech")
    if src in ("x_search", "social", "live"):
        if "X/Twitter" not in tags:
            tags.append("X/Twitter")
    if not tags:
        tags = ["Niche Internet"]
    return tags[:6]


def build_signal_report(
    *,
    observed: str,
    inferred: str,
    speculative: str,
    mutation_prediction: Optional[Dict[str, Any]] = None,
    recommendation: Optional[str] = None,
) -> Dict[str, Any]:
    """Human-facing SIGNAL REPORT summary block."""
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
    recs.append("Filter high-virality attractors for provenance before forecasting ingest.")
    recs.append("Retain classic compression slang as high-utility tribal/emotional routing.")

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
    Mutate (and return) analysis with Companion parity fields.
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

        analysis["compression_metrics"] = build_compression_metrics(
            virality=virality,
            memetic=memetic,
            lineage=lineage,
            n_neologisms=len(neos),
            hyper_stage=hyper.get("loop_stage"),
        )
        analysis["symbolic_role"] = build_symbolic_roles(
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
        # Compact family tree stub when lineage present
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


def build_seed_header(
    *,
    ingest_source: Optional[str] = None,
    hyper_stage: Optional[str] = None,
) -> Dict[str, str]:
    """Lightweight SEED-style integrity header for provenance."""
    stage = str(hyper_stage or "").upper()
    entropy = "medium" if stage in ("ACTUALIZING", "EMERGENT") else "low"
    return {
        "status": "PASS",
        "determinism": "yes (rule-based + lineage registry + optional vector boost)",
        "provenance": f"hyperlex.analysis; ingest_source={ingest_source or 'unknown'}",
        "entropy_class": entropy,
        "capability_lane": "advisory",
    }
