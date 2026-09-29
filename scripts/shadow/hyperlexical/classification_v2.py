"""Classification v2 contract. No training, no checkpoint writes, no Jev calls.

Normative text: ``specs/007-hyperlexical-model/classification-architecture-v2.md``.

This module is the drafted interface. It does not load weights, does not move
BEST, and does not authorize ``JEV_MODE = GATED``.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from hyperlexical.eval_settlement import ACTIVE_FAMILIES, CANDIDATE_FAMILIES
from hyperlexical.layout import FAMILIES

ARCHITECTURE_ID = "HYPERLEX_CLASSIFICATION_ARCHITECTURE_V2"
STATE = "CLASSIFICATION_V2_SPEC_DRAFTED"
SCHEMA = "hyperlex.classification.v2"
PACKET_SCHEMA = "hyperlex.jev.decision_packet.v1"
ADAPTER_SCHEMA = "hyperlex.classification.v2.checkpoint_adapter"

# Reference only. This module does not read or replace the production checkpoint.
BEST_REFERENCE_SHA256 = (
    "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
)

V2_FAMILY = "FAMILY"
V2_NONE = "NONE"
V2_ABSTAIN = "ABSTAIN"
V2_AMBIGUOUS = "AMBIGUOUS"
DECISIONS = (V2_FAMILY, V2_NONE, V2_ABSTAIN, V2_AMBIGUOUS)

APPLICABILITY_NONE = "NONE"
APPLICABILITY_PRESENT = "FAMILY_PRESENT"
APPLICABILITY = (APPLICABILITY_NONE, APPLICABILITY_PRESENT)

AMBIGUITY_SINGLE = "SINGLE"
AMBIGUITY_MULTI = "MULTI_OR_UNCLEAR"
AMBIGUITY = (AMBIGUITY_SINGLE, AMBIGUITY_MULTI)

PROVENANCE = ("OBSERVED", "INFERRED", "UNKNOWN")
LABEL_CLASS = ("OBSERVED", "INFERRED")

# eval_settlement.ABSTAIN is the operator token "none". It is not v2 ABSTAIN.
SETTLEMENT_ABSTAIN_TOKEN = "none"
V1_NONE_CLASS = "none"

V1_HEAD = tuple(FAMILIES)
HEAD_OUTPUTS = tuple(name for name in V1_HEAD if name != V1_NONE_CLASS)
WEIGHT_BACKED_FAMILIES = tuple(name for name in HEAD_OUTPUTS if name in ACTIVE_FAMILIES)
LEGACY_HEADS = tuple(name for name in HEAD_OUTPUTS if name not in ACTIVE_FAMILIES)
UNSUPPORTED_ACTIVE_FAMILIES = tuple(
    name for name in ACTIVE_FAMILIES if name not in WEIGHT_BACKED_FAMILIES
)

JEV_OFF = "OFF"
JEV_SHADOW = "SHADOW"
JEV_GATED = "GATED"
JEV_MODES_IMPLEMENTED = (JEV_OFF, JEV_SHADOW)

PROHIBITED_SURFACES = frozenset(
    {"held_out", "evaluation_reserve", "settlement", "measurement"}
)

PROBABILITY_SUM_TOLERANCE = 1e-6

SUPERVISION_KEYS = (
    "observed_non_none_applicability",
    "observed_non_none_family",
    "inferred_non_none_applicability",
    "inferred_non_none_family",
    "observed_none_applicability",
    "inferred_none_applicability",
)
SUPERVISION_ORDER = (
    ("observed_non_none_applicability", "inferred_non_none_applicability"),
    ("observed_non_none_family", "inferred_non_none_family"),
    ("observed_none_applicability", "inferred_none_applicability"),
)

LOSS_TERMS = (
    "applicability_loss",
    "ambiguity_loss",
    "family_loss_on_family_examples",
    "provenance_weighted_weak_supervision",
    "unbind_loss",
)

CALIBRATION_TARGETS = (
    "applicability",
    "family_confidence",
    "abstention",
    "ambiguity",
)
CALIBRATION_METRICS = (
    "ece",
    "brier_score",
    "reliability_curve",
    "margin_distribution",
    "coverage_vs_accuracy",
    "selective_risk",
)

GATED_PRECONDITIONS = (
    "validated_provider_behavior",
    "probability_schema_compliance",
    "measured_calibration",
    "known_failure_modes",
    "latency_cost_bounds",
    "exposure_policy_compliance",
    "clear_fallback",
    "shadow_evidence_of_material_value",
)

ROUTE_CHOICES = ("accept_automated", "human_review", "additional_evidence")
DECISION_TYPES = ("choice", "score", "route")
FORBIDDEN_PACKET_KEYS = frozenset(
    {
        "api_key",
        "best",
        "canonical_family",
        "observed_label",
        "reserve_gold",
        "semantic_family",
    }
)

PACKET_REQUIRED = (
    "decision_type",
    "candidate_set",
    "probabilities",
    "confidence",
    "provider",
    "model",
    "schema_version",
    "prompt_schema_version",
    "timestamp",
    "input_hash",
    "output_hash",
)


class ClassificationContractError(ValueError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class JevContractError(ClassificationContractError):
    pass


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash64(value: Any, reason: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise JevContractError(reason)
    try:
        int(value, 16)
    except ValueError as exc:
        raise JevContractError(reason) from exc
    return value


def _unit(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise JevContractError("malformed_probability")
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        raise JevContractError("malformed_probability")
    return number


def _open_unit_floor(value: Any, reason: str) -> float:
    number = _unit(value)
    if number <= 0.0 or number >= 1.0:
        raise ClassificationContractError(reason)
    return number


def architecture_state() -> dict[str, Any]:
    return {
        "architecture_id": ARCHITECTURE_ID,
        "state": STATE,
        "authorizes_training": False,
        "authorizes_preregistration": False,
        "authorizes_gated_jev": False,
        "moves_best": False,
        "best_reference_sha256": BEST_REFERENCE_SHA256,
        "select_006": "SETTLED_PASS",
        "select_007": "SETTLED_FAIL",
        "reopens_select_006": False,
        "reopens_select_007": False,
    }


def gated_authorized(_evidence: Mapping[str, Any] | None = None) -> bool:
    """GATED stays unauthorized in this drafted contract."""
    return False


def checkpoint_compatibility(head_labels: Sequence[str]) -> dict[str, Any]:
    """Read-only map from a historical head vocabulary onto v2.

    Does not invent logits for active families the checkpoint does not contain.
    Does not rename legacy heads onto current active names.
    """
    labels = tuple(head_labels)
    unknown = [
        name
        for name in labels
        if name not in ACTIVE_FAMILIES
        and name not in LEGACY_HEADS
        and name not in CANDIDATE_FAMILIES
        and name != V1_NONE_CLASS
    ]
    inactive = [name for name in labels if name in CANDIDATE_FAMILIES]
    legacy = [name for name in labels if name in LEGACY_HEADS]
    emittable = [name for name in labels if name in ACTIVE_FAMILIES]
    missing = [name for name in ACTIVE_FAMILIES if name not in labels]
    return {
        "schema": ADAPTER_SCHEMA,
        "historical_artifact_mutated": False,
        "v1_none_logit": "NOT_A_V2_DECISION" if V1_NONE_CLASS in labels else "ABSENT",
        "emittable_families": emittable,
        "unsupported_active_families": missing,
        "legacy_heads": legacy,
        "inactive_candidate_heads": inactive,
        "legacy_remap": {},
        "unknown_heads": unknown,
        "invented_logits": [],
        "status": "UNSUPPORTED" if unknown or inactive else "PARTIAL_COMPATIBLE",
    }


def derive_ambiguity(distribution: Mapping[str, float], margin_floor: float) -> str:
    """Derived ambiguity. A learned head stays masked until explicit gold exists."""
    floor = _open_unit_floor(margin_floor, "margin_floor_unconfigured")
    if any(name == V1_NONE_CLASS for name in distribution):
        raise ClassificationContractError("none_is_not_a_family")
    if len(distribution) < 2:
        return AMBIGUITY_MULTI if len(distribution) == 0 else AMBIGUITY_SINGLE
    ordered = sorted((_unit(value) for value in distribution.values()), reverse=True)
    margin = ordered[0] - ordered[1]
    return AMBIGUITY_SINGLE if margin >= floor else AMBIGUITY_MULTI


def evidence_sufficient(applicability_confidence: float, evidence_floor: float) -> bool:
    floor = _open_unit_floor(evidence_floor, "evidence_floor_unconfigured")
    return _unit(applicability_confidence) >= floor


def validate_supervision_weights(weights: Mapping[str, Any]) -> dict[str, float]:
    """Configurable contract. This module has no default weights."""
    if not isinstance(weights, Mapping):
        raise ClassificationContractError("weights_missing")
    unknown = sorted(set(weights) - set(SUPERVISION_KEYS))
    if unknown:
        raise ClassificationContractError("weights_unknown_key")
    missing = [key for key in SUPERVISION_KEYS if key not in weights]
    if missing:
        raise ClassificationContractError("weights_missing")
    checked: dict[str, float] = {}
    for key in SUPERVISION_KEYS:
        value = weights[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ClassificationContractError("weights_malformed")
        number = float(value)
        if not math.isfinite(number) or number <= 0.0 or number > 1.0:
            raise ClassificationContractError("weights_out_of_bounds")
        checked[key] = number
    for strong, weak in SUPERVISION_ORDER:
        if not checked[strong] > checked[weak]:
            raise ClassificationContractError("inferred_not_weaker")
    return checked


def loss_mask(row: Mapping[str, Any], weights: Mapping[str, Any]) -> dict[str, Any]:
    """Mask family loss off unless an active family is supervised.

    Provenance weighting multiplies the masked terms. It is not a second loss.
    Unbind is reported as unchanged and is not reweighted here.
    """
    checked = validate_supervision_weights(weights)
    klass = row.get("class")
    if klass not in LABEL_CLASS:
        raise ClassificationContractError("provenance_class_missing")
    lineage = row.get("lineage")
    supervised = tuple(row.get("supervised_families") or WEIGHT_BACKED_FAMILIES)
    unknown_supervised = [name for name in supervised if name not in ACTIVE_FAMILIES]
    if unknown_supervised or V1_NONE_CLASS in supervised:
        raise ClassificationContractError("supervised_family_invalid")

    plan: dict[str, Any] = {
        "applicability_loss": False,
        "ambiguity_loss": False,
        "family_loss": False,
        "applicability_weight": None,
        "ambiguity_weight": None,
        "family_weight": None,
        "applicability_target": None,
        "ambiguity_target": None,
        "family_target": None,
        "legacy_unsupervised": None,
        "unsupported_lineage": None,
        "unbind_loss": "separate_unchanged",
        "provenance_weighting": "multiplier_not_extra_term",
    }
    ambiguity_gold = row.get("ambiguity_gold")
    if ambiguity_gold is not None:
        if ambiguity_gold not in AMBIGUITY:
            raise ClassificationContractError("ambiguity_gold_invalid")
        plan["ambiguity_loss"] = True
        plan["ambiguity_target"] = ambiguity_gold
        plan["ambiguity_weight"] = 1.0

    if lineage == V1_NONE_CLASS:
        plan["applicability_loss"] = True
        plan["applicability_target"] = APPLICABILITY_NONE
        key = (
            "observed_none_applicability"
            if klass == "OBSERVED"
            else "inferred_none_applicability"
        )
        plan["applicability_weight"] = checked[key]
        return plan
    if lineage in supervised:
        prefix = "observed_non_none" if klass == "OBSERVED" else "inferred_non_none"
        plan["applicability_loss"] = True
        plan["applicability_target"] = APPLICABILITY_PRESENT
        plan["applicability_weight"] = checked[prefix + "_applicability"]
        plan["family_loss"] = True
        plan["family_target"] = lineage
        plan["family_weight"] = checked[prefix + "_family"]
        return plan
    if lineage in LEGACY_HEADS:
        plan["legacy_unsupervised"] = lineage
        return plan
    plan["unsupported_lineage"] = lineage
    return plan


def final_decision(state: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministic policy. Jev is not an input."""
    applicability = state.get("applicability")
    ambiguity = state.get("ambiguity")
    if applicability not in APPLICABILITY:
        raise ClassificationContractError("applicability_invalid")
    if ambiguity not in AMBIGUITY:
        raise ClassificationContractError("ambiguity_invalid")
    if not isinstance(state.get("evidence_sufficient"), bool):
        raise ClassificationContractError("evidence_flag_invalid")
    family = state.get("family")
    confidence = _unit(state.get("family_confidence"))
    floor = _open_unit_floor(state.get("family_confidence_floor"), "confidence_floor_unconfigured")
    eligible = tuple(state.get("eligible_families") or ())
    if any(name not in ACTIVE_FAMILIES for name in eligible) or V1_NONE_CLASS in eligible:
        raise ClassificationContractError("eligible_family_invalid")
    eligible_set = set(eligible)

    if state["evidence_sufficient"] is False:
        decision, emitted, stage = V2_ABSTAIN, None, "Q1_EVIDENCE"
    elif applicability == APPLICABILITY_NONE:
        decision, emitted, stage = V2_NONE, None, "Q2_APPLICABILITY"
    elif ambiguity == AMBIGUITY_MULTI:
        decision, emitted, stage = V2_AMBIGUOUS, None, "Q3_AMBIGUITY"
    elif family not in eligible_set or confidence < floor:
        decision, emitted, stage = V2_ABSTAIN, None, "Q5_CONFIDENCE"
    else:
        decision, emitted, stage = V2_FAMILY, family, "Q4_FAMILY"
    return {"decision": decision, "family": emitted, "stage": stage}


