"""HYPERLEX_V5_STAGE_B_INTEGRATION_V1 — Stage-B against canonical STAGE_A_BEST.

Wires family retrieval behind the factorized Stage-A canonical contract
(HYPERLEX_V5_STAGE_A_CANONICAL_V1). Does not train Stage-A/B, does not
score reserve, does not mutate BEST, does not rebuild the Stage-B index,
and does not retune score/margin floors.
"""

from __future__ import annotations

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
    compose_decision,
    validate_end_to_end_invariants,
)
from .classification_v5_stage_a import (
    BEST_SHA,
    EVIDENCE_LABELS,
    canonical_json,
    sha256_text,
)
from .classification_v5_stage_a_canonical import (
    CANONICAL_ID,
    MODEL_WIDE_BEST_SHA256,
    PROMOTION_RECEIPT_SHA256,
    STAGE_A_BEST_EPOCH,
    STAGE_A_BEST_SHA256,
    may_invoke_stage_b,
    stage_b_entry_from_stage_a,
)
from .classification_v5_stage_a_factorized_objective import OBJECTIVE_ID
from .classification_v5_stage_a_ident_filtered_promote import (
    CANONICAL_RELATION_THRESHOLD,
    CANONICAL_RESOLVABILITY_THRESHOLD,
)
from .classification_v5_stage_a_ident_filtered_repro_promote import (
    PREVIOUS_STAGE_A_BEST_SHA256,
)
from .classification_v5_stage_a_two_stage import (
    AUTHORIZED_DATASET_SHA,
    AUTHORIZED_SURFACE_RULE,
)

STAGE_B_RULE = "HYPERLEX_V5_STAGE_B_INTEGRATION_V1"
WIRE_ACTION = "WIRE_V5_STAGE_B_RETRIEVAL_ON_STAGE_A_BEST"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-B-001"
SCHEMA_CONTRACT = "hyperlex.classification.v5.stage_b_integration.v1"
SCHEMA_VALIDATION = "hyperlex.classification.v5.stage_b_validation.v1"
# Parent promotion is the REPRO factorized Stage-A promote (not two-stage).
PARENT_PROMOTION_RECEIPT_SHA256 = PROMOTION_RECEIPT_SHA256
PARENT_STAGE_A_EXPERIMENT_ID = (
    "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-REPRO-001"
)
PARENT_STAGE_A_CANONICAL = CANONICAL_ID

# Sealed Stage-B retrieval artifacts — content frozen; only parent pin updates.
FROZEN_INDEX_SHA256 = (
    "3fd6c87a5825f3f2a25a81f1a769a77aa69e03ddca5b370f9247672d93aaee21"
)
FROZEN_MINIMUM_FAMILY_SCORE = 0.64
FROZEN_MINIMUM_TOP1_TOP2_MARGIN = 0.07
INDEX_REBUILT = False
FLOORS_RETUNED = False

# Parent v3 floors are reference-only until V5 validation recalibrates.
PARENT_V3_REFERENCE_FLOORS = {
    "minimum_family_score": 0.96,
    "minimum_top1_top2_margin": 0.01,
    "status": "REFERENCE_ONLY_PENDING_V5_CALIBRATION",
}

FROZEN_STAGE_A = {
    "STAGE_A_BEST": STAGE_A_BEST_SHA256,
    "STAGE_A_BEST_EPOCH": STAGE_A_BEST_EPOCH,
    "STAGE_A_CANONICAL": PARENT_STAGE_A_CANONICAL,
    "architecture": OBJECTIVE_ID,
    "relation_threshold": CANONICAL_RELATION_THRESHOLD,
    "resolvability_threshold": CANONICAL_RESOLVABILITY_THRESHOLD,
    "model_wide_BEST": MODEL_WIDE_BEST_SHA256,
    "promote_rule": "RETRY_PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE",
    "previous_STAGE_A_BEST": PREVIOUS_STAGE_A_BEST_SHA256,
    "previous_STAGE_A_BEST_status": "SUPERSEDED_STAGE_A_BEST",
    # Gate1/Gate2 retained only as historical superseded semantics.
    "deprecated_gate1_gate2": {
        "status": "HISTORICAL",
        "superseded_checkpoint": PREVIOUS_STAGE_A_BEST_SHA256,
        "gate1_threshold": 0.75,
        "gate2_threshold": 0.50,
    },
}


