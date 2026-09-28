"""Preregistered one-sided residual threshold procedure.

This module freezes how a later calibration pass may choose one global
``T_HIGH``. It does not read the 225 development rows, does not draw a
surface, and does not freeze a numeric threshold.
"""

from __future__ import annotations

import math
from decimal import Decimal, ROUND_HALF_EVEN

from hyperlexical.residual_model_resolved_replay_v1 import (
    RESIDUAL_QUANTUM,
    direction_result,
    extreme_driven,
    pair_comparison,
    pos_partitioned,
    tier3_concentration,
)
from hyperlexical.semantic_compositionality_residual import RESIDUAL_QUANTUM as SCORE_QUANTUM

# Same z as hyperlexical.selection_surface.Z95. Wilson 95%.
WILSON_Z95 = Decimal("1.959963984540054")
RATE_QUANTUM = Decimal("0.000001")

RULE = "RUNE.SEMANTIC_COMPOSITIONALITY_THRESHOLD.v1"
TRACK_STATE = "THRESHOLD_PROCEDURE_PREREGISTERED"
ALGORITHM_ID = "residual_threshold_v1.precision_gated_recall_v1"

MIN_CALIBRATION_HIGH = 12
MIN_CALIBRATION_SECONDARY = 8
MIN_PREDICTED_YES = 8
PRECISION_FLOOR = Decimal("0.80")
WILSON_LOWER_FLOOR = Decimal("0.50")
CONFIDENCE_LEVEL = "0.95"
REJECT_PREDICTED_YES_MAX = 0
QUARANTINE_PREDICTED_YES_MAX = 0

# Stated separately from the calibration floors. Measurement success is not
# implied by a calibration pass. The numbers match because both were chosen
# here, before either surface exists.
MIN_MEASUREMENT_HIGH = 12
MIN_MEASUREMENT_SECONDARY = 8
MIN_MEASUREMENT_PREDICTED_YES = 8
MEASUREMENT_PRECISION_FLOOR = Decimal("0.80")
MEASUREMENT_WILSON_LOWER_FLOOR = Decimal("0.50")

OUTPUT_LABELS = ("YES", "UNKNOWN")
COMPARISON_BUCKETS = frozenset({"HIGH", "SECONDARY"})
SAFETY_BUCKETS = frozenset({"REJECT", "QUARANTINE"})
READY = "SCORED"

INSUFFICIENT_SUPPORT = "CALIBRATION_INSUFFICIENT_SUPPORT"
NO_DIRECTION = "NO_DIRECTIONAL_SIGNAL"
NO_THRESHOLD = "NO_THRESHOLD_PASSES_PRECISION_GATE"
CONFOUND_REVIEW = "CALIBRATION_CONFOUND_REVIEW"
THRESHOLD_FROZEN = "THRESHOLD_FROZEN"

MEASUREMENT_INSUFFICIENT = "MEASUREMENT_INSUFFICIENT_SUPPORT"
MEASUREMENT_NOT_ACCEPTED = "MEASUREMENT_NOT_ACCEPTED"
MEASUREMENT_ACCEPTED = "MEASUREMENT_ACCEPTED"

NEXT_TRANSITION = "RESIDUAL_CALIBRATION_SURFACE_DRAW_AUTHORIZATION"


def _quantize_rate(value: Decimal) -> Decimal:
    return value.quantize(RATE_QUANTUM, rounding=ROUND_HALF_EVEN)


def _residual_text(value: Decimal) -> str:
    quantized = value.quantize(SCORE_QUANTUM, rounding=ROUND_HALF_EVEN)
    return f"{quantized:.10f}"


