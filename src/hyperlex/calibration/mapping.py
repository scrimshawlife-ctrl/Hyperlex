"""Versioned signal → probability mappings."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

MAPPING_VERSION = "v1"

# Discrete map for hyperstition stage (explicit, not a continuous score)
HYPERSTITION_STAGE_PROB = {
    "EMERGENT": 0.35,
    "ACTUALIZING": 0.70,
}


def map_lineage_confidence(lineage: Optional[Dict[str, Any]]) -> Optional[Tuple[float, Dict[str, Any]]]:
    if not lineage or "confidence" not in lineage:
        return None
    conf = float(lineage["confidence"])
    if not 0.0 <= conf <= 1.0:
        return None
    ctx = {
        "family_id": lineage.get("family_id"),
        "matched_terms": lineage.get("matched_terms"),
        "branch_operator": lineage.get("branch_operator"),
    }
    return conf, ctx


def map_virality(virality: Optional[Dict[str, Any]]) -> Optional[Tuple[float, Dict[str, Any]]]:
    if not virality or "hybrid_score" not in virality:
        return None
    score = float(virality["hybrid_score"])
    if not 0.0 <= score <= 1.0:
        return None
    return score, {"velocity": virality.get("velocity"), "acceleration": virality.get("acceleration")}


def map_hyperstition(hyper: Optional[Dict[str, Any]]) -> Optional[Tuple[float, Dict[str, Any]]]:
    if not hyper:
        return None
    stage = str(hyper.get("loop_stage", "")).upper()
    if stage not in HYPERSTITION_STAGE_PROB:
        return None
    return HYPERSTITION_STAGE_PROB[stage], {"loop_stage": stage, "mechanism": hyper.get("mechanism")}


def available_mappings() -> Dict[str, str]:
    return {
        "lineage.confidence": "analysis.lineage.confidence as f; target=lineage.family_confirmed",
        "virality.hybrid_score": "analysis.virality.hybrid_score as f; target=uptake.observed",
        "hyperstition.stage": "discrete stage map; target=hyperstition.loop_confirmed",
    }
