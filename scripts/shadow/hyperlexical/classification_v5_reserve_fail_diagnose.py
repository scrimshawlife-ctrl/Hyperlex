"""PRESERVE_RESERVE_FAIL_AND_DIAGNOSE_V5_GENERALIZATION — read-only.

Compares frozen STAGE_A_BEST / Stage-B validation behavior against the spent
HYPERLEX_V5_PROMOTION_RESERVE_001 receipt. Does not train, recalibrate,
rebuild the index, reuse reserve rows as optimization data, or move BEST.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v2_surface import SURFACE_ATOM, SURFACE_PROSE, surface_form, word_count
from .classification_v5_promotion_reserve import (
    MINIMUM_FAMILY_MARGIN,
    MINIMUM_FAMILY_SCORE,
    RESERVE_ID,
    STAGE_B_INDEX_SHA256,
    classify_wrong_family_emission,
)
from .classification_v5_stage_a_two_stage_promote import (
    CANONICAL_GATE1_THRESHOLD,
    CANONICAL_GATE2_THRESHOLD,
    MODEL_WIDE_BEST_SHA256,
    STAGE_A_BEST_SHA256,
)
from .classification_v5_stage_b import compose_end_to_end
from .classification_v5_stage_a import canonical_json, sha256_text

DIAGNOSE_RULE = "HYPERLEX_V5_RESERVE_FAIL_GENERALIZATION_DIAGNOSE_V1"
SCHEMA = "hyperlex.classification.v5.reserve_fail_generalization_diagnose.v1"
ACTION = "PRESERVE_RESERVE_FAIL_AND_DIAGNOSE_V5_GENERALIZATION"

# Preregistered on V1R9 validation nearest-train similarity (P5 / P20).
# Computed once from admissible validation vs train embeddings; not fitted on reserve.
OOD_RULE = {
    "in_distribution_min": 0.78,
    "near_distribution_min": 0.62,
    "method": "nearest_train_cosine",
    "preregistered_on": "V1R9_validation_vs_train",
    "note": (
        "IN_DISTRIBUTION if nearest_train_sim >= 0.78; "
        "NEAR_DISTRIBUTION if >= 0.62; else OUT_OF_DISTRIBUTION. "
        "Thresholds frozen from validation nearest-train similarity P20/P5 band."
    ),
}

PRESERVATION = {
    "V5_PROMOTION_RESERVE_001": "SPENT",
    "V5_PROMOTION_RESULT": "RESERVE_FAIL",
    "production_promotion": "REJECTED",
    "evaluation_spent": True,
    "reserve_id": RESERVE_ID,
    "reuse_as_train": False,
    "reuse_as_validation": False,
    "reuse_as_calibration": False,
    "reuse_as_index": False,
    "retune_thresholds": False,
    "rebuild_index": False,
    "move_STAGE_A_BEST": False,
    "move_MODEL_WIDE_BEST": False,
}

DISPLAY_VAL_STAGE_A = {
    "false_entry": 0.0423,
    "PRESENT_recall": 0.7049,
    "NONE_recall": 0.9089,
    "UNCERTAIN_recall": 0.6790,
}


def length_bucket(text: str) -> str:
    wc = word_count(text)
    if wc <= 2:
        return "1-2"
    if wc <= 5:
        return "3-5"
    if wc <= 12:
        return "6-12"
    return "13+"


def atom_prose(text: str) -> str:
    form = surface_form(text)
    if form in {SURFACE_ATOM, SURFACE_PROSE}:
        return form
    return "AMBIGUOUS_FORM"


def source_family(row: Mapping[str, Any]) -> str:
    notes = str(row.get("notes") or "")
    if notes.startswith("v5_reserve_wikt"):
        return "wiktionary_acquire"
    if notes.startswith("v5_reserve_topup") or notes.startswith("v5_reserve_fill"):
        return "synthetic_fill"
    if notes.startswith("v5_uncertain") or "uncertain" in notes:
        return "uncertain_acquire"
    if row.get("source_url"):
        url = str(row["source_url"])
        if "wiktionary.org" in url:
            return "wiktionary"
        if "wikipedia.org" in url:
            return "wikipedia"
    rights = str(row.get("rights") or "")
    if rights == "internal-synthetic":
        return "synthetic_fill"
    return "hub_or_surface"


def cohort_keys(row: Mapping[str, Any]) -> dict[str, str]:
    family = None
    if row.get("gold_family"):
        family = str(row["gold_family"])
    elif row.get("candidate_families"):
        family = str(row["candidate_families"][0])
    return {
        "provenance": str(row.get("provenance") or "UNKNOWN"),
        "none_subtype": str(row.get("evidence_subtype") or "UNKNOWN")
        if row.get("evidence_label") == "NO_EVIDENCE"
        else "NA",
        "family_or_domain": family
        or str(row.get("topic_domain") or row.get("evidence_subtype") or "UNKNOWN"),
        "atom_prose": atom_prose(str(row.get("text") or "")),
        "length_bucket": length_bucket(str(row.get("text") or "")),
        "source_family": source_family(row),
        "label_authority": str(row.get("label_authority") or "UNKNOWN"),
        "label_derivation": str(row.get("label_derivation") or "UNKNOWN"),
    }


def route_present(p_possible: float, p_confirmed: float, decision: str) -> str:
    if decision == "EVIDENCE_PRESENT":
        return "CORRECT_PRESENT"
    if float(p_possible) < CANONICAL_GATE1_THRESHOLD:
        return "BLOCKED_AT_GATE1"
    return "PASSED_GATE1_REJECTED_GATE2"


def route_none(decision: str) -> str:
    if decision == "NO_EVIDENCE":
        return "CORRECT_NONE"
    if decision == "UNCERTAIN":
        return "LEAKED_GATE1_TO_UNCERTAIN"
    return "LEAKED_GATE1_TO_PRESENT"


def route_uncertain(decision: str) -> str:
    if decision == "UNCERTAIN":
        return "CORRECT_UNCERTAIN"
    if decision == "NO_EVIDENCE":
        return "BLOCKED_AS_NONE"
    return "PROMOTED_PRESENT"


def classify_distribution(nearest_train_sim: float) -> str:
    if nearest_train_sim >= OOD_RULE["in_distribution_min"]:
        return "IN_DISTRIBUTION"
    if nearest_train_sim >= OOD_RULE["near_distribution_min"]:
        return "NEAR_DISTRIBUTION"
    return "OUT_OF_DISTRIBUTION"


def _safe_rate(num: int, den: int) -> float | None:
    if den <= 0:
        return None
    return num / den


def label_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by = {"NO_EVIDENCE": [], "EVIDENCE_PRESENT": [], "UNCERTAIN": []}
    for row in rows:
        by[str(row["evidence_label"])].append(row)
    def recall(label: str) -> float | None:
        bucket = by[label]
        if not bucket:
            return None
        return sum(1 for r in bucket if r["evidence_decision"] == label) / len(bucket)

    none = by["NO_EVIDENCE"]
    false_entry = _safe_rate(
        sum(1 for r in none if r["evidence_decision"] == "EVIDENCE_PRESENT"),
        len(none),
    )
    return {
        "false_entry": false_entry,
        "PRESENT_recall": recall("EVIDENCE_PRESENT"),
        "NONE_recall": recall("NO_EVIDENCE"),
        "UNCERTAIN_recall": recall("UNCERTAIN"),
        "n_none": len(none),
        "n_present": len(by["EVIDENCE_PRESENT"]),
        "n_uncertain": len(by["UNCERTAIN"]),
        "n": len(rows),
    }


def cohort_shift_table(
    validation_rows: Sequence[Mapping[str, Any]],
    reserve_rows: Sequence[Mapping[str, Any]],
    *,
    gold_label: str,
    error_pred: str,
) -> list[dict[str, Any]]:
    """Per-cohort support + error rates for one gold Stage-A label."""

    def _bucket(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
        out: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for row in rows:
            if row.get("evidence_label") != gold_label:
                continue
            keys = cohort_keys(row)
            for axis, value in keys.items():
                out[f"{axis}={value}"].append(row)
            out["ALL"].append(row)
        return out

    val_b = _bucket(validation_rows)
    res_b = _bucket(reserve_rows)
    keys = sorted(set(val_b) | set(res_b))
    table = []
    for key in keys:
        v = val_b.get(key) or []
        r = res_b.get(key) or []
        v_err = sum(1 for row in v if row.get("evidence_decision") == error_pred)
        r_err = sum(1 for row in r if row.get("evidence_decision") == error_pred)
        v_hit = sum(1 for row in v if row.get("evidence_decision") == gold_label)
        r_hit = sum(1 for row in r if row.get("evidence_decision") == gold_label)
        v_err_rate = _safe_rate(v_err, len(v))
        r_err_rate = _safe_rate(r_err, len(r))
        v_recall = _safe_rate(v_hit, len(v))
        r_recall = _safe_rate(r_hit, len(r))
        table.append(
            {
                "cohort": key,
                "validation_support": len(v),
                "reserve_support": len(r),
                "validation_error_rate": v_err_rate,
                "reserve_error_rate": r_err_rate,
                "error_rate_delta": None
                if v_err_rate is None or r_err_rate is None
                else r_err_rate - v_err_rate,
                "validation_recall": v_recall,
                "reserve_recall": r_recall,
                "recall_delta": None
                if v_recall is None or r_recall is None
                else r_recall - v_recall,
                "reserve_error_count": r_err,
                "validation_error_count": v_err,
            }
        )
    table.sort(
        key=lambda item: (
            -(item["reserve_error_count"] or 0),
            -(item["reserve_support"] or 0),
            item["cohort"],
        )
    )
    return table


def routing_breakdown(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    present = Counter()
    none = Counter()
    uncertain = Counter()
    present_cohorts: Counter[str] = Counter()
    none_cohorts: Counter[str] = Counter()
    uncertain_cohorts: Counter[str] = Counter()
    for row in rows:
        label = str(row["evidence_label"])
        decision = str(row["evidence_decision"])
        keys = cohort_keys(row)
        dominant = (
            f"subtype={row.get('evidence_subtype')}|prov={keys['provenance']}|"
            f"form={keys['atom_prose']}|src={keys['source_family']}"
        )
        if label == "EVIDENCE_PRESENT":
            route = route_present(
                float(row["p_possible"]), float(row["p_confirmed"]), decision
            )
            present[route] += 1
            if route != "CORRECT_PRESENT":
                present_cohorts[f"{route}|{dominant}"] += 1
        elif label == "NO_EVIDENCE":
            route = route_none(decision)
            none[route] += 1
            if route != "CORRECT_NONE":
                none_cohorts[f"{route}|{dominant}"] += 1
        else:
            route = route_uncertain(decision)
            uncertain[route] += 1
            if route != "CORRECT_UNCERTAIN":
                uncertain_cohorts[f"{route}|{dominant}"] += 1
    return {
        "PRESENT": dict(present),
        "NONE": dict(none),
        "UNCERTAIN": dict(uncertain),
        "dominant_PRESENT_failure_cohorts": present_cohorts.most_common(12),
        "dominant_NONE_failure_cohorts": none_cohorts.most_common(12),
        "dominant_UNCERTAIN_failure_cohorts": uncertain_cohorts.most_common(12),
    }


def representation_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    def _stats(values: Sequence[float]) -> dict[str, float | None]:
        if not values:
            return {"n": 0, "mean": None, "p10": None, "p50": None, "p90": None}
        ordered = sorted(values)
        def pct(p: float) -> float:
            idx = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * p))))
            return ordered[idx]
        return {
            "n": len(ordered),
            "mean": sum(ordered) / len(ordered),
            "p10": pct(0.10),
            "p50": pct(0.50),
            "p90": pct(0.90),
        }

    dist = Counter(str(row.get("distribution_class") or "UNKNOWN") for row in rows)
    return {
        "p_possible": _stats([float(r["p_possible"]) for r in rows]),
        "p_confirmed": _stats([float(r["p_confirmed"]) for r in rows]),
        "gate1_margin": _stats(
            [float(r["p_possible"]) - CANONICAL_GATE1_THRESHOLD for r in rows]
        ),
        "gate2_margin": _stats(
            [float(r["p_confirmed"]) - CANONICAL_GATE2_THRESHOLD for r in rows]
        ),
        "nearest_train_similarity": _stats(
            [float(r["nearest_train_sim"]) for r in rows if r.get("nearest_train_sim") is not None]
        ),
        "nearest_validation_similarity": _stats(
            [
                float(r["nearest_validation_sim"])
                for r in rows
                if r.get("nearest_validation_sim") is not None
            ]
        ),
        "distribution_class_counts": dict(sorted(dist.items())),
        "ood_rule": dict(OOD_RULE),
    }


def stage_b_on_correct_present(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    admitted = [
        row
        for row in rows
        if row.get("evidence_label") == "EVIDENCE_PRESENT"
        and row.get("evidence_decision") == "EVIDENCE_PRESENT"
    ]
    decisions = []
    correct_top1 = 0
    correct_top2 = 0
    emitted = 0
    emitted_correct = 0
    scores = []
    margins = []
    details = []
    for row in admitted:
        candidates = [
            {"family": row["top1_family"], "score": row["top1_score"]},
            {"family": row["top2_family"], "score": row["top2_score"]},
        ]
        if row.get("top3_family") is not None:
            candidates.append({"family": row["top3_family"], "score": row["top3_score"]})
        decided = compose_end_to_end(
            evidence_decision="EVIDENCE_PRESENT",
            ranked_candidates=candidates,
            family_score_min=MINIMUM_FAMILY_SCORE,
            family_margin_min=MINIMUM_FAMILY_MARGIN,
        )
        decisions.append(decided)
        gold = row.get("gold_family")
        if row.get("top1_family") == gold:
            correct_top1 += 1
        if gold in {row.get("top1_family"), row.get("top2_family")}:
            correct_top2 += 1
        score = float(row["top1_score"]) if row.get("top1_score") is not None else None
        margin = None
        if row.get("top1_score") is not None and row.get("top2_score") is not None:
            margin = float(row["top1_score"]) - float(row["top2_score"])
        if score is not None:
            scores.append(score)
        if margin is not None:
            margins.append(margin)
        if decided["decision_type"] == "FAMILY":
            emitted += 1
            if decided.get("family") == gold:
                emitted_correct += 1
        details.append(
            {
                "identity": row["identity"],
                "gold_family": gold,
                "top1_family": row.get("top1_family"),
                "top1_score": row.get("top1_score"),
                "top2_family": row.get("top2_family"),
                "top2_score": row.get("top2_score"),
                "margin": margin,
                "correct_top1": row.get("top1_family") == gold,
                "decision_type": decided["decision_type"],
                "emitted_family": decided.get("family"),
            }
        )

    def _dist(vals: Sequence[float]) -> dict[str, float | None]:
        if not vals:
            return {"n": 0, "mean": None, "p50": None}
        ordered = sorted(vals)
        mid = ordered[len(ordered) // 2]
        return {"n": len(ordered), "mean": sum(ordered) / len(ordered), "p50": mid}

    n = len(admitted)
    return {
        "n_correct_stage_a_present": n,
        "top1_accuracy": _safe_rate(correct_top1, n),
        "top2_accuracy": _safe_rate(correct_top2, n),
        "family_emission_precision": _safe_rate(emitted_correct, emitted),
        "family_emission_coverage": _safe_rate(emitted, n),
        "score_distribution": _dist(scores),
        "margin_distribution": _dist(margins),
        "decision_counts": dict(Counter(d["decision_type"] for d in decisions)),
        "rows": details,
    }


def family_coverage_audit(
    reserve_rows: Sequence[Mapping[str, Any]],
    *,
    index_family_counts: Mapping[str, int],
    validation_family_counts: Mapping[str, int],
    stage_b_correct_present: Mapping[str, Any],
) -> list[dict[str, Any]]:
    by_detail = {
        str(row["identity"]): row for row in stage_b_correct_present.get("rows") or []
    }
    support: Counter[str] = Counter()
    nearest: dict[str, list[float]] = defaultdict(list)
    emitted: Counter[str] = Counter()
    emitted_correct: Counter[str] = Counter()
    for row in reserve_rows:
        if row.get("evidence_label") != "EVIDENCE_PRESENT":
            continue
        family = str(row.get("gold_family") or "")
        if not family:
            continue
        support[family] += 1
        if row.get("nearest_index_family_sim") is not None:
            nearest[family].append(float(row["nearest_index_family_sim"]))
        detail = by_detail.get(str(row["identity"]))
        if detail and detail.get("decision_type") == "FAMILY":
            emitted[family] += 1
            if detail.get("emitted_family") == family:
                emitted_correct[family] += 1
    families = sorted(
        set(support)
        | set(index_family_counts)
        | set(validation_family_counts)
        | set(emitted)
    )
    out = []
    for family in families:
        sims = nearest.get(family) or []
        mean_sim = sum(sims) / len(sims) if sims else None
        flags = []
        idx_n = int(index_family_counts.get(family, 0))
        if idx_n < 10:
            flags.append("LOW_INDEX_SUPPORT")
        if mean_sim is not None and mean_sim < OOD_RULE["near_distribution_min"]:
            flags.append("DOMAIN_SHIFT")
        if support[family] and emitted[family] == 0 and emitted_correct[family] == 0:
            # no emission of this family from correct-present rows with this gold
            gold_emitted = sum(
                1
                for row in (stage_b_correct_present.get("rows") or [])
                if row.get("gold_family") == family and row.get("decision_type") == "FAMILY"
            )
            if gold_emitted == 0:
                flags.append("NO_EMISSION")
        # GOOD_RETRIEVAL_BAD_MARGIN / WRONG_NEAREST_FAMILY from correct-present details
        wrong_nn = 0
        good_ret_bad_margin = 0
        for row in stage_b_correct_present.get("rows") or []:
            if row.get("gold_family") != family:
                continue
            if row.get("top1_family") != family and row.get("top1_score") is not None:
                wrong_nn += 1
            if (
                row.get("top1_family") == family
                and row.get("decision_type") != "FAMILY"
                and row.get("margin") is not None
                and float(row["margin"]) < MINIMUM_FAMILY_MARGIN
            ):
                good_ret_bad_margin += 1
        if wrong_nn:
            flags.append("WRONG_NEAREST_FAMILY")
        if good_ret_bad_margin:
            flags.append("GOOD_RETRIEVAL_BAD_MARGIN")
        out.append(
            {
                "family": family,
                "reserve_support": int(support.get(family, 0)),
                "index_support": idx_n,
                "validation_support": int(validation_family_counts.get(family, 0)),
                "nearest_exemplar_similarity_mean": mean_sim,
                "emitted_count": int(emitted.get(family, 0)),
                "correct_emitted_count": int(emitted_correct.get(family, 0)),
                "flags": flags,
            }
        )
    out.sort(key=lambda item: (-item["reserve_support"], item["family"]))
    return out


def explain_wrong_emissions(
    wrong_emissions: Sequence[Mapping[str, Any]],
    reserve_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    explained = []
    for item in wrong_emissions:
        identity = str(item["identity"])
        row = reserve_by_id.get(identity) or {}
        classification = str(
            item.get("classification")
            or classify_wrong_family_emission(
                gold_evidence_label=str(item.get("gold_stage_a_label")),
                gold_family=item.get("gold_family"),
                predicted_family=item.get("stage_b_predicted_family"),
            )
        )
        explanation = {
            "identity": identity,
            "classification": classification,
            "gold_stage_a_label": item.get("gold_stage_a_label"),
            "gold_family": item.get("gold_family"),
            "stage_a_decision": item.get("stage_a_decision"),
            "p_possible": item.get("p_possible"),
            "p_confirmed": item.get("p_confirmed"),
            "stage_b_predicted_family": item.get("stage_b_predicted_family"),
            "family_score": item.get("family_score"),
            "runner_up_family": item.get("runner_up_family"),
            "runner_up_score": item.get("runner_up_score"),
            "margin": item.get("margin"),
            "cohort": cohort_keys(row) if row else None,
            "frozen_evidence_note": None,
        }
        if classification == "STAGE_A_FALSE_ENTRY":
            explanation["frozen_evidence_note"] = (
                "Gold NO_EVIDENCE crossed both frozen gates into PRESENT; "
                "Stage-B then emitted a FAMILY under floors 0.64/0.07."
            )
        elif classification == "STAGE_B_WRONG_FAMILY":
            explanation["frozen_evidence_note"] = (
                "Stage A correctly admitted PRESENT; Stage-B top1 disagreed with "
                "gold family under the frozen index/floors."
            )
        else:
            explanation["frozen_evidence_note"] = (
                "Compound path: gold was not a settled PRESENT family emission "
                "target (UNCERTAIN or mismatched Stage-A), yet FAMILY was emitted."
            )
        explained.append(explanation)
    return explained


def decide_generalization_diagnosis(
    *,
    stage_a_val: Mapping[str, Any],
    stage_a_reserve: Mapping[str, Any],
    stage_b_val: Mapping[str, Any],
    stage_b_reserve_correct_present: Mapping[str, Any],
    representation_reserve: Mapping[str, Any],
) -> dict[str, Any]:
    fe_delta = float(stage_a_reserve["false_entry"] or 0) - float(
        stage_a_val["false_entry"] or 0
    )
    present_delta = float(stage_a_reserve["PRESENT_recall"] or 0) - float(
        stage_a_val["PRESENT_recall"] or 0
    )
    none_delta = float(stage_a_reserve["NONE_recall"] or 0) - float(
        stage_a_val["NONE_recall"] or 0
    )
    stage_a_bad = fe_delta >= 0.03 or present_delta <= -0.15 or none_delta <= -0.15

    b_prec_val = stage_b_val.get("family_emission_precision")
    b_prec_res = stage_b_reserve_correct_present.get("family_emission_precision")
    b_top1_val = stage_b_val.get("top1_accuracy")
    b_top1_res = stage_b_reserve_correct_present.get("top1_accuracy")
    stage_b_bad = False
    if b_prec_res is not None and b_prec_val is not None:
        stage_b_bad = stage_b_bad or (float(b_prec_val) - float(b_prec_res) >= 0.10)
    if b_top1_res is not None and b_top1_val is not None:
        stage_b_bad = stage_b_bad or (float(b_top1_val) - float(b_top1_res) >= 0.15)
    if stage_b_reserve_correct_present.get("n_correct_stage_a_present", 0) < 20:
        # Too few correctly routed PRESENT rows → Stage-A starved Stage-B.
        stage_b_starved = True
    else:
        stage_b_starved = False

    ood_share = 0.0
    dist = representation_reserve.get("distribution_class_counts") or {}
    n_rep = sum(int(v) for v in dist.values()) or 1
    ood_share = (
        int(dist.get("OUT_OF_DISTRIBUTION", 0)) + 0.5 * int(dist.get("NEAR_DISTRIBUTION", 0))
    ) / n_rep
    distribution_mismatch = ood_share >= 0.45 and stage_a_bad

    if distribution_mismatch and not stage_b_bad:
        diagnosis = "RESERVE_DISTRIBUTION_MISMATCH"
    elif stage_a_bad and stage_b_bad and not stage_b_starved:
        diagnosis = "COMPOUND_GENERALIZATION_FAILURE"
    elif stage_a_bad and stage_b_bad and stage_b_starved:
        diagnosis = "MIXED_V5_GENERALIZATION_FAILURE"
    elif stage_a_bad and not stage_b_bad:
        diagnosis = "STAGE_A_GENERALIZATION_FAILURE"
    elif stage_b_bad and not stage_a_bad:
        diagnosis = "STAGE_B_GENERALIZATION_FAILURE"
    elif stage_a_bad and stage_b_starved:
        diagnosis = "STAGE_A_GENERALIZATION_FAILURE"
    else:
        diagnosis = "MIXED_V5_GENERALIZATION_FAILURE"

    remediation = {
        "STAGE_A_GENERALIZATION_FAILURE": "NEW_STAGE_A_TRAINING_SURFACE",
        "STAGE_B_GENERALIZATION_FAILURE": "NEW_STAGE_B_INDEX_SURFACE",
        "COMPOUND_GENERALIZATION_FAILURE": "NEW_STAGE_A_TRAINING_SURFACE",
        "RESERVE_DISTRIBUTION_MISMATCH": "NEW_STAGE_A_TRAINING_SURFACE",
        "MIXED_V5_GENERALIZATION_FAILURE": "NEW_STAGE_A_TRAINING_SURFACE",
    }[diagnosis]

    return {
        "diagnosis": diagnosis,
        "remediation": remediation,
        "stage_a_bad": stage_a_bad,
        "stage_b_bad": stage_b_bad,
        "stage_b_starved_by_stage_a": stage_b_starved,
        "distribution_mismatch": distribution_mismatch,
        "deltas": {
            "false_entry": fe_delta,
            "PRESENT_recall": present_delta,
            "NONE_recall": none_delta,
        },
        "dataset_change_justified": remediation
        in {"NEW_STAGE_A_TRAINING_SURFACE", "NEW_STAGE_B_INDEX_SURFACE"},
        "architecture_change_justified": False,
        "stage_b_index_change_justified": remediation == "NEW_STAGE_B_INDEX_SURFACE"
        or diagnosis
        in {"COMPOUND_GENERALIZATION_FAILURE", "STAGE_B_GENERALIZATION_FAILURE"},
    }


def next_action_for_diagnosis(diagnosis_payload: Mapping[str, Any]) -> str:
    rem = diagnosis_payload["remediation"]
    diag = diagnosis_payload["diagnosis"]
    return (
        f"{rem} — diagnosis={diag}; preserve spent reserve; do not retune "
        f"0.75/0.50 or 0.64/0.07; do not train on reserve mistakes; "
        f"do not add reserve identities to the Stage-B index."
    )


def assemble_diagnose_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    receipt = {
        "ACTION": ACTION,
        "BEST": "UNCHANGED",
        "BEST_MUTATED": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_A_BEST_MUTATED": False,
        "TRAIN": False,
        "recalibrate": False,
        "rebuild_index": False,
        "reserve_id": RESERVE_ID,
        "rule": DIAGNOSE_RULE,
        "schema": SCHEMA,
        "stage_b_index_sha256": STAGE_B_INDEX_SHA256,
        "preservation": dict(PRESERVATION),
        "frozen_thresholds": {
            "gate1_threshold": CANONICAL_GATE1_THRESHOLD,
            "gate2_threshold": CANONICAL_GATE2_THRESHOLD,
            "minimum_family_score": MINIMUM_FAMILY_SCORE,
            "minimum_family_margin": MINIMUM_FAMILY_MARGIN,
        },
        "ood_rule": dict(OOD_RULE),
        "stage_a": payload["stage_a"],
        "routing": payload["routing"],
        "representation": payload["representation"],
        "stage_b": payload["stage_b"],
        "family_coverage": payload["family_coverage"],
        "wrong_emissions": payload["wrong_emissions"],
        "diagnosis": payload["diagnosis"],
        "next_action": payload["next_action"],
        "reserve_hashes": payload["reserve_hashes"],
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    return receipt