def wilson_interval(successes: int, trials: int) -> tuple[Decimal, Decimal] | None:
    """Wilson score interval at 95%. None when the trial count is zero.

    The arithmetic matches ``selection_surface.wilson_interval`` with
    ``Z95``. A zero trial count does not invent an interval.
    """
    if trials <= 0:
        return None
    if successes < 0 or successes > trials:
        raise ValueError(f"wilson successes={successes} outside 0..{trials}")
    z = float(WILSON_Z95)
    n = trials
    phat = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (phat + z2 / (2.0 * n)) / denom
    half = z * math.sqrt(phat * (1.0 - phat) / n + z2 / (4.0 * n * n)) / denom
    low = max(0.0, center - half)
    high = min(1.0, center + half)
    if low < 1e-12:
        low = 0.0
    if high > 1.0 - 1e-12:
        high = 1.0
    return (_quantize_rate(Decimal(low)), _quantize_rate(Decimal(high)))


def _ready_rows(rows: list[dict]) -> list[dict]:
    ready = []
    for row in rows:
        if row.get("development_row") is True:
            raise RuntimeError("a development row cannot enter threshold selection")
        bucket = row["operator_bucket"]
        if bucket not in COMPARISON_BUCKETS | SAFETY_BUCKETS:
            raise RuntimeError(f"unexpected operator bucket {bucket}")
        if "uses_tier3" not in row or "pos" not in row:
            raise RuntimeError("calibration row is missing tier or pos provenance")
        status = row.get("score_status", READY)
        if status != READY:
            continue
        text = _residual_text(Decimal(row["residual_score"]))
        ready.append({**row, "residual_score": text, "operator_bucket": bucket})
    return ready


def _comparison(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row["operator_bucket"] in COMPARISON_BUCKETS]


def _scores(rows: list[dict], bucket: str) -> list[str]:
    return [row["residual_score"] for row in rows if row["operator_bucket"] == bucket]


def _predicted_yes(rows: list[dict], threshold: str) -> list[dict]:
    cutoff = Decimal(threshold)
    return [row for row in rows if Decimal(row["residual_score"]) >= cutoff]


def _precision_terms(comparison_rows: list[dict], threshold: str) -> tuple[int, int]:
    yes = _predicted_yes(comparison_rows, threshold)
    true_high = sum(1 for row in yes if row["operator_bucket"] == "HIGH")
    return true_high, len(yes)


def precision_gates(
    true_high: int,
    predicted_yes: int,
    *,
    minimum_yes: int,
    precision_floor: Decimal,
    wilson_floor: Decimal,
) -> bool:
    """Precision, Wilson lower bound, and minimum YES support. Recall is not a gate."""
    if predicted_yes < minimum_yes or predicted_yes <= 0:
        return False
    if true_high < 0 or true_high > predicted_yes:
        return False
    precision = _quantize_rate(Decimal(true_high) / Decimal(predicted_yes))
    if precision < precision_floor:
        return False
    interval = wilson_interval(true_high, predicted_yes)
    if interval is None:
        return False
    return interval[0] >= wilson_floor


def _stable(comparison_rows: list[dict], threshold: str, *, minimum_yes: int, precision_floor: Decimal, wilson_floor: Decimal) -> bool:
    """A pass must survive deletion of any one comparison row."""
    if not precision_gates(
        *_precision_terms(comparison_rows, threshold),
        minimum_yes=minimum_yes,
        precision_floor=precision_floor,
        wilson_floor=wilson_floor,
    ):
        return False
    for index in range(len(comparison_rows)):
        reduced = comparison_rows[:index] + comparison_rows[index + 1 :]
        true_high, support = _precision_terms(reduced, threshold)
        if not precision_gates(
            true_high,
            support,
            minimum_yes=minimum_yes,
            precision_floor=precision_floor,
            wilson_floor=wilson_floor,
        ):
            return False
    return True


def _safety_counts(rows: list[dict], threshold: str) -> dict[str, int]:
    yes = _predicted_yes(rows, threshold)
    return {
        "quarantine_predicted_yes": sum(1 for row in yes if row["operator_bucket"] == "QUARANTINE"),
        "reject_predicted_yes": sum(1 for row in yes if row["operator_bucket"] == "REJECT"),
    }