def _distribution(distribution: Mapping[str, Any], eligible: Sequence[str]) -> dict[str, float]:
    if not isinstance(distribution, Mapping):
        raise ClassificationContractError("distribution_invalid")
    if V1_NONE_CLASS in distribution or V2_NONE in distribution or V2_ABSTAIN in distribution:
        raise ClassificationContractError("none_is_not_a_family")
    eligible_set = set(eligible)
    if any(name not in eligible_set for name in distribution):
        raise ClassificationContractError("distribution_outside_eligible")
    checked = {name: _unit(value) for name, value in distribution.items()}
    if checked and abs(sum(checked.values()) - 1.0) > PROBABILITY_SUM_TOLERANCE:
        raise ClassificationContractError("distribution_not_normalized")
    return checked


def build_result(
    *,
    evidence_sufficient: bool,
    applicability: str,
    applicability_score: float,
    ambiguity: str,
    ambiguity_score: float,
    family: str | None,
    family_distribution: Mapping[str, Any],
    family_confidence: float,
    family_confidence_floor: float,
    eligible_families: Sequence[str],
    confidence: float,
    provenance_context: str,
) -> dict[str, Any]:
    if provenance_context not in PROVENANCE:
        raise ClassificationContractError("provenance_context_invalid")
    decided = final_decision(
        {
            "evidence_sufficient": evidence_sufficient,
            "applicability": applicability,
            "ambiguity": ambiguity,
            "family": family,
            "family_confidence": family_confidence,
            "family_confidence_floor": family_confidence_floor,
            "eligible_families": eligible_families,
        }
    )
    return {
        "schema": SCHEMA,
        "decision": decided["decision"],
        "family": decided["family"],
        "applicability": applicability,
        "applicability_score": _unit(applicability_score),
        "ambiguity": ambiguity,
        "ambiguity_score": _unit(ambiguity_score),
        "family_distribution": _distribution(family_distribution, eligible_families),
        "confidence": _unit(confidence),
        "family_confidence": _unit(family_confidence),
        "provenance_context": provenance_context,
        "stage": decided["stage"],
        "brier": None,
        "forecast_eligible": False,
        "jev": {
            "mode": JEV_OFF,
            "invoked": False,
            "decision_packet_ref": None,
            "agreement": None,
            "rejection": None,
        },
    }


