"""HYPERLEX_FORWARD_HUB_ERROR_DECOMPOSITION_V1 — read-only validation audit.

Scores the sealed forward-hub checkpoint on the hub-filtered validation
surface. Does not train, does not score the evaluation reserve, does not
move BEST, and does not mutate ontology or prototypes.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from typing import Any, Mapping, Sequence

from .classification_v2 import (
    ACTIVE_FAMILY_VOCABULARY,
    EXACT_COPY_FAMILIES,
    canonical_json,
    prf_table,
    sha256_text,
)
from .classification_v2_surface import SURFACE_ATOM, SURFACE_PROSE, surface_form

RULE = "HYPERLEX_FORWARD_HUB_ERROR_DECOMPOSITION_V1"
SCHEMA = "hyperlex.classification.v2.forward_hub_error_decomposition.v1"
RUN_ID = "HLX-CLASSIFICATION-V2-FORWARD-HUB-ERROR-DECOMPOSITION-20260930"

PRIOR_INTERNAL_ACTIVE_FAMILY_MACRO_F1 = 0.1960828268105939
FORWARD_HUB_ACTIVE_FAMILY_MACRO_F1 = 0.18562993635457403
FORWARD_HUB_PROTOTYPE_FAMILY_MACRO_F1 = 0.05451049985211476
FORWARD_HUB_WEIGHTS_SHA256 = (
    "adf5db93dfe258290be531f0a25035dfaae03873bd800fd929bee43b38c9f89c"
)
FORWARD_HUB_EXPORT_SHA256 = (
    "0d8f4532f84ed9fade3fd4e69af0d1e0717fb1098d40754e95c0090d8282bfe1"
)
FORWARD_HUB_WITNESS_SHA256 = (
    "acca1594b49aa624d0d4dc97f03c7ccc69176568dfde0bebb7fb81c5085ca294"
)
HUB_BOUNDARY_SHA256 = (
    "96a0587c06fac352872e462445f2eaaf773e35a48ab4c987e267b479cab72a83"
)
BEST_SHA256 = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
MERGE_PAIR_SHA256 = "c901badb70c0c72f1af20fe4dd0b64bcbdfad917568682e9abb2cc9321ad69d5"

SOCIAL_EVALUATION = "social-evaluation"
RELATIONSHIP_DATING = "relationship-dating"

FAILURE_CAUSES = (
    "DOMINANT_CLASS_ATTRACTOR",
    "PAIRWISE_BOUNDARY_COLLISION",
    "UNDER_SUPPORTED_FAMILY",
    "SURFACE_MISMATCH",
    "PROTOTYPE_MISMATCH",
    "RESIDUAL_HEAD_FAILURE",
    "AMBIGUOUS_GOLD",
    "OTHER",
)

DECISIONS = (
    "SCORER_REPAIR_JUSTIFIED",
    "DATA_REMEDIATION_JUSTIFIED",
    "ONTOLOGY_REMEDIATION_JUSTIFIED",
    "ENCODER_REMEDIATION_JUSTIFIED",
    "RESERVE_EVAL_JUSTIFIED",
    "STOP_NO_CLEAR_REMEDIATION",
)

UNDER_SUPPORT_MAX = 3
HUB_RATIO_MIN = 2.0
HUB_INCOMING_FP_MIN = 5
HUB_FP_SHARE_MIN = 0.20
AMBIGUOUS_MARGIN = 0.35
OVERLAP_COSINE_MIN = 0.80
TOP_CONFUSIONS_K = 5


def error_decomposition_contract() -> dict[str, Any]:
    return {
        "applies_ontology_change": False,
        "best_sha256": BEST_SHA256,
        "export_sha256": FORWARD_HUB_EXPORT_SHA256,
        "forward_hub_weights_sha256": FORWARD_HUB_WEIGHTS_SHA256,
        "hub_boundary_sha256": HUB_BOUNDARY_SHA256,
        "jev": "OFF",
        "merge_pair_sha256": MERGE_PAIR_SHA256,
        "modifies_prototypes": False,
        "moves_best": False,
        "opens_training_gate": False,
        "prior_internal_active_family_macro_f1": PRIOR_INTERNAL_ACTIVE_FAMILY_MACRO_F1,
        "prototype_witness_sha256": FORWARD_HUB_WITNESS_SHA256,
        "reserve_scored": False,
        "rule": RULE,
        "run": RUN_ID,
        "schema": SCHEMA,
        "train": False,
    }


def _finite(value: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non_finite_metric")
    return number


def logit_rank(logits: Sequence[float], index: int) -> int:
    if index < 0 or index >= len(logits):
        raise ValueError("logit_index_out_of_range")
    target = float(logits[index])
    better = sum(1 for value in logits if float(value) > target)
    ties_before = sum(
        1
        for position, value in enumerate(logits)
        if position < index and float(value) == target
    )
    return better + ties_before + 1


def topk_accuracy(ranks: Sequence[int], k: int) -> float | None:
    if not ranks:
        return None
    return sum(1 for rank in ranks if rank <= k) / len(ranks)


def confusion_matrix(
    golds: Sequence[str], preds: Sequence[str], labels: Sequence[str]
) -> dict[str, dict[str, int]]:
    table = {gold: {pred: 0 for pred in labels} for gold in labels}
    for gold, pred in zip(golds, preds, strict=True):
        if gold in table and pred in table[gold]:
            table[gold][pred] += 1
    return {
        gold: {pred: count for pred, count in row.items() if count}
        for gold, row in table.items()
        if any(row.values())
    }


def confusion_matrix_hash(matrix: Mapping[str, Mapping[str, int]]) -> str:
    return sha256_text(canonical_json(matrix))


def top_confusions_for_family(
    matrix: Mapping[str, Mapping[str, int]], family: str, *, k: int = TOP_CONFUSIONS_K
) -> list[dict[str, Any]]:
    outgoing = [
        {"count": int(count), "pred": pred}
        for pred, count in (matrix.get(family) or {}).items()
        if pred != family and count
    ]
    outgoing.sort(key=lambda item: (-int(item["count"]), str(item["pred"])))
    return outgoing[:k]


def family_surface_majority(rows: Sequence[Mapping[str, Any]], family: str) -> str | None:
    counts: Counter[str] = Counter()
    for row in rows:
        if row.get("lineage") != family:
            continue
        form = surface_form(str(row.get("text") or ""))
        if form in {SURFACE_ATOM, SURFACE_PROSE}:
            counts[form] += 1
    if not counts:
        return None
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def overlap_pair_set(
    pairs: Sequence[Mapping[str, Any]], *, threshold: float = OVERLAP_COSINE_MIN
) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for pair in pairs:
        cosine = float(pair.get("cosine") or 0.0)
        if cosine < threshold:
            continue
        left = str(pair.get("family_a") or "")
        right = str(pair.get("family_b") or "")
        if not left or not right:
            continue
        out.add(tuple(sorted((left, right))))
    return out


def nearest_neighbors(
    pairs: Sequence[Mapping[str, Any]], family: str, *, k: int = 8
) -> list[dict[str, Any]]:
    rows = []
    for pair in pairs:
        left = str(pair.get("family_a") or "")
        right = str(pair.get("family_b") or "")
        if family not in {left, right}:
            continue
        other = right if left == family else left
        rows.append({"cosine": float(pair.get("cosine") or 0.0), "family": other})
    rows.sort(key=lambda item: (-float(item["cosine"]), str(item["family"])))
    return rows[:k]


def detect_prediction_hubs(
    golds: Sequence[str],
    preds: Sequence[str],
    labels: Sequence[str],
    *,
    ratio_min: float = HUB_RATIO_MIN,
    incoming_fp_min: int = HUB_INCOMING_FP_MIN,
    fp_share_min: float = HUB_FP_SHARE_MIN,
) -> list[dict[str, Any]]:
    support = Counter(golds)
    predicted = Counter(preds)
    incoming: Counter[str] = Counter()
    absorbed: dict[str, Counter[str]] = {name: Counter() for name in labels}
    for gold, pred in zip(golds, preds, strict=True):
        if gold == pred:
            continue
        if pred in absorbed:
            incoming[pred] += 1
            absorbed[pred][gold] += 1
    total_fp = sum(incoming.values()) or 1
    hubs = []
    for family in labels:
        gold_support = int(support.get(family, 0))
        pred_count = int(predicted.get(family, 0))
        ratio = pred_count / max(gold_support, 1)
        fp = int(incoming.get(family, 0))
        fp_share = fp / total_fp
        is_hub = (ratio >= ratio_min and fp >= incoming_fp_min) or (
            fp_share >= fp_share_min and fp >= incoming_fp_min
        )
        if not is_hub:
            continue
        top_absorbed = [
            {"count": count, "family": name}
            for name, count in absorbed[family].most_common(8)
        ]
        hubs.append(
            {
                "family": family,
                "flag": "PREDICTION_HUB",
                "gold_support": gold_support,
                "incoming_confusion_count": fp,
                "incoming_fp_share": fp_share,
                "predicted_count": pred_count,
                "predicted_over_gold": ratio,
                "families_most_frequently_absorbed": top_absorbed,
            }
        )
    hubs.sort(
        key=lambda item: (
            -float(item["incoming_confusion_count"]),
            -float(item["predicted_over_gold"]),
            str(item["family"]),
        )
    )
    return hubs


def assign_primary_cause(
    *,
    gold: str,
    pred: str,
    gold_support: int,
    gold_residual_rank: int,
    gold_prototype_rank: int | None,
    residual_logits: Sequence[float],
    gold_index: int,
    pred_index: int,
    prediction_hubs: set[str],
    overlap_pairs: set[tuple[str, str]],
    gold_surface: str,
    gold_majority_surface: str | None,
    pred_majority_surface: str | None,
    initialization_mode: str | None,
    evidence_class: str,
) -> dict[str, Any]:
    if gold == pred:
        raise ValueError("cause_only_for_errors")
    margin = abs(float(residual_logits[gold_index]) - float(residual_logits[pred_index]))
    pair = tuple(sorted((gold, pred)))
    evidence: dict[str, Any] = {
        "evidence_class": evidence_class,
        "gold": gold,
        "gold_majority_surface": gold_majority_surface,
        "gold_prototype_rank": gold_prototype_rank,
        "gold_residual_rank": gold_residual_rank,
        "gold_support": gold_support,
        "gold_surface": gold_surface,
        "initialization_mode": initialization_mode,
        "logit_margin_abs": margin,
        "overlap_pair": pair in overlap_pairs,
        "pred": pred,
        "pred_is_hub": pred in prediction_hubs,
        "pred_majority_surface": pred_majority_surface,
    }

    if (
        evidence_class == "INFERRED"
        and gold_residual_rank <= 3
        and margin < AMBIGUOUS_MARGIN
        and pair in overlap_pairs
    ):
        return {"cause": "AMBIGUOUS_GOLD", "evidence": evidence}

    if gold_support <= UNDER_SUPPORT_MAX:
        return {"cause": "UNDER_SUPPORTED_FAMILY", "evidence": evidence}

    if pred in prediction_hubs:
        return {"cause": "DOMINANT_CLASS_ATTRACTOR", "evidence": evidence}

    if pair in overlap_pairs:
        return {"cause": "PAIRWISE_BOUNDARY_COLLISION", "evidence": evidence}

    if (
        gold_majority_surface in {SURFACE_ATOM, SURFACE_PROSE}
        and gold_surface in {SURFACE_ATOM, SURFACE_PROSE}
        and gold_surface != gold_majority_surface
        and pred_majority_surface == gold_surface
    ):
        return {"cause": "SURFACE_MISMATCH", "evidence": evidence}

    if (
        initialization_mode == "SEMANTIC_PROTOTYPE"
        and gold_prototype_rank is not None
        and gold_prototype_rank > gold_residual_rank
    ):
        return {"cause": "PROTOTYPE_MISMATCH", "evidence": evidence}

    if gold_residual_rank > 2:
        return {"cause": "RESIDUAL_HEAD_FAILURE", "evidence": evidence}

    return {"cause": "OTHER", "evidence": evidence}


def per_family_report(
    *,
    labels: Sequence[str],
    golds: Sequence[str],
    preds: Sequence[str],
    residual_ranks: Sequence[int],
    matrix: Mapping[str, Mapping[str, int]],
) -> dict[str, dict[str, Any]]:
    table = prf_table(golds, preds, labels)["per_label"]
    ranks_by_family: dict[str, list[int]] = {name: [] for name in labels}
    for gold, rank in zip(golds, residual_ranks, strict=True):
        ranks_by_family[gold].append(int(rank))
    out: dict[str, dict[str, Any]] = {}
    for family in labels:
        stats = table[family]
        family_ranks = ranks_by_family[family]
        out[family] = {
            "f1": stats["f1"],
            "gold_logit_rank_mean": None
            if not family_ranks
            else sum(family_ranks) / len(family_ranks),
            "precision": stats["precision"],
            "predicted_count": int(stats.get("predicted") or 0),
            "recall": stats["recall"],
            "support": int(stats["support"] or 0),
            "top1_accuracy": topk_accuracy(family_ranks, 1),
            "top2_accuracy": topk_accuracy(family_ranks, 2),
            "top_confusions": top_confusions_for_family(matrix, family),
        }
    return out


def surface_macro_f1(
    golds: Sequence[str],
    preds: Sequence[str],
    surfaces: Sequence[str],
    labels: Sequence[str],
    form: str,
) -> float | None:
    kept_gold = []
    kept_pred = []
    for gold, pred, surface in zip(golds, preds, surfaces, strict=True):
        if surface == form:
            kept_gold.append(gold)
            kept_pred.append(pred)
    if not kept_gold:
        return None
    return prf_table(kept_gold, kept_pred, labels)["macro_f1"]


def social_evaluation_audit(
    *,
    golds: Sequence[str],
    preds: Sequence[str],
    family_metrics: Mapping[str, Mapping[str, Any]],
    matrix: Mapping[str, Mapping[str, int]],
    overlap_pairs: Sequence[Mapping[str, Any]],
    hubs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    se = family_metrics[SOCIAL_EVALUATION]
    incoming = []
    for gold, row in matrix.items():
        count = int(row.get(SOCIAL_EVALUATION) or 0)
        if gold != SOCIAL_EVALUATION and count:
            incoming.append({"count": count, "gold": gold})
    incoming.sort(key=lambda item: (-int(item["count"]), str(item["gold"])))
    outgoing = list(se.get("top_confusions") or [])
    rd_to_se = int((matrix.get(RELATIONSHIP_DATING) or {}).get(SOCIAL_EVALUATION) or 0)
    se_to_rd = int((matrix.get(SOCIAL_EVALUATION) or {}).get(RELATIONSHIP_DATING) or 0)
    hub_families = {str(item["family"]) for item in hubs}
    neighbors = nearest_neighbors(overlap_pairs, SOCIAL_EVALUATION)
    attractor = SOCIAL_EVALUATION in hub_families or sum(item["count"] for item in incoming) >= 5
    operational = (
        float(se.get("f1") or 0.0) > 0.0
        and int(se.get("support") or 0) >= 2
        and not attractor
    )
    return {
        "f1": se.get("f1"),
        "flag": "LARGER_ATTRACTOR" if attractor and not operational else (
            "OPERATIONAL_SEPARABILITY" if operational else "WEAK_NON_HUB"
        ),
        "incoming_confusions": incoming,
        "is_prediction_hub": SOCIAL_EVALUATION in hub_families,
        "merge_improved_operational_separability": operational,
        "nearest_ontology_neighbors": neighbors,
        "outgoing_confusions": outgoing,
        "predicted_count": se.get("predicted_count"),
        "relationship_dating_confusion": {
            "relationship_dating_to_social_evaluation": rd_to_se,
            "social_evaluation_to_relationship_dating": se_to_rd,
            "total": rd_to_se + se_to_rd,
        },
        "support": se.get("support"),
    }


def prototype_vs_residual(
    *,
    labels: Sequence[str],
    golds: Sequence[str],
    residual_preds: Sequence[str],
    prototype_preds: Sequence[str],
    residual_ranks: Sequence[int],
    prototype_ranks: Sequence[int],
    initialization_by_family: Mapping[str, str],
) -> dict[str, Any]:
    residual_table = prf_table(golds, residual_preds, labels)
    prototype_table = prf_table(golds, prototype_preds, labels)
    per_family = {}
    for family in labels:
        family_residual_ranks = [
            rank for gold, rank in zip(golds, residual_ranks) if gold == family
        ]
        family_prototype_ranks = [
            rank for gold, rank in zip(golds, prototype_ranks) if gold == family
        ]
        per_family[family] = {
            "initialization_mode": initialization_by_family.get(family),
            "prototype_f1": prototype_table["per_label"][family]["f1"],
            "prototype_top1_accuracy": topk_accuracy(family_prototype_ranks, 1),
            "residual_f1": residual_table["per_label"][family]["f1"],
            "residual_top1_accuracy": topk_accuracy(family_residual_ranks, 1),
            "mean_prototype_rank": None
            if not family_prototype_ranks
            else sum(family_prototype_ranks) / len(family_prototype_ranks),
            "mean_residual_rank": None
            if not family_residual_ranks
            else sum(family_residual_ranks) / len(family_residual_ranks),
        }
    proto_names = [name for name in labels if name not in EXACT_COPY_FAMILIES]
    exact_names = [name for name in labels if name in EXACT_COPY_FAMILIES]

    def _group(names: Sequence[str], key: str) -> float | None:
        scored = []
        for name in names:
            value = per_family[name][key]
            support = residual_table["per_label"][name]["support"]
            if support and value is not None:
                scored.append(float(value))
        if not scored:
            return None
        return sum(scored) / len(scored)

    return {
        "exact_copy_families": list(exact_names),
        "explanation": (
            "prototype_family_macro_f1 scores residual-head argmax on families outside "
            "EXACT_COPY_FAMILIES; separately, prototype-path argmax uses cosine to sealed "
            "witness weights. Weak PF indicates residual discrimination failure on "
            "prototype-initialized / non-legacy-strong families, not a witness mutation."
        ),
        "per_family": per_family,
        "prototype_path_macro_f1": prototype_table["macro_f1"],
        "prototype_group_residual_macro_f1": _group(proto_names, "residual_f1"),
        "residual_macro_f1": residual_table["macro_f1"],
        "semantic_prototype_families": [
            name
            for name in labels
            if initialization_by_family.get(name) == "SEMANTIC_PROTOTYPE"
        ],
    }


def macro_loss_drivers(
    family_metrics: Mapping[str, Mapping[str, Any]],
    *,
    baseline: float = PRIOR_INTERNAL_ACTIVE_FAMILY_MACRO_F1,
) -> dict[str, Any]:
    rows = []
    for family, stats in family_metrics.items():
        support = int(stats.get("support") or 0)
        if not support:
            continue
        f1 = float(stats.get("f1") or 0.0)
        rows.append(
            {
                "delta_vs_baseline": f1 - baseline,
                "f1": f1,
                "family": family,
                "loss_vs_perfect": 1.0 - f1,
                "support": support,
                "weighted_loss": (1.0 - f1) * support,
            }
        )
    rows.sort(key=lambda item: (-float(item["loss_vs_perfect"]), -int(item["support"]), str(item["family"])))
    zero = [row for row in rows if float(row["f1"]) == 0.0]
    return {
        "families_with_zero_f1": [row["family"] for row in zero],
        "top_macro_loss_families": rows[:12],
        "zero_f1_support_total": sum(int(row["support"]) for row in zero),
    }


def decide_remediation(
    *,
    active_family_macro_f1: float,
    prototype_family_macro_f1: float | None,
    hubs: Sequence[Mapping[str, Any]],
    se_audit: Mapping[str, Any],
    cause_counts: Mapping[str, int],
    loss_drivers: Mapping[str, Any],
    prototype_compare: Mapping[str, Any],
) -> dict[str, Any]:
    af = _finite(active_family_macro_f1)
    pf = None if prototype_family_macro_f1 is None else _finite(prototype_family_macro_f1)
    hub_names = [str(item["family"]) for item in hubs]
    total_errors = sum(int(count) for count in cause_counts.values()) or 1
    under_share = int(cause_counts.get("UNDER_SUPPORTED_FAMILY") or 0) / total_errors
    boundary_share = int(cause_counts.get("PAIRWISE_BOUNDARY_COLLISION") or 0) / total_errors
    attractor_share = int(cause_counts.get("DOMINANT_CLASS_ATTRACTOR") or 0) / total_errors
    residual_share = int(cause_counts.get("RESIDUAL_HEAD_FAILURE") or 0) / total_errors
    proto_path = float(prototype_compare.get("prototype_path_macro_f1") or 0.0)
    residual_macro = float(prototype_compare.get("residual_macro_f1") or 0.0)
    zero_families = list(loss_drivers.get("families_with_zero_f1") or [])
    se_attractor = se_audit.get("flag") == "LARGER_ATTRACTOR" or bool(
        se_audit.get("is_prediction_hub")
    )
    competitive = af + 1e-12 >= PRIOR_INTERNAL_ACTIVE_FAMILY_MACRO_F1
    major_unresolved = bool(hub_names) or se_attractor or len(zero_families) >= 6

    if competitive and not major_unresolved:
        decision = "RESERVE_EVAL_JUSTIFIED"
        remediation = (
            "Internal AF is competitive with the prior baseline and no major hub/"
            "ontology failure remains; an explicit reserve score is the next authorized step."
        )
    elif se_attractor or (
        SOCIAL_EVALUATION in hub_names and float(se_audit.get("f1") or 0.0) == 0.0
    ):
        decision = "ONTOLOGY_REMEDIATION_JUSTIFIED"
        remediation = (
            "social-evaluation absorbed false-positive mass / remained F1=0; refine or "
            "re-split the SE merge boundary (especially vs relationship-dating and slang "
            "neighbors) before more training or reserve spend."
        )
    elif under_share >= 0.45 and len(zero_families) >= 6:
        decision = "DATA_REMEDIATION_JUSTIFIED"
        remediation = (
            "Macro-F1 is dominated by under-supported families (support≤3) with F1=0; "
            "acquire/balance validation+train definitions for those families before "
            "another scorer pass."
        )
    elif boundary_share >= 0.30 and attractor_share < 0.20:
        decision = "ONTOLOGY_REMEDIATION_JUSTIFIED"
        remediation = (
            "Pairwise high-overlap collisions dominate errors; tighten exclusive "
            "definitions / hub boundaries on the colliding pairs."
        )
    elif proto_path + 0.02 < residual_macro and residual_share >= 0.25:
        decision = "SCORER_REPAIR_JUSTIFIED"
        remediation = (
            "Residual head still outranks the frozen prototype path, but residual "
            "rank failures concentrate on non-hub families; repair family-head / "
            "calibration scoring on the existing ontology."
        )
    elif residual_macro < 0.12 and len([n for n in EXACT_COPY_FAMILIES if n in zero_families]) >= 2:
        decision = "ENCODER_REMEDIATION_JUSTIFIED"
        remediation = (
            "Even legacy-strong exact-copy families collapse; encoder geometry needs "
            "another repair before ontology or reserve work."
        )
    elif attractor_share >= 0.25 and hub_names:
        decision = "SCORER_REPAIR_JUSTIFIED"
        remediation = (
            "Prediction hubs dominate false-positive mass with an otherwise frozen "
            "ontology; apply hub-aware scorer / prior rebalancing on the forward head."
        )
    elif pf is not None and pf < 0.08 and af < PRIOR_INTERNAL_ACTIVE_FAMILY_MACRO_F1:
        decision = "DATA_REMEDIATION_JUSTIFIED"
        remediation = (
            "Prototype-group residual macro-F1 remains near floor while AF stays below "
            "the internal baseline; remediate sparse family support and definition "
            "coverage before reserve spend."
        )
    else:
        decision = "STOP_NO_CLEAR_REMEDIATION"
        remediation = (
            "Failure mass is mixed without a single dominant lever that clears the "
            "baseline gap; do not spend reserve or launch another blind train."
        )

    if decision not in DECISIONS:
        raise ValueError(f"unknown_decision:{decision}")
    return {
        "active_family_macro_f1": af,
        "attractor_share": attractor_share,
        "boundary_share": boundary_share,
        "competitive_with_prior_baseline": competitive,
        "decision": decision,
        "major_unresolved_failure_mode": major_unresolved,
        "prediction_hubs": hub_names,
        "prior_internal_active_family_macro_f1": PRIOR_INTERNAL_ACTIVE_FAMILY_MACRO_F1,
        "prototype_family_macro_f1": pf,
        "residual_share": residual_share,
        "smallest_justified_remediation": remediation,
        "under_supported_share": under_share,
    }


def assemble_error_decomposition(payload: Mapping[str, Any]) -> dict[str, Any]:
    contract = error_decomposition_contract()
    labels = list(payload["labels"])
    if labels != list(ACTIVE_FAMILY_VOCABULARY):
        raise ValueError("label_order_drift")
    golds = list(payload["golds"])
    residual_preds = list(payload["residual_preds"])
    prototype_preds = list(payload["prototype_preds"])
    residual_ranks = [int(value) for value in payload["residual_ranks"]]
    prototype_ranks = [int(value) for value in payload["prototype_ranks"]]
    surfaces = list(payload["surfaces"])
    evidence_classes = list(payload["evidence_classes"])
    residual_logits_rows = list(payload["residual_logits"])
    initialization_by_family = dict(payload["initialization_by_family"])
    overlap_pairs = list(payload.get("overlap_pairs") or [])
    train_rows = list(payload.get("train_rows") or [])

    if not (
        len(golds)
        == len(residual_preds)
        == len(prototype_preds)
        == len(residual_ranks)
        == len(prototype_ranks)
        == len(surfaces)
        == len(evidence_classes)
        == len(residual_logits_rows)
    ):
        raise ValueError("row_length_mismatch")

    matrix = confusion_matrix(golds, residual_preds, labels)
    family_metrics = per_family_report(
        labels=labels,
        golds=golds,
        preds=residual_preds,
        residual_ranks=residual_ranks,
        matrix=matrix,
    )
    prf = prf_table(golds, residual_preds, labels)
    exact_names = [name for name in labels if name in EXACT_COPY_FAMILIES]
    non_exact = [name for name in labels if name not in EXACT_COPY_FAMILIES]
    exact_macro = prf_table(golds, residual_preds, exact_names)["macro_f1"]
    non_exact_macro = prf_table(golds, residual_preds, non_exact)["macro_f1"]
    hubs = detect_prediction_hubs(golds, residual_preds, labels)
    hub_names = {str(item["family"]) for item in hubs}
    overlap_set = overlap_pair_set(overlap_pairs)
    majority = {
        family: family_surface_majority(train_rows, family)
        for family in labels
    }
    support = Counter(golds)
    index_of = {name: index for index, name in enumerate(labels)}
    cause_rows = []
    cause_counts: Counter[str] = Counter()
    for index, (gold, pred) in enumerate(zip(golds, residual_preds, strict=True)):
        if gold == pred:
            continue
        assigned = assign_primary_cause(
            gold=gold,
            pred=pred,
            gold_support=int(support[gold]),
            gold_residual_rank=residual_ranks[index],
            gold_prototype_rank=prototype_ranks[index],
            residual_logits=residual_logits_rows[index],
            gold_index=index_of[gold],
            pred_index=index_of[pred],
            prediction_hubs=hub_names,
            overlap_pairs=overlap_set,
            gold_surface=surfaces[index],
            gold_majority_surface=majority.get(gold),
            pred_majority_surface=majority.get(pred),
            initialization_mode=initialization_by_family.get(gold),
            evidence_class=str(evidence_classes[index]),
        )
        cause_counts[assigned["cause"]] += 1
        cause_rows.append(
            {
                "cause": assigned["cause"],
                "evidence": assigned["evidence"],
                "index": index,
            }
        )
    se_audit = social_evaluation_audit(
        golds=golds,
        preds=residual_preds,
        family_metrics=family_metrics,
        matrix=matrix,
        overlap_pairs=overlap_pairs,
        hubs=hubs,
    )
    proto_compare = prototype_vs_residual(
        labels=labels,
        golds=golds,
        residual_preds=residual_preds,
        prototype_preds=prototype_preds,
        residual_ranks=residual_ranks,
        prototype_ranks=prototype_ranks,
        initialization_by_family=initialization_by_family,
    )
    drivers = macro_loss_drivers(family_metrics)
    decision = decide_remediation(
        active_family_macro_f1=float(prf["macro_f1"] or 0.0),
        prototype_family_macro_f1=non_exact_macro,
        hubs=hubs,
        se_audit=se_audit,
        cause_counts=cause_counts,
        loss_drivers=drivers,
        prototype_compare=proto_compare,
    )
    artifact = {
        "active_family_macro_f1": prf["macro_f1"],
        "atom_macro_f1": surface_macro_f1(golds, residual_preds, surfaces, labels, SURFACE_ATOM),
        "audit_state": {
            "best_moved": False,
            "checkpoint_sha256": FORWARD_HUB_WEIGHTS_SHA256,
            "export_sha256": FORWARD_HUB_EXPORT_SHA256,
            "forward_ontology": True,
            "read_only": True,
            "reserve_scored": False,
            "run": RUN_ID,
            "surface": "validation",
            "train": False,
        },
        "confusion_matrix": matrix,
        "confusion_matrix_sha256": confusion_matrix_hash(matrix),
        "contract": contract,
        "decision": decision["decision"],
        "decision_detail": decision,
        "dominant_failure_categories": [
            {"cause": cause, "count": int(cause_counts.get(cause, 0))}
            for cause in FAILURE_CAUSES
        ],
        "error_rows": cause_rows,
        "exact_copy_macro_f1": exact_macro,
        "macro_f1_excluding_exact_copy": non_exact_macro,
        "macro_loss_drivers": drivers,
        "n_errors": len(cause_rows),
        "n_family_rows": len(golds),
        "next_action": _next_action(decision["decision"]),
        "per_family": family_metrics,
        "prediction_hubs": hubs,
        "prose_macro_f1": surface_macro_f1(
            golds, residual_preds, surfaces, labels, SURFACE_PROSE
        ),
        "prototype_family_macro_f1": non_exact_macro,
        "prototype_vs_residual": proto_compare,
        "rule": RULE,
        "schema": SCHEMA,
        "smallest_justified_remediation": decision["smallest_justified_remediation"],
        "social_evaluation": se_audit,
    }
    artifact["artifact_sha256"] = sha256_text(canonical_json(artifact))
    return artifact


def _next_action(decision: str) -> str:
    mapping = {
        "SCORER_REPAIR_JUSTIFIED": (
            "APPLY_FORWARD_HUB_SCORER_REPAIR — hub-aware / residual-head repair only; "
            "do not score reserve; do not move BEST."
        ),
        "DATA_REMEDIATION_JUSTIFIED": (
            "APPLY_FORWARD_FAMILY_SUPPORT_REMEDIATION — raise support for zero-F1 "
            "families; do not score reserve; do not move BEST."
        ),
        "ONTOLOGY_REMEDIATION_JUSTIFIED": (
            "APPLY_SOCIAL_EVALUATION_BOUNDARY_REMEDIATION — refine SE merge/hub "
            "boundary (esp. relationship-dating); do not score reserve; do not move BEST."
        ),
        "ENCODER_REMEDIATION_JUSTIFIED": (
            "APPLY_ENCODER_GEOMETRY_REPAIR — frozen-core geometry pass; do not score "
            "reserve; do not move BEST."
        ),
        "RESERVE_EVAL_JUSTIFIED": (
            "OPERATOR_AUTHORIZE_RESERVE_EVAL — explicit reserve score only after "
            "operator authorization; do not move BEST."
        ),
        "STOP_NO_CLEAR_REMEDIATION": (
            "STOP — no clear remediation; do not train; do not score reserve; "
            "do not move BEST."
        ),
    }
    return mapping[decision]


def score_validation_bundle_from_tensors(
    *,
    labels: Sequence[str],
    residual_logits: Sequence[Sequence[float]],
    prototype_logits: Sequence[Sequence[float]],
    golds: Sequence[str],
    texts: Sequence[str],
    evidence_classes: Sequence[str],
    initialization_by_family: Mapping[str, str],
    overlap_pairs: Sequence[Mapping[str, Any]],
    train_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """CPU-side assembly helper used by the Spark runner after CUDA inference."""
    index_of = {name: index for index, name in enumerate(labels)}
    residual_preds = []
    prototype_preds = []
    residual_ranks = []
    prototype_ranks = []
    surfaces = []
    for gold, residual, prototype, text in zip(
        golds, residual_logits, prototype_logits, texts, strict=True
    ):
        residual_preds.append(labels[max(range(len(residual)), key=residual.__getitem__)])
        prototype_preds.append(
            labels[max(range(len(prototype)), key=prototype.__getitem__)]
        )
        residual_ranks.append(logit_rank(residual, index_of[gold]))
        prototype_ranks.append(logit_rank(prototype, index_of[gold]))
        surfaces.append(surface_form(text))
    return assemble_error_decomposition(
        {
            "evidence_classes": evidence_classes,
            "golds": golds,
            "initialization_by_family": initialization_by_family,
            "labels": labels,
            "overlap_pairs": overlap_pairs,
            "prototype_preds": prototype_preds,
            "prototype_ranks": prototype_ranks,
            "residual_logits": residual_logits,
            "residual_preds": residual_preds,
            "residual_ranks": residual_ranks,
            "surfaces": surfaces,
            "train_rows": train_rows,
        }
    )