def _high_recall(comparison_rows: list[dict], threshold: str) -> Decimal:
    high = _scores(comparison_rows, "HIGH")
    if not high:
        return Decimal(0)
    true_high = sum(1 for score in high if Decimal(score) >= Decimal(threshold))
    return _quantize_rate(Decimal(true_high) / Decimal(len(high)))


def _metrics(comparison_rows: list[dict], ready: list[dict], threshold: str) -> dict:
    true_high, support = _precision_terms(comparison_rows, threshold)
    false_high = support - true_high
    precision = None if support == 0 else str(_quantize_rate(Decimal(true_high) / Decimal(support)))
    interval = wilson_interval(true_high, support)
    high_n = len(_scores(comparison_rows, "HIGH"))
    abstained = len(comparison_rows) - support
    safety = _safety_counts(ready, threshold)
    return {
        "abstention_count": abstained,
        "abstention_rate": str(_quantize_rate(Decimal(abstained) / Decimal(len(comparison_rows)))) if comparison_rows else None,
        "false_high": false_high,
        "high_recall": str(_high_recall(comparison_rows, threshold)),
        "precision": precision,
        "precision_interval": None if interval is None else [str(interval[0]), str(interval[1])],
        "predicted_yes_support": support,
        "quarantine_predicted_yes": safety["quarantine_predicted_yes"],
        "reject_predicted_yes": safety["reject_predicted_yes"],
        "true_high": true_high,
        "true_high_denominator": high_n,
    }


def _confound(ready: list[dict], high_scores: list[str], secondary_scores: list[str]) -> dict:
    views = [
        {
            "bucket": row["operator_bucket"],
            "pos": row["pos"],
            "residual_score": row["residual_score"],
            "uses_tier3": row["uses_tier3"],
        }
        for row in ready
        if row["operator_bucket"] in COMPARISON_BUCKETS
    ]
    tier3 = tier3_concentration(views)
    return {
        "extreme_driven": extreme_driven(high_scores, secondary_scores),
        "pos_partitioned": pos_partitioned(views),
        "tier3_concentrated": bool(tier3["concentrated"]),
    }


def _candidate_thresholds(ready: list[dict]) -> list[str]:
    values = sorted({Decimal(row["residual_score"]) for row in ready})
    return [_residual_text(value) for value in values]


def _passes_candidate(ready: list[dict], comparison_rows: list[dict], threshold: str) -> bool:
    safety = _safety_counts(ready, threshold)
    if safety["reject_predicted_yes"] > REJECT_PREDICTED_YES_MAX:
        return False
    if safety["quarantine_predicted_yes"] > QUARANTINE_PREDICTED_YES_MAX:
        return False
    return _stable(
        comparison_rows,
        threshold,
        minimum_yes=MIN_PREDICTED_YES,
        precision_floor=PRECISION_FLOOR,
        wilson_floor=WILSON_LOWER_FLOOR,
    )