def packet_body(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {key: packet[key] for key in packet if key != "output_hash"}


def packet_output_hash(packet: Mapping[str, Any]) -> str:
    return sha256_text(canonical_json(packet_body(packet)))


def validate_decision_packet(
    packet: Mapping[str, Any], *, eligible: Sequence[str]
) -> dict[str, Any]:
    """Fail closed. Malformed provider output is not repaired."""
    if not isinstance(packet, Mapping):
        raise JevContractError("packet_not_object")
    forbidden = FORBIDDEN_PACKET_KEYS.intersection(packet)
    if forbidden:
        raise JevContractError("forbidden_authority_field")
    missing = [key for key in PACKET_REQUIRED if key not in packet]
    if missing:
        raise JevContractError("packet_field_missing")
    if packet.get("schema_version") != PACKET_SCHEMA:
        raise JevContractError("schema_mismatch")
    decision_type = packet.get("decision_type")
    if decision_type not in DECISION_TYPES:
        raise JevContractError("decision_type_invalid")
    _unit(packet.get("confidence"))
    _hash64(packet.get("input_hash"), "input_hash_invalid")
    _hash64(packet.get("output_hash"), "output_hash_invalid")
    if packet_output_hash(packet) != packet["output_hash"]:
        raise JevContractError("output_hash_mismatch")
    for key in ("provider", "model", "prompt_schema_version", "timestamp"):
        if not isinstance(packet.get(key), str) or not str(packet.get(key)).strip():
            raise JevContractError("packet_field_missing")
    candidates = packet.get("candidate_set")
    probabilities = packet.get("probabilities")
    if not isinstance(candidates, list) or not isinstance(probabilities, dict):
        raise JevContractError("packet_field_missing")
    eligible_set = set(eligible)
    if any(name not in ACTIVE_FAMILIES for name in eligible_set):
        raise ClassificationContractError("eligible_family_invalid")

    if decision_type == "choice":
        if not candidates or len(candidates) != len(set(candidates)):
            raise JevContractError("candidate_set_invalid")
        if any(name not in eligible_set for name in candidates):
            raise JevContractError("candidate_outside_eligible")
        if set(probabilities) != set(candidates):
            raise JevContractError("probability_keys_mismatch")
        if "abstain_probability" not in packet:
            raise JevContractError("packet_field_missing")
        checked = {name: _unit(probabilities[name]) for name in candidates}
        abstain = _unit(packet.get("abstain_probability"))
        if abs(sum(checked.values()) + abstain - 1.0) > PROBABILITY_SUM_TOLERANCE:
            raise JevContractError("not_normalized")
        selected = packet.get("selected")
        if selected is not None and selected not in candidates:
            raise JevContractError("candidate_outside_eligible")
    elif decision_type == "score":
        expected = {"confidence", "ambiguity", "escalation_need"}
        if set(probabilities) != expected:
            raise JevContractError("probability_keys_mismatch")
        for key in expected:
            _unit(probabilities[key])
    else:
        if not candidates or any(name not in ROUTE_CHOICES for name in candidates):
            raise JevContractError("candidate_set_invalid")
        if set(probabilities) != set(candidates):
            raise JevContractError("probability_keys_mismatch")
        checked = {name: _unit(probabilities[name]) for name in candidates}
        if abs(sum(checked.values()) - 1.0) > PROBABILITY_SUM_TOLERANCE:
            raise JevContractError("not_normalized")
        selected = packet.get("selected")
        if selected is not None and selected not in candidates:
            raise JevContractError("candidate_outside_eligible")
    return dict(packet)


def _agreement(canonical: Mapping[str, Any], packet: Mapping[str, Any]) -> dict[str, Any]:
    jev_choice = packet.get("selected") if packet.get("decision_type") == "choice" else None
    hyper_family = canonical.get("family") if canonical.get("decision") == V2_FAMILY else None
    family_agreement = None
    if packet.get("decision_type") == "choice":
        family_agreement = hyper_family == jev_choice and hyper_family is not None
    return {
        "family_agreement": family_agreement,
        "hyperlex_abstain_jev_choice": canonical.get("decision") == V2_ABSTAIN and jev_choice is not None,
        "hyperlex_choice_jev_null": canonical.get("decision") == V2_FAMILY and jev_choice is None,
        "ambiguity_disagreement": None,
        "adopted": False,
    }


def jev_call_count(*, surface: str, mode: str) -> int:
    if mode == JEV_GATED or mode not in JEV_MODES_IMPLEMENTED:
        raise JevContractError("gated_not_authorized")
    if surface in PROHIBITED_SURFACES or mode == JEV_OFF:
        return 0
    return 1


def integrate_jev(
    *,
    canonical: Mapping[str, Any],
    mode: str,
    surface: str,
    eligible: Sequence[str],
    packet: Mapping[str, Any] | None = None,
    provider_status: str = "ok",
) -> dict[str, Any]:
    """Shadow records a packet. It does not write canonical decision or family."""
    if mode == JEV_GATED or mode not in JEV_MODES_IMPLEMENTED:
        raise JevContractError("gated_not_authorized")
    result = json.loads(canonical_json(canonical))
    decision = result.get("decision")
    family = result.get("family")
    result["jev"] = {
        "mode": mode,
        "invoked": False,
        "decision_packet_ref": None,
        "agreement": None,
        "rejection": None,
    }
    if surface in PROHIBITED_SURFACES:
        result["jev"]["rejection"] = "exposure_prohibited"
    elif mode == JEV_SHADOW and provider_status != "ok":
        result["jev"]["rejection"] = "provider_unavailable"
    elif mode == JEV_SHADOW and packet is not None:
        try:
            checked = validate_decision_packet(packet, eligible=eligible)
        except JevContractError as exc:
            result["jev"]["rejection"] = exc.reason
        else:
            result["jev"]["invoked"] = True
            result["jev"]["decision_packet_ref"] = checked["output_hash"]
            result["jev"]["agreement"] = _agreement(result, checked)
    if result.get("decision") != decision or result.get("family") != family:
        raise JevContractError("canonical_mutated")
    return result


def map_legacy_jevgate(*, jevgate: bool, no_jevgate: bool, v2_jev_mode: str | None) -> dict[str, Any]:
    """``--jevgate`` stays jevgate-1. It does not authorize v2 GATED mode."""
    requested = (v2_jev_mode or JEV_OFF).upper()
    if requested == JEV_GATED or requested not in JEV_MODES_IMPLEMENTED:
        raise JevContractError("gated_not_authorized")
    legacy_enabled = False if no_jevgate else bool(jevgate)
    return {
        "legacy_gate": "jevgate-1",
        "legacy_enabled": legacy_enabled,
        "authorizes_v2_gated": False,
        "v2_mode": requested,
        "legacy_flag_changes_v2_canonical": False,
    }


def evaluation_plan() -> dict[str, Any]:
    return {
        "applicability": ("precision", "recall", "f1"),
        "family_on_family_examples_only": (
            "macro_f1",
            "per_family_precision",
            "per_family_recall",
            "per_family_f1",
            "confusion",
        ),
        "abstention": (
            "coverage",
            "selective_accuracy",
            "selective_risk",
            "false_abstention_rate",
            "unsafe_emission_rate",
        ),
        "ambiguity_requires_explicit_gold": True,
        "ambiguity_gold_from_disagreement": False,
        "provenance_slices": ("OBSERVED", "INFERRED"),
        "aggregate_hides_provenance": False,
        "calibration_targets": CALIBRATION_TARGETS,
        "calibration_metrics": CALIBRATION_METRICS,
        "packet_brier": None,
        "jev_is_calibration_truth": False,
        "jev_calls_on_reserve": 0,
        "trutina_module_in_repo": False,
    }
