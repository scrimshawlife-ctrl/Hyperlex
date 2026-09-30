"""Stage B retrieval wired behind Stage A EVIDENCE_PRESENT.

Composes Stage A → B → C on the v3 evidence surface. Does not train Stage A,
does not score a fresh reserve, does not reuse the spent v2 reserve, and does
not move BEST.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping, Sequence

from .classification_v2 import ACTIVE_FAMILY_VOCABULARY
from .classification_v2_family_retrieval import (
    EMISSION_PRECISION_MIN,
    MARGIN_THRESHOLD_GRID,
    SCORE_THRESHOLD_GRID,
    build_index_records,
    family_scores,
)
from .classification_v3_evidence_gate import (
    FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
    FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
    RULE,
    compose_decision,
    may_invoke_retrieval,
    validate_end_to_end_invariants,
)
from .classification_v3_evidence_surface import SURFACE_RULE
from .classification_v3_stage_a import STAGE_A_RULE
STAGE_B_RULE = "HYPERLEX_CLASSIFICATION_V3_STAGE_B_RETRIEVAL_V1"
FROZEN_STAGE_A_THRESHOLDS = {
    "none_threshold": 0.05,
    "present_threshold": 0.55,
}
STAGE_A_CHECKPOINT_SHA = (
    "0b7dbdac1f39e7b7ede1e51e86b9b938aa68e95692bf4b2f062329d487420ce7"
)
SURFACE_DATASET_SHA = (
    "7339c044596a4cc2eb5ae17f3fbab185fface9abffb6151bdb0db69eca0d2d3a"
)


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stage_b_contract() -> dict[str, Any]:
    return {
        "best": "UNCHANGED",
        "emission_precision_min": FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
        "false_evidence_entry_rate_on_none_max": FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
        "frozen_stage_a_thresholds": dict(FROZEN_STAGE_A_THRESHOLDS),
        "parent_rule": RULE,
        "retrieval_only_on": "EVIDENCE_PRESENT",
        "rule": STAGE_B_RULE,
        "stage_a_rule": STAGE_A_RULE,
        "surface_rule": SURFACE_RULE,
        "train": False,
        "v3_reserve": None,
    }


def gold_end_to_end(row: Mapping[str, Any]) -> dict[str, Any]:
    subtype = str(row["evidence_subtype"])
    if subtype == "POSITIVE_EVIDENCE":
        families = list(row.get("candidate_families") or [])
        if not families:
            raise ValueError("positive_without_family")
        return {"decision_type": "FAMILY", "family": str(families[0])}
    if subtype == "AMBIGUOUS_EVIDENCE":
        return {"decision_type": "ABSTAIN", "family": None}
    if subtype in {"HARD_NONE", "NEAR_DOMAIN_NONE", "GENERIC_NONE"}:
        return {"decision_type": "NONE", "family": None}
    raise ValueError(f"unknown_subtype:{subtype}")


def gold_lineage_for_retrieval(row: Mapping[str, Any]) -> str | None:
    gold = gold_end_to_end(row)
    if gold["decision_type"] == "FAMILY":
        return gold["family"]
    return None


def is_index_positive_row(row: Mapping[str, Any]) -> bool:
    return (
        row.get("split") == "train"
        and row.get("evidence_subtype") == "POSITIVE_EVIDENCE"
        and bool(row.get("candidate_families"))
        and str(row["candidate_families"][0]) in ACTIVE_FAMILY_VOCABULARY
        and bool(str(row.get("text") or "").strip())
    )


def surface_rows_to_index_source(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Map evidence-surface positives into the v2 index row shape."""
    out = []
    for row in rows:
        if not is_index_positive_row(row):
            continue
        out.append(
            {
                "class": row.get("provenance") or "OBSERVED",
                "lineage": str(row["candidate_families"][0]),
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": str(row["text"]),
                "jev": "OFF",
                "evaluation_reserve": False,
                "held_out": False,
            }
        )
    return out