def stage_b_contract() -> dict[str, Any]:
    return {
        "BEST": "UNCHANGED",
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_A_CANONICAL": PARENT_STAGE_A_CANONICAL,
        "dataset_sha256": AUTHORIZED_DATASET_SHA,
        "emission_precision_min": FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
        "entry_invariant": {
            "EVIDENCE_PRESENT": "PERMIT_STAGE_B",
            "NO_EVIDENCE": "STOP",
            "UNCERTAIN": "ABSTAIN",
            "rule": "Stage B may execute only when Stage A == EVIDENCE_PRESENT",
        },
        "experiment_id": EXPERIMENT_ID,
        "false_evidence_entry_rate_on_none_max": FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
        "floors_retuned": FLOORS_RETUNED,
        "frozen_index_sha256": FROZEN_INDEX_SHA256,
        "frozen_stage_a": dict(FROZEN_STAGE_A),
        "index_rebuilt": INDEX_REBUILT,
        "minimum_family_score": FROZEN_MINIMUM_FAMILY_SCORE,
        "minimum_top1_top2_margin": FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        "parent_promotion_receipt_sha256": PARENT_PROMOTION_RECEIPT_SHA256,
        "parent_stage_a_experiment_id": PARENT_STAGE_A_EXPERIMENT_ID,
        "parent_v3_reference_floors": dict(PARENT_V3_REFERENCE_FLOORS),
        "retrieval_only_on": "EVIDENCE_PRESENT",
        "rule": STAGE_B_RULE,
        "schema": SCHEMA_CONTRACT,
        "semantic_stage_a_labels": list(EVIDENCE_LABELS),
        "surface_rule": AUTHORIZED_SURFACE_RULE,
        "train": False,
        "v5_reserve": None,
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
    if subtype in {
        "HARD_NONE",
        "NEAR_DOMAIN_NONE",
        "GENERIC_NONE",
        "ORDINARY_DOMAIN_NONE",
        "LEXICAL_LOOKALIKE_NONE",
        "SHORT_ATOM_NONE",
    }:
        return {"decision_type": "NONE", "family": None}
    raise ValueError(f"unknown_subtype:{subtype}")


def is_index_positive_row(row: Mapping[str, Any]) -> bool:
    families = list(row.get("candidate_families") or [])
    return (
        row.get("split") == "train"
        and row.get("evidence_subtype") == "POSITIVE_EVIDENCE"
        and row.get("evidence_label") == "EVIDENCE_PRESENT"
        and bool(families)
        and str(families[0]) in ACTIVE_FAMILY_VOCABULARY
        and bool(str(row.get("text") or "").strip())
    )


def surface_rows_to_index_source(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
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


def stage_b_family_vocabulary(
    surface_rows: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    """Families with train POSITIVE_EVIDENCE exemplars on the V5 surface."""
    names = {
        str(row["candidate_families"][0])
        for row in surface_rows
        if is_index_positive_row(row)
    }
    return tuple(sorted(names))


def build_stage_b_index(
    surface_rows: Sequence[Mapping[str, Any]],
    embeddings_by_identity: Mapping[str, Sequence[float]],
) -> dict[str, Any]:
    source = surface_rows_to_index_source(surface_rows)
    vocabulary = stage_b_family_vocabulary(surface_rows)
    if not vocabulary:
        raise ValueError("stage_b_index_empty_vocabulary")
    index = build_index_records(
        source, embeddings_by_identity, family_vocabulary=vocabulary
    )
    index["rule"] = STAGE_B_RULE
    index["surface_rule"] = AUTHORIZED_SURFACE_RULE
    index["surface_dataset_sha256"] = AUTHORIZED_DATASET_SHA
    index["stage_a_best_sha256"] = STAGE_A_BEST_SHA256
    index["model_wide_best_sha256"] = MODEL_WIDE_BEST_SHA256
    index["family_vocabulary"] = list(vocabulary)
    index["active_ontology_size"] = len(ACTIVE_FAMILY_VOCABULARY)
    index["surface_family_count"] = len(vocabulary)
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
    """Stage-B composition gated by promoted Stage-A entry adapter."""
    entry = stage_b_entry_from_stage_a(evidence_decision)
    candidates = None
    if entry["stage_b_permitted"]:
        candidates = list(ranked_candidates or [])
    decision = compose_decision(
        evidence_decision=evidence_decision,
        candidates=candidates,
        family_score_min=family_score_min,
        family_margin_min=family_margin_min,
    )
    validate_end_to_end_invariants(decision, evidence_decision)
    decision["stage_a_entry"] = entry
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
    """Global score/margin sweep. Stage-A thresholds stay frozen at STAGE_A_BEST."""
    false_entry = _stage_a_false_entry(rows)
    primary_pass = false_entry <= FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX
    fixed: list[dict[str, Any] | None] = [None] * len(rows)
    admitted_indices = []
    for index, row in enumerate(rows):
        evidence_decision = str(row["evidence_decision"])
        if may_invoke_stage_b(evidence_decision):
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
            "fallback": None
            if fallback is None
            else {k: v for k, v in fallback.items() if k != "rank"},
            "false_evidence_entry_rate_on_none": false_entry,
            "minimum_family_score": None
            if fallback is None
            else fallback["minimum_family_score"],
            "minimum_top1_top2_margin": None
            if fallback is None
            else fallback["minimum_top1_top2_margin"],
            "primary_gate_pass": primary_pass,
            "reason": "no_feasible_secondary_gate",
            "reserve_used": False,
            "surface": "validation",
        }
    chosen = {k: v for k, v in best.items() if k != "rank"}
    decisions = []
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
                family_score_min=float(chosen["minimum_family_score"]),
                family_margin_min=float(chosen["minimum_top1_top2_margin"]),
            )
        )
    metrics = _metrics_from_decisions(
        rows, decisions, false_entry=false_entry, primary_pass=primary_pass
    )
    return {
        "feasible": True,
        "false_evidence_entry_rate_on_none": false_entry,
        "metrics": metrics,
        "minimum_family_score": chosen["minimum_family_score"],
        "minimum_top1_top2_margin": chosen["minimum_top1_top2_margin"],
        "primary_gate_pass": primary_pass,
        "reserve_used": False,
        "secondary_gate_pass": metrics["secondary_gate_pass"],
        "surface": "validation",
        **chosen,
    }