def select_threshold(rows: list[dict]) -> dict:
    """Run the frozen calibration rule. The caller must already have joined labels.

    Development rows are refused. UNKNOWN rows are ignored. No threshold is
    read from a file.
    """
    ready = _ready_rows(rows)
    comparison_rows = _comparison(ready)
    high_scores = _scores(comparison_rows, "HIGH")
    secondary_scores = _scores(comparison_rows, "SECONDARY")
    base = {
        "algorithm_id": ALGORITHM_ID,
        "high_support": len(high_scores),
        "output_labels": list(OUTPUT_LABELS),
        "secondary_support": len(secondary_scores),
        "threshold_frozen": False,
        "threshold_value": None,
    }
    if len(high_scores) < MIN_CALIBRATION_HIGH or len(secondary_scores) < MIN_CALIBRATION_SECONDARY:
        return {**base, "calibration_state": INSUFFICIENT_SUPPORT}
    comparison = pair_comparison(high_scores, secondary_scores)
    direction = direction_result(comparison)
    if direction != "SUPPORTED_DIRECTION":
        return {**base, "calibration_state": NO_DIRECTION, "direction": direction}
    confound = _confound(ready, high_scores, secondary_scores)
    if confound["extreme_driven"] or confound["pos_partitioned"] or confound["tier3_concentrated"]:
        return {
            **base,
            "calibration_state": CONFOUND_REVIEW,
            "confound": confound,
            "direction": direction,
        }
    best: tuple[Decimal, Decimal, str] | None = None
    best_metrics: dict | None = None
    for threshold in _candidate_thresholds(ready):
        if not _passes_candidate(ready, comparison_rows, threshold):
            continue
        recall = _high_recall(comparison_rows, threshold)
        rank = (recall, Decimal(threshold))
        if best is None or rank > (best[0], best[1]):
            best = (recall, Decimal(threshold), threshold)
            best_metrics = _metrics(comparison_rows, ready, threshold)
    if best is None:
        return {**base, "calibration_state": NO_THRESHOLD, "direction": direction}
    return {
        **base,
        "calibration_state": THRESHOLD_FROZEN,
        "direction": direction,
        "selection_metrics": best_metrics,
        "threshold_frozen": True,
        "threshold_value": best[2],
    }


def semantic_output(score_status: str, residual: str | None, threshold: str) -> str:
    """Map one frozen threshold onto YES or UNKNOWN. There is no NO output."""
    if score_status != READY or residual is None:
        return "UNKNOWN"
    if Decimal(residual) >= Decimal(threshold):
        return "YES"
    return "UNKNOWN"


def measurement_acceptance(rows: list[dict], threshold: str) -> dict:
    """Score a frozen threshold. This does not choose a new one."""
    if threshold is None or str(threshold).strip() == "":
        raise RuntimeError("measurement requires an already frozen threshold")
    ready = _ready_rows(rows)
    comparison_rows = _comparison(ready)
    high_n = len(_scores(comparison_rows, "HIGH"))
    secondary_n = len(_scores(comparison_rows, "SECONDARY"))
    cutoff = _residual_text(Decimal(threshold))
    metrics = _metrics(comparison_rows, ready, cutoff) if comparison_rows else None
    accepted = (
        high_n >= MIN_MEASUREMENT_HIGH
        and secondary_n >= MIN_MEASUREMENT_SECONDARY
        and comparison_rows
        and _safety_counts(ready, cutoff)["reject_predicted_yes"] <= REJECT_PREDICTED_YES_MAX
        and _safety_counts(ready, cutoff)["quarantine_predicted_yes"] <= QUARANTINE_PREDICTED_YES_MAX
        and _stable(
            comparison_rows,
            cutoff,
            minimum_yes=MIN_MEASUREMENT_PREDICTED_YES,
            precision_floor=MEASUREMENT_PRECISION_FLOOR,
            wilson_floor=MEASUREMENT_WILSON_LOWER_FLOOR,
        )
    )
    if high_n < MIN_MEASUREMENT_HIGH or secondary_n < MIN_MEASUREMENT_SECONDARY:
        state = MEASUREMENT_INSUFFICIENT
    elif accepted:
        state = MEASUREMENT_ACCEPTED
    else:
        state = MEASUREMENT_NOT_ACCEPTED
    return {
        "applied_threshold": cutoff,
        "high_support": high_n,
        "measurement_state": state,
        "metrics": metrics,
        "secondary_support": secondary_n,
        "threshold_adjusted": False,
    }