def build_stage_b_index(
    surface_rows: Sequence[Mapping[str, Any]],
    embeddings_by_identity: Mapping[str, Sequence[float]],
) -> dict[str, Any]:
    source = surface_rows_to_index_source(surface_rows)
    index = build_index_records(source, embeddings_by_identity)
    index["rule"] = STAGE_B_RULE
    index["surface_rule"] = SURFACE_RULE
    index["surface_dataset_sha256"] = SURFACE_DATASET_SHA
    index["stage_a_checkpoint_sha256"] = STAGE_A_CHECKPOINT_SHA
    bare = {key: value for key, value in index.items() if key != "index_sha256"}
    index["index_sha256"] = sha256_text(canonical_json(bare))
    return index


def compose_end_to_end(
    *,
    evidence_decision: str,
    ranked_candidates: Sequence[Mapping[str, Any]] | None,
    family_score_min: float,
    family_margin_min: float,
) -> dict[str, Any]:
    candidates = None
    if may_invoke_retrieval(evidence_decision):
        candidates = list(ranked_candidates or [])
    decision = compose_decision(
        evidence_decision=evidence_decision,
        candidates=candidates,
        family_score_min=family_score_min,
        family_margin_min=family_margin_min,
    )
    validate_end_to_end_invariants(decision, evidence_decision)
    return decision


def _stage_a_false_entry(rows: Sequence[Mapping[str, Any]]) -> float:
    none_idx = [
        i for i, row in enumerate(rows) if row.get("evidence_label") == "NO_EVIDENCE"
    ]
    if not none_idx:
        return 0.0
    hits = sum(
        1 for i in none_idx if rows[i].get("evidence_decision") == "EVIDENCE_PRESENT"
    )
    return hits / len(none_idx)


def _metrics_from_decisions(
    rows: Sequence[Mapping[str, Any]],
    decisions: Sequence[Mapping[str, Any]],
    *,
    false_entry: float,
    primary_pass: bool,
) -> dict[str, Any]:
    family_emitted = 0
    family_correct = 0
    n_present_gold = 0
    selective_correct = 0
    selective_total = 0
    none_tp = none_fp = none_fn = 0
    decision_counts: Counter[str] = Counter()
    for row, decided in zip(rows, decisions):
        gold_type = row["gold_decision_type"]
        gold_family = row.get("gold_family")
        if gold_type == "FAMILY":
            n_present_gold += 1
        decision_counts[str(decided["decision_type"])] += 1
        if decided["decision_type"] == "FAMILY":
            family_emitted += 1
            if gold_family == decided.get("family"):
                family_correct += 1
        if decided["decision_type"] in {"FAMILY", "NONE"}:
            selective_total += 1
            if (
                decided["decision_type"] == gold_type
                and decided.get("family") == gold_family
            ):
                selective_correct += 1
        if decided["decision_type"] == "NONE" and gold_type == "NONE":
            none_tp += 1
        elif decided["decision_type"] == "NONE" and gold_type != "NONE":
            none_fp += 1
        elif decided["decision_type"] != "NONE" and gold_type == "NONE":
            none_fn += 1
    family_precision = None if family_emitted == 0 else family_correct / family_emitted
    family_coverage = None if n_present_gold == 0 else family_emitted / n_present_gold
    family_recall = None if n_present_gold == 0 else family_correct / n_present_gold
    none_precision = none_tp / (none_tp + none_fp) if (none_tp + none_fp) else 0.0
    none_recall = none_tp / (none_tp + none_fn) if (none_tp + none_fn) else 0.0
    selective_accuracy = (
        None if selective_total == 0 else selective_correct / selective_total
    )
    secondary_pass = (
        primary_pass
        and family_precision is not None
        and family_precision + 1e-12 >= FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE
    )
    uncertain_rate = sum(
        1 for row in rows if row.get("evidence_decision") == "UNCERTAIN"
    ) / max(1, len(rows))
    return {
        "decision_counts": dict(decision_counts),
        "false_evidence_entry_rate_on_none": false_entry,
        "family_emission_coverage": family_coverage,
        "family_emission_precision": family_precision,
        "family_emission_recall": family_recall,
        "n": len(rows),
        "n_family_emitted": family_emitted,
        "n_present_gold": n_present_gold,
        "none_precision": none_precision,
        "none_recall": none_recall,
        "primary_gate_max": FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
        "primary_gate_pass": primary_pass,
        "secondary_gate_min": FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
        "secondary_gate_pass": secondary_pass,
        "selective_accuracy": selective_accuracy,
        "uncertain_rate": uncertain_rate,
    }