def evaluate_end_to_end(
    rows: Sequence[Mapping[str, Any]],
    *,
    family_score_min: float,
    family_margin_min: float,
) -> dict[str, Any]:
    false_entry = _stage_a_false_entry(rows)
    primary_pass = false_entry <= FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX
    decisions = []
    for row in rows:
        evidence_decision = str(row["evidence_decision"])
        candidates = None
        if may_invoke_stage_b(evidence_decision):
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
                evidence_decision=evidence_decision,
                ranked_candidates=candidates,
                family_score_min=family_score_min,
                family_margin_min=family_margin_min,
            )
        )
    return _metrics_from_decisions(
        rows, decisions, false_entry=false_entry, primary_pass=primary_pass
    )


def reserve_authorization(metrics: Mapping[str, Any]) -> dict[str, Any]:
    """May authorize sealing a NEW v5 reserve; does not create or score one."""
    ok = bool(metrics.get("primary_gate_pass")) and bool(
        metrics.get("secondary_gate_pass")
    )
    return {
        "decision": "RESERVE_SEAL_AUTHORIZED" if ok else "RESERVE_SEAL_NOT_AUTHORIZED",
        "family_emission_precision": metrics.get("family_emission_precision"),
        "false_evidence_entry_rate_on_none": metrics.get(
            "false_evidence_entry_rate_on_none"
        ),
        "primary_gate_pass": bool(metrics.get("primary_gate_pass")),
        "secondary_gate_pass": bool(metrics.get("secondary_gate_pass")),
        "spent_prior_reserve_used": False,
        "v5_reserve_created": False,
    }


def next_action_for_stage_b(authorization: Mapping[str, Any]) -> str:
    if authorization.get("decision") == "RESERVE_SEAL_AUTHORIZED":
        return "AUTHORIZE_SEAL_NEW_V5_RESERVE_THEN_ONE_SHOT_SCORE"
    return "DIAGNOSE_V5_STAGE_B_BEFORE_ANY_RESERVE"


def retrieval_candidates_from_embedding(
    query_embedding: Sequence[float],
    index_records: Sequence[Mapping[str, Any]],
    *,
    family_vocabulary: Sequence[str] | None = None,
) -> dict[str, Any]:
    return family_scores(
        query_embedding,
        index_records,
        family_vocabulary=family_vocabulary,
    )


def design_freeze_receipt(*, code_revision: str) -> dict[str, Any]:
    payload = {
        "BEST": "UNCHANGED",
        "BEST_SHA256": BEST_SHA,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "NEXT_ACTION": WIRE_ACTION,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_A_PROMOTION_RECEIPT_SHA256": PARENT_PROMOTION_RECEIPT_SHA256,
        "TRAIN": False,
        "code_revision": code_revision,
        "contract": stage_b_contract(),
        "rule": STAGE_B_RULE,
        "schema": "hyperlex.classification.v5.stage_b_design_freeze.v1",
    }
    payload["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in payload.items() if k != "receipt_sha256"})
    )
    return payload


def assemble_stage_b_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    receipt = {
        "BEST": "UNCHANGED",
        "BEST_MUTATED": False,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "RESERVE_CONSUMED": False,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_A_PROMOTION_RECEIPT_SHA256": PARENT_PROMOTION_RECEIPT_SHA256,
        "TRAIN": False,
        "authorization": payload["authorization"],
        "best_sha256": payload["best_sha256"],
        "calibration": payload["calibration"],
        "contract": stage_b_contract(),
        "frozen_stage_a": dict(FROZEN_STAGE_A),
        "index_sha256": payload["index_sha256"],
        "metrics": payload["metrics"],
        "next_action": payload["next_action"],
        "rule": STAGE_B_RULE,
        "schema": SCHEMA_VALIDATION,
        "surface_dataset_sha256": AUTHORIZED_DATASET_SHA,
        "surface_rule": AUTHORIZED_SURFACE_RULE,
        "v5_reserve": None,
        "wire_action": WIRE_ACTION,
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    return receipt