def _common(sealed: dict) -> dict:
    return {
        "admitted": 0,
        "calibration_surface_drawn": False,
        "development_rows_reusable_for_threshold_selection": False,
        "development_row_count_excluded": 225,
        "gold": 0,
        "json_schema_document": None,
        "json_schema_exists": False,
        "measurement_eligible": False,
        "measurement_sample_drawn": False,
        "measurement_surface_drawn": False,
        "next_legal_transition": NEXT_TRANSITION,
        "next_transition_authorized": False,
        "no_output": "NO",
        "output_labels": list(OUTPUT_LABELS),
        "rule": RULE,
        "runtime_integration": False,
        "sealed_ancestors": dict(sorted(sealed.items())),
        "select_005_authorized": False,
        "selected_source": "none",
        "settled": 0,
        "state": TRACK_STATE,
        "threshold_count": 1,
        "threshold_frozen": False,
        "threshold_scope": "one_global_T_HIGH",
        "threshold_value": None,
        "this_pass_selects_threshold": False,
    }


def documents(sealed: dict, sibling_sha256: dict | None = None) -> dict[str, dict]:
    """Return the seven frozen contracts. ``threshold_value`` is always null."""
    common = _common(sealed)
    acceptance = {
        **common,
        "calibration_gates": [
            "resolved HIGH support meets the frozen minimum",
            "resolved SECONDARY support meets the frozen minimum",
            "HIGH residuals are directionally larger than SECONDARY residuals",
            "precision meets the frozen floor",
            "predicted YES support meets the frozen minimum",
            "Wilson lower bound meets the frozen floor",
            "the same precision gates hold after deleting any one comparison row",
            "REJECT predicted YES count is 0",
            "QUARANTINE predicted YES count is 0",
        ],
        "confidence_level": CONFIDENCE_LEVEL,
        "direction_rule": "median_difference > 0 and rank_biserial > 0 and auc > 0.5",
        "direction_rule_source": "residual_model_resolved_replay_v1.direction_result",
        "floors_are_not_a_function_of_development_auc": True,
        "high_recall_is_a_gate": False,
        "interval_method": "wilson_score",
        "interval_when_support_is_zero": "no_interval_and_gate_fails",
        "minimum_calibration_high": MIN_CALIBRATION_HIGH,
        "minimum_calibration_secondary": MIN_CALIBRATION_SECONDARY,
        "minimum_predicted_yes": MIN_PREDICTED_YES,
        "optimized_objectives_forbidden": ["accuracy", "f1", "youden_j", "auc"],
        "precision_denominator": "operator HIGH versus operator SECONDARY among RESIDUAL_READY rows",
        "precision_floor": str(PRECISION_FLOOR),
        "primary_objective": "highest HIGH recall among thresholds that pass the precision gates",
        "quarantine_predicted_yes_maximum": QUARANTINE_PREDICTED_YES_MAX,
        "reject_in_precision_denominator": False,
        "reject_predicted_yes_maximum": REJECT_PREDICTED_YES_MAX,
        "schema": "hyperlex.residual_threshold_v1_acceptance.v1",
        "single_row_rule": "deleting any one HIGH or SECONDARY comparison row must leave the precision, Wilson, and minimum-support gates intact",
        "wilson_lower_floor": str(WILSON_LOWER_FLOOR),
        "wilson_z": str(WILSON_Z95),
    }
    procedure = {
        **common,
        "algorithm_id": ALGORITHM_ID,
        "candidate_thresholds": "unique RESIDUAL_READY residual values, quantized to 10 decimal places, sorted ascending",
        "failure_states": [
            INSUFFICIENT_SUPPORT,
            NO_DIRECTION,
            CONFOUND_REVIEW,
            NO_THRESHOLD,
        ],
        "prediction_rule": "YES if and only if the row is RESIDUAL_READY and residual >= T_HIGH; otherwise UNKNOWN",
        "schema": "hyperlex.residual_threshold_v1_selection_procedure.v1",
        "steps": [
            "refuse if any row is marked as a development row",
            "ignore rows that are not RESIDUAL_READY",
            "stop with CALIBRATION_INSUFFICIENT_SUPPORT when ready HIGH is below 12 or ready SECONDARY is below 8",
            "stop with NO_DIRECTIONAL_SIGNAL unless direction_result is SUPPORTED_DIRECTION",
            "stop with CALIBRATION_CONFOUND_REVIEW when the frozen tier-3 concentration, extreme-driven, or POS-partition flag is true",
            "evaluate each candidate threshold with YES defined as residual >= T",
            "keep a threshold only when precision, the Wilson lower bound, minimum YES support, leave-one-out stability, and both safety counts pass",
            "among kept thresholds, choose the highest HIGH recall",
            "break remaining ties by choosing the larger threshold",
            "stop with NO_THRESHOLD_PASSES_PRECISION_GATE when none are kept",
        ],
        "success_state_of_a_future_run": THRESHOLD_FROZEN,
        "tie_break": "larger threshold",
    }
    calibration = {
        **common,
        "comparison_buckets": ["HIGH", "SECONDARY"],
        "descriptive_checks": [
            "pos",
            "token_count",
            "character_length",
            "content_constituent_count",
            "resolution_tier",
            "glossbert_involvement",
            "candidate_sense_count",
        ],
        "descriptive_checks_do_not_change_threshold": True,
        "eligible_row": "RESIDUAL_READY under the frozen Tier1, Tier2, and Tier3 stack",
        "failure_states": procedure["failure_states"],
        "glossbert_fields_are_not_threshold_inputs": True,
        "labels_joined_only_after_score_hash": True,
        "order": [
            "freeze calibration manifest",
            "resolve constituents with the frozen stack",
            "freeze integrated resolutions",
            "compute residuals",
            "freeze score file",
            "freeze score hash",
            "only then join operator labels",
            "execute the preregistered threshold algorithm",
            "freeze a threshold or freeze a calibration failure",
        ],
        "preserved_provenance": [
            "tier_1",
            "tier_2",
            "tier_3",
            "glossbert_confidence",
            "glossbert_margin",
            "candidate_sense_count",
        ],
        "schema": "hyperlex.residual_threshold_v1_calibration_contract.v1",
        "subgroup_thresholds": False,
        "unknown_rows_select_threshold": False,
    }
    measurement = {
        **common,
        "calibration_success_implies_measurement_success": False,
        "confidence_level": CONFIDENCE_LEVEL,
        "failure_states": [MEASUREMENT_INSUFFICIENT, MEASUREMENT_NOT_ACCEPTED],
        "interval_method": "wilson_score",
        "interval_when_support_is_zero": "no_interval_and_acceptance_fails",
        "minimum_measurement_high": MIN_MEASUREMENT_HIGH,
        "minimum_measurement_secondary": MIN_MEASUREMENT_SECONDARY,
        "minimum_predicted_yes": MIN_MEASUREMENT_PREDICTED_YES,
        "order": [
            "freeze measurement manifest",
            "resolve constituents with the frozen stack",
            "compute residuals",
            "apply the already frozen T_HIGH",
            "freeze predictions",
            "only then join operator labels",
            "score acceptance without changing T_HIGH",
        ],
        "outcomes": [
            "YES support",
            "YES precision",
            "HIGH recall",
            "abstention rate",
            "false YES count",
            "REJECT receiving YES",
            "QUARANTINE receiving YES",
        ],
        "precision_floor": str(MEASUREMENT_PRECISION_FLOOR),
        "quarantine_predicted_yes_maximum": QUARANTINE_PREDICTED_YES_MAX,
        "reject_predicted_yes_maximum": REJECT_PREDICTED_YES_MAX,
        "schema": "hyperlex.residual_threshold_v1_measurement_contract.v1",
        "success_state": MEASUREMENT_ACCEPTED,
        "threshold_may_be_refit": False,
        "wilson_lower_floor": str(MEASUREMENT_WILSON_LOWER_FLOOR),
    }
    artifact = {
        **common,
        "document_kind": "artifact_contract",
        "future_threshold_artifact_required_fields": [
            "threshold_id",
            "residual_candidate_spec_hash",
            "resolver_stack_hashes",
            "calibration_manifest_hash",
            "calibration_score_hash",
            "label_hash",
            "threshold_value",
            "selection_algorithm_id",
            "predicted_yes_support",
            "true_high",
            "false_high",
            "precision",
            "precision_interval",
            "high_recall",
            "excluded_reject_count",
            "excluded_quarantine_count",
            "selection_receipt",
        ],
        "schema": "hyperlex.residual_threshold_v1_artifact_contract.v1",
        "schema_note": "No JSON Schema document exists for this threshold family. This contract names the future fields. It is not a JSON Schema.",
    }
    isolation = {
        **common,
        "development_partitions_included": "all 225 reviewed positional rows, including historical v3-v7 partitions stored in the development evidence artifact",
        "identity_fences": [
            "row_id, which is hyperlexical.holdout_guard.normalized_text_sha256 of the surface",
            "normalized surface text from heldout_census.normalize_group_text",
            "PWN 3.0 synset key synset_pos:synset_offset when the offset is non-empty",
        ],
        "missing_synset_does_not_match_another_missing_synset": True,
        "population": "the same positional-unbind universe as the 225-row development inventory",
        "primary_existing_fence": "hyperlexical.holdout_guard.normalized_text_sha256",
        "provenance_requirements": "unchanged from the evaluation reserve",
        "rights_requirements": "unchanged from the evaluation reserve",
        "same_synset_on_two_surfaces": False,
        "schema": "hyperlex.residual_threshold_v1_surface_isolation.v1",
        "synset_justification": "The residual is a property of one synset's resolved constituents. Reusing that synset on another surface is not an independent observation. This exclusion is frozen before any calibration or measurement draw.",
        "surfaces": ["DEVELOPMENT", "CALIBRATION", "MEASUREMENT"],
    }
    preregistration = {
        **common,
        "asymmetry": "residual >= T_HIGH maps to YES; residual < T_HIGH maps to UNKNOWN; there is no NO path and no lower threshold",
        "composition": "normalized_mean_v1",
        "distance": "1 - cosine",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        "research_track": RULE,
        "residual_track_state_unchanged": "RESIDUAL_DEVELOPMENT_ANALYZED_V2",
        "resolver_stack": ["TIER1_STRUCTURAL_OR_UNIQUE", "TIER2_EXTENDED_LESK_V1", "TIER3_GLOSSBERT_FROZEN_CANDIDATE"],
        "schema": "hyperlex.residual_threshold_v1_preregistration.v1",
        "sibling_artifact_sha256": dict(sorted((sibling_sha256 or {}).items())),
    }
    body = {
        "RESIDUAL_THRESHOLD_V1_ACCEPTANCE.json": acceptance,
        "RESIDUAL_THRESHOLD_V1_ARTIFACT_SCHEMA.json": artifact,
        "RESIDUAL_THRESHOLD_V1_CALIBRATION_CONTRACT.json": calibration,
        "RESIDUAL_THRESHOLD_V1_MEASUREMENT_CONTRACT.json": measurement,
        "RESIDUAL_THRESHOLD_V1_PREREGISTRATION.json": preregistration,
        "RESIDUAL_THRESHOLD_V1_SELECTION_PROCEDURE.json": procedure,
        "RESIDUAL_THRESHOLD_V1_SURFACE_ISOLATION_POLICY.json": isolation,
    }
    for name, document in body.items():
        if document["threshold_value"] is not None:
            raise RuntimeError(f"{name} carries a numeric threshold")
        if document["state"] != TRACK_STATE:
            raise RuntimeError(f"{name} left the preregistered state")
    if RESIDUAL_QUANTUM != SCORE_QUANTUM:
        raise RuntimeError("residual quanta disagree")
    return body