def calibrate_stage_b_thresholds(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Global score/margin sweep. Stage A thresholds stay frozen."""
    false_entry = _stage_a_false_entry(rows)
    primary_pass = false_entry <= FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX
    fixed: list[dict[str, Any] | None] = [None] * len(rows)
    admitted_indices = []
    for index, row in enumerate(rows):
        evidence_decision = str(row["evidence_decision"])
        if evidence_decision == "EVIDENCE_PRESENT":
            admitted_indices.append(index)
            continue
        fixed[index] = compose_end_to_end(
            evidence_decision=evidence_decision,
            ranked_candidates=None,
            family_score_min=0.0,
            family_margin_min=0.0,
        )
    if not admitted_indices:
        decisions = [item for item in fixed if item is not None]
        metrics = _metrics_from_decisions(
            rows, decisions, false_entry=false_entry, primary_pass=primary_pass
        )
        return {
            "feasible": False,
            "false_evidence_entry_rate_on_none": false_entry,
            "minimum_family_score": None,
            "minimum_top1_top2_margin": None,
            "primary_gate_pass": primary_pass,
            "reason": "no_stage_a_present_rows",
            "metrics": metrics,
            "surface": "validation",
            "reserve_used": False,
        }
    best = None
    fallback = None
    for score_threshold in SCORE_THRESHOLD_GRID:
        for margin_threshold in MARGIN_THRESHOLD_GRID:
            decisions: list[Mapping[str, Any]] = []
            for index, row in enumerate(rows):
                fixed_decision = fixed[index]
                if fixed_decision is not None:
                    decisions.append(fixed_decision)
                    continue
                candidates = [
                    {"family": row["top1_family"], "score": row["top1_score"]},
                    {"family": row["top2_family"], "score": row["top2_score"]},
                ]
                if row.get("top3_family") is not None:
                    candidates.append(
                        {"family": row["top3_family"], "score": row["top3_score"]}
                    )
                decisions.append(
                    compose_end_to_end(
                        evidence_decision="EVIDENCE_PRESENT",
                        ranked_candidates=candidates,
                        family_score_min=score_threshold,
                        family_margin_min=margin_threshold,
                    )
                )
            metrics = _metrics_from_decisions(
                rows, decisions, false_entry=false_entry, primary_pass=primary_pass
            )
            precision = metrics["family_emission_precision"]
            if precision is None:
                continue
            candidate = {
                "family_emission_coverage": metrics["family_emission_coverage"],
                "family_emission_precision": precision,
                "family_emission_recall": metrics["family_emission_recall"],
                "minimum_family_score": score_threshold,
                "minimum_top1_top2_margin": margin_threshold,
                "primary_gate_pass": primary_pass,
                "selective_accuracy": metrics["selective_accuracy"],
            }
            rank_fallback = (
                1 if primary_pass else 0,
                float(precision),
                float(metrics["family_emission_recall"] or 0.0),
                float(margin_threshold),
                float(score_threshold),
            )
            if fallback is None or rank_fallback > fallback["rank"]:
                fallback = {**candidate, "rank": rank_fallback}
            if primary_pass and precision + 1e-12 >= EMISSION_PRECISION_MIN:
                rank = (
                    float(metrics["family_emission_recall"] or 0.0),
                    float(metrics["family_emission_coverage"] or 0.0),
                    float(precision),
                    float(margin_threshold),
                    float(score_threshold),
                )
                if best is None or rank > best["rank"]:
                    best = {**candidate, "rank": rank}
    if best is None:
        return {
            "feasible": False,
            "false_evidence_entry_rate_on_none": false_entry,
            "minimum_family_score": None if fallback is None else fallback["minimum_family_score"],
            "minimum_top1_top2_margin": None
            if fallback is None
            else fallback["minimum_top1_top2_margin"],
            "primary_gate_pass": primary_pass,
            "reason": "no_threshold_pair_met_primary_and_emission_floors",
            "fallback": None
            if fallback is None
            else {k: v for k, v in fallback.items() if k != "rank"},
            "surface": "validation",
            "reserve_used": False,
        }
    return {
        "feasible": True,
        "false_evidence_entry_rate_on_none": false_entry,
        "minimum_family_score": best["minimum_family_score"],
        "minimum_top1_top2_margin": best["minimum_top1_top2_margin"],
        "family_emission_precision": best["family_emission_precision"],
        "family_emission_coverage": best["family_emission_coverage"],
        "family_emission_recall": best["family_emission_recall"],
        "primary_gate_pass": primary_pass,
        "selective_accuracy": best["selective_accuracy"],
        "surface": "validation",
        "reserve_used": False,
        "selection_rule": "primary_gate_and_emission_precision_then_max_recall_coverage",
    }


def evaluate_end_to_end(
    rows: Sequence[Mapping[str, Any]],
    *,
    family_score_min: float,
    family_margin_min: float,
) -> dict[str, Any]:
    """rows: evidence_decision, evidence_label/subtype gold, top1/top2, gold helpers."""
    decisions = []
    stage_a_preds = []
    stage_a_golds = []
    none_gold_idx = []
    family_emitted = 0
    family_correct = 0
    n_present_gold = 0
    selective_correct = 0
    selective_total = 0
    none_tp = none_fp = none_fn = 0
    decision_counts: Counter[str] = Counter()

    for index, row in enumerate(rows):
        evidence_decision = str(row["evidence_decision"])
        stage_a_preds.append(evidence_decision)
        stage_a_golds.append(str(row["evidence_label"]))
        if row["evidence_label"] == "NO_EVIDENCE":
            none_gold_idx.append(index)
        gold = {
            "decision_type": row["gold_decision_type"],
            "family": row.get("gold_family"),
        }
        if gold["decision_type"] == "FAMILY":
            n_present_gold += 1
        candidates = [
            {"family": row["top1_family"], "score": row["top1_score"]},
            {"family": row["top2_family"], "score": row["top2_score"]},
        ]
        if row.get("top3_family") is not None:
            candidates.append(
                {"family": row["top3_family"], "score": row["top3_score"]}
            )
        decided = compose_end_to_end(
            evidence_decision=evidence_decision,
            ranked_candidates=candidates if may_invoke_retrieval(evidence_decision) else None,
            family_score_min=family_score_min,
            family_margin_min=family_margin_min,
        )
        decision_counts[str(decided["decision_type"])] += 1
        decisions.append(decided)

        if decided["decision_type"] == "FAMILY":
            family_emitted += 1
            if gold["family"] == decided.get("family"):
                family_correct += 1
        if decided["decision_type"] in {"FAMILY", "NONE"}:
            selective_total += 1
            if (
                decided["decision_type"] == gold["decision_type"]
                and decided.get("family") == gold.get("family")
            ):
                selective_correct += 1
        if decided["decision_type"] == "NONE" and gold["decision_type"] == "NONE":
            none_tp += 1
        elif decided["decision_type"] == "NONE" and gold["decision_type"] != "NONE":
            none_fp += 1
        elif decided["decision_type"] != "NONE" and gold["decision_type"] == "NONE":
            none_fn += 1

    false_entries = sum(
        1 for i in none_gold_idx if stage_a_preds[i] == "EVIDENCE_PRESENT"
    )
    false_entry_rate = false_entries / len(none_gold_idx) if none_gold_idx else 0.0
    family_precision = None if family_emitted == 0 else family_correct / family_emitted
    family_coverage = None if n_present_gold == 0 else family_emitted / n_present_gold
    family_recall = None if n_present_gold == 0 else family_correct / n_present_gold
    none_precision = none_tp / (none_tp + none_fp) if (none_tp + none_fp) else 0.0
    none_recall = none_tp / (none_tp + none_fn) if (none_tp + none_fn) else 0.0
    selective_accuracy = (
        None if selective_total == 0 else selective_correct / selective_total
    )
    primary_pass = false_entry_rate <= FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX
    secondary_pass = (
        primary_pass
        and family_precision is not None
        and family_precision + 1e-12 >= FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE
    )
    return {
        "decision_counts": dict(decision_counts),
        "false_evidence_entry_rate_on_none": false_entry_rate,
        "family_emission_coverage": family_coverage,
        "family_emission_precision": family_precision,
        "family_emission_recall": family_recall,
        "n": len(rows),
        "n_family_emitted": family_emitted,
        "n_present_gold": n_present_gold,
        "none_precision": none_precision,
        "none_recall": none_recall,
        "primary_gate_max": FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
        "primary_gate_pass": primary_pass,
        "secondary_gate_min": FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
        "secondary_gate_pass": secondary_pass,
        "selective_accuracy": selective_accuracy,
        "uncertain_rate": sum(1 for p in stage_a_preds if p == "UNCERTAIN")
        / max(1, len(stage_a_preds)),
    }


def reserve_authorization(metrics: Mapping[str, Any]) -> dict[str, Any]:
    """May authorize sealing a NEW v3 reserve; does not create one."""
    ok = bool(metrics.get("primary_gate_pass")) and bool(
        metrics.get("secondary_gate_pass")
    )
    return {
        "decision": "RESERVE_SEAL_AUTHORIZED" if ok else "RESERVE_SEAL_NOT_AUTHORIZED",
        "primary_gate_pass": bool(metrics.get("primary_gate_pass")),
        "secondary_gate_pass": bool(metrics.get("secondary_gate_pass")),
        "family_emission_precision": metrics.get("family_emission_precision"),
        "false_evidence_entry_rate_on_none": metrics.get(
            "false_evidence_entry_rate_on_none"
        ),
        "v3_reserve_created": False,
        "spent_v2_reserve_used": False,
    }


def next_action_for_stage_b(authorization: Mapping[str, Any]) -> str:
    if authorization.get("decision") == "RESERVE_SEAL_AUTHORIZED":
        return "AUTHORIZE_SEAL_NEW_V3_RESERVE_THEN_ONE_SHOT_SCORE"
    return "DIAGNOSE_STAGE_B_BEFORE_ANY_RESERVE"


def assemble_stage_b_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    receipt = {
        "BEST": "UNCHANGED",
        "authorization": payload["authorization"],
        "best_sha256": payload["best_sha256"],
        "calibration": payload["calibration"],
        "contract": stage_b_contract(),
        "index_sha256": payload["index_sha256"],
        "metrics": payload["metrics"],
        "next_action": payload["next_action"],
        "rule": STAGE_B_RULE,
        "schema": "hyperlex.classification.v3.stage_b_validation.v1",
        "stage_a_checkpoint_sha256": STAGE_A_CHECKPOINT_SHA,
        "stage_a_thresholds": dict(FROZEN_STAGE_A_THRESHOLDS),
        "surface_dataset_sha256": SURFACE_DATASET_SHA,
        "surface_rule": SURFACE_RULE,
        "train": False,
        "v3_reserve": None,
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    return receipt


def retrieval_candidates_from_embedding(
    query_embedding: Sequence[float],
    index_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    ranked = family_scores(query_embedding, index_records)
    return ranked
