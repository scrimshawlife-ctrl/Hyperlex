"""Encoder geometry repair for Classification v2.

Boundaries structure the supervised contrastive loss. Family logits stay on the
learned residual head. This module does not train, fetch, or read the evaluation
reserve.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from .classification_v2 import (
    ACTIVE_FAMILY_VOCABULARY,
    ClassificationContractError,
    canonical_json,
    sha256_text,
)
from .classification_v2_boundaries import (
    BOUNDARY_RULE,
    BOUNDARY_SCHEMA,
    COLLISION_COSINE,
    NEAREST_COMPETITORS,
    SUPPORT_SPARSE,
    assess_boundary_artifact,
)
from .classification_v2_prototype import _f32_round, _unit

REPAIR_SCHEMA = "hyperlex.classification.v2.geometry_repair.v1"
REPAIR_RULE = "HYPERLEX_FAMILY_GEOMETRY_REPAIR_V1"
GEOMETRY_TAU = 0.10
LAMBDA_GEOMETRY = 0.5
HARD_NEGATIVE_MULTIPLIER = 2.0
CANONICAL_LOGITS = "learned_residual"
REJECTED_LOGITS = "frozen_prototype_fusion"
BOUNDARY_SHA = "0ca6f34ce1abf68388e443371672ca36e16028079a175b6775e1968900e1c52f"
SEPARATION_SHA = "ab698d342d2d276f81d4baf3fed609bb6f8bf88cd6810bb1d1998c5e409f63c3"
PRIOR_ACTIVE_FAMILY_MACRO = 0.1960828268105939
PRIOR_PROTOTYPE_FAMILY_MACRO = 0.041352657004830914
PRIOR_NEW_FAMILY_F1_GT_0 = 3


def repair_contract() -> dict[str, Any]:
    return {
        "boundary_rule": BOUNDARY_RULE,
        "canonical_logits": CANONICAL_LOGITS,
        "hard_negative_count": NEAREST_COMPETITORS,
        "hard_negative_multiplier": HARD_NEGATIVE_MULTIPLIER,
        "hard_negatives": "sealed_nearest_competing_families",
        "jev": "OFF",
        "lambda_geometry": LAMBDA_GEOMETRY,
        "last_trainable": 2,
        "rejected_logits": REJECTED_LOGITS,
        "rule": REPAIR_RULE,
        "schema": REPAIR_SCHEMA,
        "tau": GEOMETRY_TAU,
        "train_encoder": True,
    }


def hard_negatives_from_boundaries(boundaries: Mapping[str, Any]) -> dict[str, list[str]]:
    """Nearest competing families from the sealed artifact. No evaluation mining."""
    nearest = boundaries.get("nearest_competitors")
    if not isinstance(nearest, dict):
        raise ClassificationContractError("FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", "nearest")
    chosen: dict[str, list[str]] = {}
    for family in ACTIVE_FAMILY_VOCABULARY:
        rows = nearest.get(family)
        if not isinstance(rows, list) or len(rows) < NEAREST_COMPETITORS:
            raise ClassificationContractError("FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", family)
        names = [str(item["family"]) for item in rows[:NEAREST_COMPETITORS]]
        if family in names or len(set(names)) != NEAREST_COMPETITORS:
            raise ClassificationContractError("FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", family)
        if any(name not in ACTIVE_FAMILY_VOCABULARY for name in names):
            raise ClassificationContractError("FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", family)
        chosen[family] = names
    return chosen


def sparse_families_from_boundaries(boundaries: Mapping[str, Any]) -> list[str]:
    sparse = []
    for family in boundaries.get("families") or []:
        if family.get("support_status") == SUPPORT_SPARSE:
            sparse.append(str(family["family"]))
    return sparse


def flatten_anchors(boundaries: Mapping[str, Any]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for family in boundaries.get("families") or []:
        name = str(family["family"])
        for anchor in family.get("anchors") or []:
            vector = _f32_round(_unit(anchor["vector"]))
            flat.append(
                {
                    "anchor_id": str(anchor["anchor_id"]),
                    "family": name,
                    "support_count": int(anchor["support_count"]),
                    "vector": vector,
                }
            )
    if not flat:
        raise ClassificationContractError("FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", "anchors")
    names = {item["family"] for item in flat}
    if names != set(ACTIVE_FAMILY_VOCABULARY):
        raise ClassificationContractError("FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", "coverage")
    return flat


def denominator_anchor_weights(
    family: str,
    anchors: Sequence[Mapping[str, Any]],
    hard_negatives: Mapping[str, Sequence[str]],
) -> list[float]:
    competitors = set(hard_negatives[family])
    weights: list[float] = []
    for anchor in anchors:
        if anchor["family"] == family:
            weights.append(1.0)
        elif anchor["family"] in competitors:
            weights.append(HARD_NEGATIVE_MULTIPLIER)
        else:
            weights.append(1.0)
    return weights


def supervised_contrastive_nll(
    similarities: Sequence[float],
    positive_mask: Sequence[bool],
    weights: Sequence[float],
    *,
    tau: float = GEOMETRY_TAU,
) -> float:
    """-log(sum_pos exp(sim/tau) / sum_all w exp(sim/tau))."""
    if not similarities or len(similarities) != len(positive_mask) or len(similarities) != len(weights):
        raise ClassificationContractError("FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", "contrastive_width")
    if not any(positive_mask):
        raise ClassificationContractError("FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", "no_positive")
    if not math.isfinite(tau) or tau <= 0.0:
        raise ClassificationContractError("FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", "tau")
    logits = [float(value) / tau for value in similarities]
    peak = max(logits)
    numer = 0.0
    denom = 0.0
    for logit, positive, weight in zip(logits, positive_mask, weights):
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(float(weight)):
            raise ClassificationContractError("FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", "weight")
        scale = float(weight)
        if scale <= 0.0:
            raise ClassificationContractError("FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", "weight")
        term = math.exp(logit - peak)
        denom += scale * term
        if positive:
            numer += term
    if numer <= 0.0 or denom <= 0.0:
        raise ClassificationContractError("FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", "contrastive")
    return math.log(denom) - math.log(numer)


def row_geometry_scores(
    similarities: Sequence[float],
    gold_family: str,
    anchors: Sequence[Mapping[str, Any]],
    hard_negatives: Mapping[str, Sequence[str]],
) -> dict[str, float]:
    if gold_family not in ACTIVE_FAMILY_VOCABULARY:
        raise ClassificationContractError("FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", gold_family)
    if len(similarities) != len(anchors):
        raise ClassificationContractError("FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", "similarity_width")
    competitors = set(hard_negatives[gold_family])
    positives = [
        float(value)
        for value, anchor in zip(similarities, anchors)
        if anchor["family"] == gold_family
    ]
    negatives = [
        float(value)
        for value, anchor in zip(similarities, anchors)
        if anchor["family"] in competitors
    ]
    if not positives or not negatives:
        raise ClassificationContractError("FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", gold_family)
    positive = max(positives)
    nearest_negative = max(negatives)
    return {
        "margin": positive - nearest_negative,
        "nearest_negative_similarity": nearest_negative,
        "positive_similarity": positive,
    }


def summarize_geometry_margins(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Aggregate per-family and global margin stats. Reserve rows are refused."""
    buckets: dict[str, list[dict[str, float]]] = {name: [] for name in ACTIVE_FAMILY_VOCABULARY}
    for row in rows:
        if row.get("evaluation_reserve") or row.get("held_out") or row.get("split") == "test":
            raise ClassificationContractError("evaluation_isolation")
        family = str(row["family"])
        buckets[family].append(
            {
                "margin": float(row["margin"]),
                "nearest_negative_similarity": float(row["nearest_negative_similarity"]),
                "positive_similarity": float(row["positive_similarity"]),
            }
        )
    per_family: dict[str, Any] = {}
    margins: list[float] = []
    high_collision_rows = 0
    for family, values in buckets.items():
        if not values:
            per_family[family] = {
                "margin": None,
                "n": 0,
                "nearest_negative_similarity": None,
                "positive_similarity": None,
            }
            continue
        pos = sum(item["positive_similarity"] for item in values) / len(values)
        neg = sum(item["nearest_negative_similarity"] for item in values) / len(values)
        margin = sum(item["margin"] for item in values) / len(values)
        per_family[family] = {
            "margin": margin,
            "n": len(values),
            "nearest_negative_similarity": neg,
            "positive_similarity": pos,
        }
        margins.extend(item["margin"] for item in values)
        high_collision_rows += sum(
            1 for item in values if item["nearest_negative_similarity"] >= COLLISION_COSINE
        )
    ordered = sorted(margins)
    median = None if not ordered else (
        ordered[len(ordered) // 2]
        if len(ordered) % 2 == 1
        else (ordered[len(ordered) // 2 - 1] + ordered[len(ordered) // 2]) / 2.0
    )
    return {
        "high_collision_rows": high_collision_rows,
        "median_margin": median,
        "mean_margin": None if not margins else sum(margins) / len(margins),
        "n_family": len(margins),
        "per_family": per_family,
    }


def assess_boundary_for_repair(boundaries: Mapping[str, Any]) -> dict[str, Any]:
    base = assess_boundary_artifact(boundaries)
    if not base.get("pass"):
        return base
    if boundaries.get("boundary_sha256") != BOUNDARY_SHA:
        return {"pass": False, "reason": "FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", "detail": "boundary_hash"}
    if boundaries.get("separation_sha256") != SEPARATION_SHA:
        return {"pass": False, "reason": "FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", "detail": "separation_hash"}
    if boundaries.get("schema") != BOUNDARY_SCHEMA:
        return {"pass": False, "reason": "FAMILY_GEOMETRY_REPAIR_UNAVAILABLE", "detail": "schema"}
    hard = hard_negatives_from_boundaries(boundaries)
    sparse = sparse_families_from_boundaries(boundaries)
    anchors = flatten_anchors(boundaries)
    return {
        "anchors": len(anchors),
        "boundary_sha256": BOUNDARY_SHA,
        "hard_negatives": hard,
        "pass": True,
        "separation_sha256": SEPARATION_SHA,
        "sparse_families": sparse,
    }


def repair_readiness_gate(
    *,
    active_family_macro_f1: float,
    prototype_family_macro_f1: float,
    new_family_f1_gt_0: int,
    median_margin: float,
    prior_median_margin: float,
    high_collision_rows: int,
    prior_high_collision_rows: int,
    invariance_pass: bool,
) -> dict[str, Any]:
    family_ok = float(active_family_macro_f1) > PRIOR_ACTIVE_FAMILY_MACRO
    new_macro_ok = float(prototype_family_macro_f1) > PRIOR_PROTOTYPE_FAMILY_MACRO
    breadth_ok = int(new_family_f1_gt_0) > PRIOR_NEW_FAMILY_F1_GT_0
    margin_ok = float(median_margin) > float(prior_median_margin)
    collision_ok = int(high_collision_rows) < int(prior_high_collision_rows)
    geometry_ok = margin_ok and collision_ok
    if family_ok and new_macro_ok and breadth_ok and geometry_ok and invariance_pass:
        status = "INTERNAL_IMPROVED"
    elif family_ok and not invariance_pass:
        status = "SETTLED_INVALID"
    else:
        status = "INTERNAL_SHORT"
    return {
        "breadth_ok": breadth_ok,
        "collision_ok": collision_ok,
        "family_ok": family_ok,
        "geometry_ok": geometry_ok,
        "invariance_pass": bool(invariance_pass),
        "margin_ok": margin_ok,
        "new_macro_ok": new_macro_ok,
        "reserve_justified": status == "INTERNAL_IMPROVED",
        "status": status,
    }


def repair_artifact_sha256(payload: Mapping[str, Any]) -> str:
    body = {
        "boundary_sha256": payload["boundary_sha256"],
        "canonical_logits": payload["canonical_logits"],
        "contract": payload["contract"],
        "hard_negatives": payload["hard_negatives"],
        "sparse_families": payload["sparse_families"],
    }
    return sha256_text(canonical_json(body))
