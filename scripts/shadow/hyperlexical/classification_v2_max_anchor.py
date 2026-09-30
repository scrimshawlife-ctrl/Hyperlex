"""Max-anchor family scorer for Classification v2.

Uses sealed multi-anchor boundaries as the family score. This module does not
train, fetch, or read the evaluation reserve.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .classification_v2 import (
    ACTIVE_FAMILY_VOCABULARY,
    ClassificationContractError,
    EXACT_COPY_FAMILIES,
    canonical_json,
    prf_table,
    sha256_text,
)
from .classification_v2_boundaries import (
    BOUNDARY_SCHEMA,
    assess_boundary_artifact,
)
from .classification_v2_geometry_repair import (
    BOUNDARY_SHA,
    SEPARATION_SHA,
    flatten_anchors,
)
from .classification_v2_prototype import population_standardize

SCORER_SCHEMA = "hyperlex.classification.v2.max_anchor_scorer.v1"
SCORER_RULE = "MAX_ANCHOR_FAMILY_SCORER_V1"
FUSION_ALPHA = 1.0
FUSION_BETA = 1.0
REPAIR_PRIMARY_SHA = "449bf3b303c95bc5d6b7d87173d50315616556c1379057414b970f3e5f0b18cf"
PRIOR_ACTIVE_FAMILY_MACRO = 0.1960828268105939
PRIOR_NEW_FAMILY_F1_GT_0 = 3
FORBIDDEN_FAMILY_LABELS = frozenset({"none", "NONE", "ABSTAIN", "AMBIGUOUS"})


def scorer_contract() -> dict[str, Any]:
    return {
        "boundary_sha256": BOUNDARY_SHA,
        "canonical_prediction": "argmax_max_anchor_cosine",
        "fusion_alpha": FUSION_ALPHA,
        "fusion_beta": FUSION_BETA,
        "fusion_diagnostic_only": True,
        "jev": "OFF",
        "repair_primary_sha256": REPAIR_PRIMARY_SHA,
        "rule": SCORER_RULE,
        "schema": SCORER_SCHEMA,
        "separation_sha256": SEPARATION_SHA,
        "train": False,
    }


def load_sealed_anchors(boundaries: Mapping[str, Any]) -> dict[str, list[list[float]]]:
    """Load sealed anchors unchanged. Refuse drifted hashes or missing families."""
    report = assess_boundary_artifact(boundaries)
    if not report.get("pass"):
        raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", report.get("detail") or "boundary")
    if boundaries.get("boundary_sha256") != BOUNDARY_SHA:
        raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", "boundary_hash")
    if boundaries.get("separation_sha256") != SEPARATION_SHA:
        raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", "separation_hash")
    if boundaries.get("schema") != BOUNDARY_SCHEMA:
        raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", "schema")
    flat = flatten_anchors(boundaries)
    by_family: dict[str, list[list[float]]] = {name: [] for name in ACTIVE_FAMILY_VOCABULARY}
    hashes: dict[str, list[str]] = {name: [] for name in ACTIVE_FAMILY_VOCABULARY}
    for anchor in flat:
        family = str(anchor["family"])
        if family in FORBIDDEN_FAMILY_LABELS:
            raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", family)
        by_family[family].append(list(anchor["vector"]))
        hashes[family].append(str(anchor["anchor_id"]))
    for family in ACTIVE_FAMILY_VOCABULARY:
        if not by_family[family]:
            raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", family)
    return {
        "anchors": by_family,
        "anchor_ids": hashes,
        "n_anchors": sum(len(values) for values in by_family.values()),
    }


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _unit(values: Sequence[float]) -> list[float]:
    norm = sum(value * value for value in values) ** 0.5
    if norm == 0.0:
        raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", "zero_norm")
    return [value / norm for value in values]


def max_anchor_scores(
    representation: Sequence[float],
    anchors_by_family: Mapping[str, Sequence[Sequence[float]]],
) -> list[float]:
    """One score per active family in vocabulary order."""
    if set(anchors_by_family) != set(ACTIVE_FAMILY_VOCABULARY):
        raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", "coverage")
    hidden = _unit(representation)
    scores: list[float] = []
    for family in ACTIVE_FAMILY_VOCABULARY:
        anchors = anchors_by_family[family]
        if not anchors:
            raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", family)
        peak = max(_dot(hidden, _unit(anchor)) for anchor in anchors)
        scores.append(float(peak))
    return scores


def residual_scores(logits: Sequence[float]) -> list[float]:
    if len(logits) != len(ACTIVE_FAMILY_VOCABULARY):
        raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", "residual_width")
    return [float(value) for value in logits]


def fusion_scores(anchor_scores: Sequence[float], residual_logits: Sequence[float]) -> list[float]:
    """Diagnostic only. Fixed 1:1 population-zscore fusion."""
    if len(anchor_scores) != len(residual_logits):
        raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", "fusion_width")
    left = population_standardize(anchor_scores)
    right = population_standardize(residual_logits)
    return [FUSION_ALPHA * a + FUSION_BETA * b for a, b in zip(left, right)]


def predict_family(scores: Sequence[float]) -> str:
    """Argmax with vocabulary-order tie break. No NONE/ABSTAIN/AMBIGUOUS rows."""
    if len(scores) != len(ACTIVE_FAMILY_VOCABULARY):
        raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", "score_width")
    best_index = 0
    best_score = float(scores[0])
    for index, score in enumerate(scores):
        value = float(score)
        if value > best_score:
            best_index = index
            best_score = value
    name = ACTIVE_FAMILY_VOCABULARY[best_index]
    if name in FORBIDDEN_FAMILY_LABELS:
        raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", name)
    return name


def topk_families(scores: Sequence[float], k: int = 2) -> list[str]:
    if k < 1 or k > len(ACTIVE_FAMILY_VOCABULARY):
        raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", "topk")
    order = sorted(
        range(len(ACTIVE_FAMILY_VOCABULARY)),
        key=lambda index: (-float(scores[index]), index),
    )
    return [ACTIVE_FAMILY_VOCABULARY[index] for index in order[:k]]


def gold_vs_best_negative_margin(scores: Sequence[float], gold: str) -> float:
    if gold not in ACTIVE_FAMILY_VOCABULARY:
        raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", gold)
    index = ACTIVE_FAMILY_VOCABULARY.index(gold)
    gold_score = float(scores[index])
    others = [float(scores[i]) for i in range(len(scores)) if i != index]
    return gold_score - max(others)


def breadth_counts(per_family: Mapping[str, Mapping[str, Any]]) -> dict[str, int]:
    def count(threshold: float, names: Sequence[str] | None = None) -> int:
        total = 0
        for name, stats in per_family.items():
            if names is not None and name not in names:
                continue
            if name in FORBIDDEN_FAMILY_LABELS:
                continue
            f1 = stats.get("f1")
            if f1 is not None and float(f1) > threshold:
                total += 1
        return total

    new_names = [name for name in ACTIVE_FAMILY_VOCABULARY if name not in EXACT_COPY_FAMILIES]
    return {
        "f1_gt_0": count(0.0),
        "f1_ge_0_20": count(0.20 - 1e-12),
        "f1_ge_0_50": count(0.50 - 1e-12),
        "new_family_f1_gt_0": count(0.0, new_names),
    }


def summarize_margins(margins: Sequence[float]) -> dict[str, float | int | None]:
    values = [float(value) for value in margins]
    if not values:
        return {"mean": None, "median": None, "n": 0}
    ordered = sorted(values)
    mid = len(ordered) // 2
    median = ordered[mid] if len(ordered) % 2 == 1 else (ordered[mid - 1] + ordered[mid]) / 2.0
    return {
        "mean": sum(values) / len(values),
        "median": median,
        "n": len(values),
    }


def score_report(
    golds: Sequence[str],
    preds: Sequence[str],
    scores_rows: Sequence[Sequence[float]],
    *,
    surfaces: Sequence[str] | None = None,
) -> dict[str, Any]:
    if len(golds) != len(preds) or len(golds) != len(scores_rows):
        raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", "report_width")
    if any(name in FORBIDDEN_FAMILY_LABELS for name in (*golds, *preds)):
        raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", "forbidden_label")
    table = prf_table(list(golds), list(preds), ACTIVE_FAMILY_VOCABULARY)
    top1 = sum(1 for gold, pred in zip(golds, preds) if gold == pred) / max(1, len(golds))
    top2 = 0
    margins = []
    for gold, scores in zip(golds, scores_rows):
        names = topk_families(scores, 2)
        if gold in names:
            top2 += 1
        margins.append(gold_vs_best_negative_margin(scores, gold))
    top2 = top2 / max(1, len(golds))
    by_surface: dict[str, Any] = {}
    if surfaces is not None:
        if len(surfaces) != len(golds):
            raise ClassificationContractError("MAX_ANCHOR_SCORER_UNAVAILABLE", "surface_width")
        for surface in sorted(set(surfaces)):
            idxs = [index for index, name in enumerate(surfaces) if name == surface]
            if not idxs:
                continue
            surface_table = prf_table(
                [golds[index] for index in idxs],
                [preds[index] for index in idxs],
                ACTIVE_FAMILY_VOCABULARY,
            )
            by_surface[surface] = surface_table["macro_f1"]
    return {
        "active_family_macro_f1": table["macro_f1"],
        "breadth": breadth_counts(table["per_label"]),
        "macro_f1_by_surface": by_surface,
        "margin": summarize_margins(margins),
        "n": len(golds),
        "per_family": table["per_label"],
        "top1_accuracy": top1,
        "top2_accuracy": top2,
    }


def decide_max_anchor(report: Mapping[str, Any]) -> dict[str, Any]:
    macro = float(report["active_family_macro_f1"])
    breadth = int(report["breadth"]["new_family_f1_gt_0"])
    supported = macro > PRIOR_ACTIVE_FAMILY_MACRO and breadth > PRIOR_NEW_FAMILY_F1_GT_0
    return {
        "active_family_macro_f1": macro,
        "canonical_integration_justified": supported,
        "decision": "MAX_ANCHOR_SCORER_SUPPORTED" if supported else "MAX_ANCHOR_SCORER_REJECTED",
        "new_family_f1_gt_0": breadth,
        "prior_active_family_macro_f1": PRIOR_ACTIVE_FAMILY_MACRO,
        "prior_new_family_f1_gt_0": PRIOR_NEW_FAMILY_F1_GT_0,
    }


def artifact_sha256(payload: Mapping[str, Any]) -> str:
    body = {
        "contract": payload["contract"],
        "decision": payload["decision"],
        "max_anchor": {
            "active_family_macro_f1": payload["max_anchor"]["active_family_macro_f1"],
            "breadth": payload["max_anchor"]["breadth"],
            "top1_accuracy": payload["max_anchor"]["top1_accuracy"],
            "top2_accuracy": payload["max_anchor"]["top2_accuracy"],
        },
        "residual": {
            "active_family_macro_f1": payload["residual"]["active_family_macro_f1"],
            "breadth": payload["residual"]["breadth"],
        },
        "fusion": {
            "active_family_macro_f1": payload["fusion"]["active_family_macro_f1"],
            "breadth": payload["fusion"]["breadth"],
        },
    }
    return sha256_text(canonical_json(body))
