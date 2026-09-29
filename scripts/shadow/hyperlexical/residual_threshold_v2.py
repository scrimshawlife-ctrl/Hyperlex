"""Preregister threshold v2. This module does not draw a surface.

v1 stays closed. The acceptance gates are the v1 gates. The only new
design choice is the label-blind raw-row quota, taken from a readiness
rate below the lower observed coverage, not from class labels.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_HALF_EVEN

from hyperlexical.residual_threshold_v1 import (
    ALGORITHM_ID,
    MIN_CALIBRATION_HIGH,
    MIN_CALIBRATION_SECONDARY,
    MIN_MEASUREMENT_HIGH,
    MIN_MEASUREMENT_PREDICTED_YES,
    MIN_MEASUREMENT_SECONDARY,
    MIN_PREDICTED_YES,
    MEASUREMENT_PRECISION_FLOOR,
    MEASUREMENT_WILSON_LOWER_FLOOR,
    PRECISION_FLOOR,
    QUARANTINE_PREDICTED_YES_MAX,
    REJECT_PREDICTED_YES_MAX,
    WILSON_LOWER_FLOOR,
    WILSON_Z95,
)

RULE = "RUNE.SEMANTIC_COMPOSITIONALITY_THRESHOLD.v2"
TRACK_STATE = "THRESHOLD_PROCEDURE_PREREGISTERED"
NEXT_TRANSITION = "THRESHOLD_V2_SURFACE_DRAW_AUTHORIZATION"
SAMPLING_RULE_ID = "positional_stratified_hash_round_robin_quota_v2"

# Sum of the unchanged ready-HIGH and ready-SECONDARY floors. Not a new gate.
REQUIRED_TARGET_READY = MIN_CALIBRATION_HIGH + MIN_CALIBRATION_SECONDARY
# Below the lower observed readiness, 6/27. The development rate 73/225 is not used.
CONSERVATIVE_READINESS = Decimal("0.20")
SAFETY_FACTOR = Decimal("2.0")

V1_EXECUTION_STATE = "CALIBRATION_INSUFFICIENT_SUPPORT"
V1_DISPOSITION = "CLOSED_CALIBRATION_DESIGN_INSUFFICIENT"
FAILURE_STATES = (
    "CALIBRATION_INSUFFICIENT_SUPPORT",
    "NO_DIRECTIONAL_SIGNAL",
    "CALIBRATION_CONFOUND_REVIEW",
    "NO_THRESHOLD_PASSES_PRECISION_GATE",
)
QUOTA_UNFILLED = "SURFACE_QUOTA_UNFILLED"


def quota_from_readiness(required_ready: int = REQUIRED_TARGET_READY) -> int:
    """ceil(required_ready / conservative_readiness * safety_factor)."""
    value = (Decimal(required_ready) / CONSERVATIVE_READINESS) * SAFETY_FACTOR
    return int(value.to_integral_value(rounding=ROUND_CEILING))


def calibration_draw_size() -> int:
    return quota_from_readiness()


def measurement_draw_size() -> int:
    return quota_from_readiness()


def _common() -> dict:
    return {
        "admitted": 0,
        "calibration_draw_size": calibration_draw_size(),
        "calibration_surface_drawn": False,
        "development_rows_reusable_for_threshold_selection": False,
        "gold": 0,
        "json_schema_document": None,
        "json_schema_exists": False,
        "measurement_draw_size": measurement_draw_size(),
        "measurement_eligible": False,
        "measurement_surface_drawn": False,
        "next_legal_transition": NEXT_TRANSITION,
        "next_transition_authorized": False,
        "no_output": "NO",
        "output_labels": ["YES", "UNKNOWN"],
        "redraw_authorized": False,
        "rule": RULE,
        "runtime_integration": False,
        "select_005_authorized": False,
        "selected_source": "none",
        "selection_algorithm_id": ALGORITHM_ID,
        "settled": 0,
        "state": TRACK_STATE,
        "this_pass_draws_surfaces": False,
        "this_pass_selects_threshold": False,
        "threshold_frozen": False,
        "threshold_value": None,
        "v1_disposition": V1_DISPOSITION,
        "v1_execution_state": V1_EXECUTION_STATE,
        "v1_redraw_authorized": False,
        "v1_threshold_value": None,
    }


def sample_size_document() -> dict:
    lower = Decimal(6) / Decimal(27)
    return {
        **_common(),
        "conservative_readiness": str(CONSERVATIVE_READINESS),
        "development_readiness_not_used": "73/225",
        "formula": "ceil(required_target_ready / conservative_readiness * safety_factor)",
        "frozen_rate_below_lower_observed": CONSERVATIVE_READINESS < lower,
        "lower_observed_readiness": "6/27",
        "lower_observed_readiness_display": str(lower.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)),
        "quotas_are_separate": True,
        "readiness_inputs_are_label_independent": True,
        "required_target_ready": REQUIRED_TARGET_READY,
        "safety_factor": str(SAFETY_FACTOR),
        "schema": "hyperlex.residual_threshold_v2_sample_size.v1",
        "unused_for_quota": [
            "HIGH_prevalence",
            "SECONDARY_prevalence",
            "residual_distribution",
            "AUC",
            "threshold_performance",
        ],
    }


def calibration_contract() -> dict:
    return {
        **_common(),
        "draw_seed": None,
        "failure_states": list(FAILURE_STATES),
        "full_manifest_frozen_before_resolution": True,
        "labels_joined_only_after_score_hash": True,
        "ordering": "normalized_text_sha256 ascending within cell",
        "quota_unfilled_state": QUOTA_UNFILLED,
        "replacement": "without_replacement",
        "sampling_rule_id": SAMPLING_RULE_ID,
        "schema": "hyperlex.residual_threshold_v2_calibration_contract.v1",
        "stop_when_support_reached": False,
        "stratification": "source_pos x token_count",
        "support_floors": {
            "precision": str(PRECISION_FLOOR),
            "predicted_yes": MIN_PREDICTED_YES,
            "quarantine_yes": QUARANTINE_PREDICTED_YES_MAX,
            "ready_high": MIN_CALIBRATION_HIGH,
            "ready_secondary": MIN_CALIBRATION_SECONDARY,
            "reject_yes": REJECT_PREDICTED_YES_MAX,
            "wilson_lower": str(WILSON_LOWER_FLOOR),
            "wilson_z": str(WILSON_Z95),
        },
        "visit_order": "round-robin across cells sorted by source_pos then token_count; skip exhausted cells",
    }


def measurement_contract() -> dict:
    return {
        **_common(),
        "acceptance_floors": {
            "precision": str(MEASUREMENT_PRECISION_FLOOR),
            "predicted_yes": MIN_MEASUREMENT_PREDICTED_YES,
            "quarantine_yes": QUARANTINE_PREDICTED_YES_MAX,
            "ready_high": MIN_MEASUREMENT_HIGH,
            "ready_secondary": MIN_MEASUREMENT_SECONDARY,
            "reject_yes": REJECT_PREDICTED_YES_MAX,
            "wilson_lower": str(MEASUREMENT_WILSON_LOWER_FLOOR),
        },
        "partitioned_with_calibration": True,
        "schema": "hyperlex.residual_threshold_v2_measurement_contract.v1",
        "sealed_before_calibration_labels": True,
        "threshold_refit_prohibited": True,
        "unresolved_until_later_authorization": True,
    }


def selection_procedure() -> dict:
    return {
        **_common(),
        "failure_states": list(FAILURE_STATES),
        "gates_changed_from_v1": False,
        "inadequate_support_authorizes_redraw": False,
        "schema": "hyperlex.residual_threshold_v2_selection_procedure.v1",
        "threshold_count": 1,
        "threshold_scope": "one_global_T_HIGH",
    }


def isolation_policy() -> dict:
    return {
        **_common(),
        "excluded_surfaces": [
            "development_225",
            "v1_calibration_manifest",
        ],
        "identity_fences": [
            "normalized_text_sha256",
            "normalized surface text",
            "PWN 3.0 synset key when the offset is non-empty",
        ],
        "same_synset_on_two_surfaces": False,
        "schema": "hyperlex.residual_threshold_v2_surface_isolation.v1",
        "v1_labels_and_scores_not_read_for_selection": True,
        "v2_calibration_and_measurement_disjoint": True,
    }


def acceptance() -> dict:
    return {
        **_common(),
        "gates_lowered": False,
        "schema": "hyperlex.residual_threshold_v2_acceptance.v1",
    }


def artifact_schema() -> dict:
    return {
        **_common(),
        "document_kind": "artifact_contract",
        "schema": "hyperlex.residual_threshold_v2_artifact_contract.v1",
        "schema_note": "No JSON Schema document exists for this threshold family. This contract names the fields. It is not a JSON Schema.",
    }


def preregistration(sibling_sha256: dict[str, str]) -> dict:
    return {
        **_common(),
        "kept_from_v1": [
            "tier1_tier2_tier3_resolver",
            "glossbert_revision_and_abstention",
            "minilm_residual",
            "normalized_mean_v1",
            "one_minus_cosine",
            "yes_unknown_only",
            "precision_gated_recall",
            "development_exclusion_fences",
            "no_redraw_after_labels",
        ],
        "schema": "hyperlex.residual_threshold_v2_preregistration.v1",
        "sibling_artifact_sha256": sibling_sha256,
    }


def companion_documents() -> dict[str, dict]:
    return {
        "RESIDUAL_THRESHOLD_V2_ACCEPTANCE.json": acceptance(),
        "RESIDUAL_THRESHOLD_V2_ARTIFACT_SCHEMA.json": artifact_schema(),
        "RESIDUAL_THRESHOLD_V2_CALIBRATION_CONTRACT.json": calibration_contract(),
        "RESIDUAL_THRESHOLD_V2_MEASUREMENT_CONTRACT.json": measurement_contract(),
        "RESIDUAL_THRESHOLD_V2_SAMPLE_SIZE.json": sample_size_document(),
        "RESIDUAL_THRESHOLD_V2_SELECTION_PROCEDURE.json": selection_procedure(),
        "RESIDUAL_THRESHOLD_V2_SURFACE_ISOLATION_POLICY.json": isolation_policy(),
    }
