"""Classification v2 contract. No training, no network, no BEST mutation."""

from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v2 import (  # noqa: E402
    BEST_REFERENCE_SHA256,
    LEGACY_HEADS,
    SETTLEMENT_ABSTAIN_TOKEN,
    STATE,
    V1_HEAD,
    V1_NONE_CLASS,
    V2_ABSTAIN,
    V2_NONE,
    WEIGHT_BACKED_FAMILIES,
    architecture_state,
    build_result,
    checkpoint_compatibility,
    derive_ambiguity,
    evaluation_plan,
    evidence_sufficient,
    final_decision,
    gated_authorized,
    integrate_jev,
    jev_call_count,
    loss_mask,
    map_legacy_jevgate,
    packet_output_hash,
    validate_decision_packet,
    validate_supervision_weights,
)
from hyperlexical.layout import FAMILIES  # noqa: E402

SCHEMA_DIR = ROOT / "specs" / "007-hyperlexical-model" / "schemas"
CLASSIFICATION_SCHEMA = json.loads(
    (SCHEMA_DIR / "classification.v2.schema.json").read_text(encoding="utf-8")
)
PACKET_SCHEMA = json.loads(
    (SCHEMA_DIR / "jev_decision_packet.v1.schema.json").read_text(encoding="utf-8")
)

ELIGIBLE = WEIGHT_BACKED_FAMILIES
INPUT_HASH = "a" * 64


def _weights() -> dict[str, float]:
    return {
        "observed_non_none_applicability": 1.0,
        "observed_non_none_family": 1.0,
        "inferred_non_none_applicability": 0.25,
        "inferred_non_none_family": 0.25,
        "observed_none_applicability": 1.0,
        "inferred_none_applicability": 0.1,
    }


def _result(**overrides: object) -> dict:
    payload = {
        "evidence_sufficient": True,
        "applicability": "FAMILY_PRESENT",
        "applicability_score": 0.9,
        "ambiguity": "SINGLE",
        "ambiguity_score": 0.1,
        "family": "ai-native",
        "family_distribution": {
            "betting-sharp": 0.05,
            "crypto-degen": 0.05,
            "ai-native": 0.8,
            "gaming-meta": 0.1,
        },
        "family_confidence": 0.8,
        "family_confidence_floor": 0.5,
        "eligible_families": ELIGIBLE,
        "confidence": 0.8,
        "provenance_context": "UNKNOWN",
    }
    payload.update(overrides)
    return build_result(**payload)


def _choice(**overrides: object) -> dict:
    body = {
        "schema_version": "hyperlex.jev.decision_packet.v1",
        "decision_type": "choice",
        "candidate_set": ["ai-native", "gaming-meta"],
        "probabilities": {"ai-native": 0.6, "gaming-meta": 0.3},
        "abstain_probability": 0.1,
        "selected": "ai-native",
        "confidence": 0.6,
        "provider": "provider-neutral-fixture",
        "model": "fixture-model",
        "prompt_schema_version": "classification-v2-shadow",
        "timestamp": "2026-09-29T00:00:00Z",
        "input_hash": INPUT_HASH,
        "reason_code": "shadow_choice",
    }
    body.update(overrides)
    body["output_hash"] = packet_output_hash(body)
    return body


def test_architecture_is_drafted_and_does_not_move_best():
    state = architecture_state()
    assert state["state"] == STATE == "CLASSIFICATION_V2_SPEC_DRAFTED"
    assert state["authorizes_training"] is False
    assert state["authorizes_preregistration"] is False
    assert state["moves_best"] is False
    assert state["best_reference_sha256"] == BEST_REFERENCE_SHA256
    assert state["reopens_select_006"] is False
    assert state["reopens_select_007"] is False
    assert gated_authorized({name: True for name in (
        "validated_provider_behavior",
        "probability_schema_compliance",
        "measured_calibration",
        "known_failure_modes",
        "latency_cost_bounds",
        "exposure_policy_compliance",
        "clear_fallback",
        "shadow_evidence_of_material_value",
    )}) is False


def test_decision_ontology_stays_distinct():
    assert V2_ABSTAIN != V2_NONE
    assert V2_NONE != "AMBIGUOUS"
    assert V2_ABSTAIN != V1_NONE_CLASS
    assert V2_NONE != V1_NONE_CLASS
    assert SETTLEMENT_ABSTAIN_TOKEN == "none"
    assert SETTLEMENT_ABSTAIN_TOKEN != V2_ABSTAIN
    abstain = final_decision(
        {
            "evidence_sufficient": False,
            "applicability": "NONE",
            "ambiguity": "SINGLE",
            "family": "ai-native",
            "family_confidence": 0.99,
            "family_confidence_floor": 0.5,
            "eligible_families": ELIGIBLE,
        }
    )
    none = final_decision(
        {
            "evidence_sufficient": True,
            "applicability": "NONE",
            "ambiguity": "MULTI_OR_UNCLEAR",
            "family": "ai-native",
            "family_confidence": 0.99,
            "family_confidence_floor": 0.5,
            "eligible_families": ELIGIBLE,
        }
    )
    ambiguous = final_decision(
        {
            "evidence_sufficient": True,
            "applicability": "FAMILY_PRESENT",
            "ambiguity": "MULTI_OR_UNCLEAR",
            "family": "ai-native",
            "family_confidence": 0.99,
            "family_confidence_floor": 0.5,
            "eligible_families": ELIGIBLE,
        }
    )
    low = final_decision(
        {
            "evidence_sufficient": True,
            "applicability": "FAMILY_PRESENT",
            "ambiguity": "SINGLE",
            "family": "ai-native",
            "family_confidence": 0.2,
            "family_confidence_floor": 0.5,
            "eligible_families": ELIGIBLE,
        }
    )
    emitted = final_decision(
        {
            "evidence_sufficient": True,
            "applicability": "FAMILY_PRESENT",
            "ambiguity": "SINGLE",
            "family": "ai-native",
            "family_confidence": 0.8,
            "family_confidence_floor": 0.5,
            "eligible_families": ELIGIBLE,
        }
    )
    assert abstain == {"decision": "ABSTAIN", "family": None, "stage": "Q1_EVIDENCE"}
    assert none == {"decision": "NONE", "family": None, "stage": "Q2_APPLICABILITY"}
    assert ambiguous == {"decision": "AMBIGUOUS", "family": None, "stage": "Q3_AMBIGUITY"}
    assert low["decision"] == "ABSTAIN" and low["stage"] == "Q5_CONFIDENCE"
    assert emitted == {"decision": "FAMILY", "family": "ai-native", "stage": "Q4_FAMILY"}
    assert derive_ambiguity({"ai-native": 0.51, "gaming-meta": 0.49}, 0.1) == "MULTI_OR_UNCLEAR"
    assert derive_ambiguity({"ai-native": 0.9, "gaming-meta": 0.1}, 0.1) == "SINGLE"


def test_family_loss_is_masked_and_weights_have_no_default():
    assert not hasattr(sys.modules["hyperlexical.classification_v2"], "DEFAULT_WEIGHTS")
    weights = _weights()
    observed = loss_mask({"class": "OBSERVED", "lineage": "ai-native"}, weights)
    inferred = loss_mask({"class": "INFERRED", "lineage": "ai-native"}, weights)
    observed_none = loss_mask({"class": "OBSERVED", "lineage": "none"}, weights)
    inferred_none = loss_mask({"class": "INFERRED", "lineage": "none"}, weights)
    legacy = loss_mask({"class": "OBSERVED", "lineage": "brainrot-aura"}, weights)
    assert observed["family_loss"] is True and observed["family_target"] == "ai-native"
    assert observed["family_weight"] > inferred["family_weight"]
    assert observed["applicability_weight"] > inferred["applicability_weight"]
    assert observed_none["applicability_target"] == "NONE"
    assert observed_none["family_loss"] is False
    assert inferred_none["family_loss"] is False
    assert observed_none["applicability_weight"] > inferred_none["applicability_weight"]
    assert legacy["family_loss"] is False and legacy["legacy_unsupervised"] == "brainrot-aura"
    assert observed["unbind_loss"] == "separate_unchanged"
    tied = dict(weights)
    tied["inferred_none_applicability"] = tied["observed_none_applicability"]
    try:
        validate_supervision_weights(tied)
    except Exception as exc:
        assert exc.reason == "inferred_not_weaker"
    else:
        raise AssertionError("equal provenance weights were accepted")


def test_active_family_adapter_does_not_invent_or_rename():
    adapted = checkpoint_compatibility(FAMILIES)
    assert adapted["historical_artifact_mutated"] is False
    assert adapted["invented_logits"] == []
    assert adapted["legacy_remap"] == {}
    assert adapted["emittable_families"] == list(WEIGHT_BACKED_FAMILIES)
    assert adapted["legacy_heads"] == list(LEGACY_HEADS)
    assert "workplace-career" in adapted["unsupported_active_families"]
    assert "politics-civic" in adapted["unsupported_active_families"]
    assert adapted["v1_none_logit"] == "NOT_A_V2_DECISION"
    assert adapted["status"] == "PARTIAL_COMPATIBLE"
    unknown = checkpoint_compatibility(("ai-native", "not-a-family"))
    assert unknown["status"] == "UNSUPPORTED"
    assert unknown["unknown_heads"] == ["not-a-family"]
    assert V1_HEAD[-1] == "none"


def test_result_schema_keeps_brier_null():
    result = _result()
    jsonschema.validate(result, CLASSIFICATION_SCHEMA)
    assert result["brier"] is None
    assert result["family_distribution"].keys().isdisjoint({"none", "NONE", "ABSTAIN"})
    try:
        _result(family_distribution={"none": 1.0})
    except Exception as exc:
        assert exc.reason == "none_is_not_a_family"
    else:
        raise AssertionError("none entered the family distribution")


def test_jev_disabled_leaves_hyperlex_output_unchanged():
    canonical = _result()
    packet = _choice(selected="gaming-meta", probabilities={"ai-native": 0.2, "gaming-meta": 0.7})
    out = integrate_jev(
        canonical=canonical,
        mode="OFF",
        surface="operational",
        eligible=ELIGIBLE,
        packet=packet,
    )
    assert out["decision"] == canonical["decision"] == "FAMILY"
    assert out["family"] == canonical["family"] == "ai-native"
    assert out["jev"]["invoked"] is False
    assert out["jev"]["agreement"] is None
    assert jev_call_count(surface="operational", mode="OFF") == 0


def test_shadow_mode_records_disagreement_without_adoption():
    canonical = _result()
    packet = _choice(
        selected="gaming-meta",
        probabilities={"ai-native": 0.2, "gaming-meta": 0.7},
        abstain_probability=0.1,
    )
    jsonschema.validate(packet, PACKET_SCHEMA)
    out = integrate_jev(
        canonical=canonical,
        mode="SHADOW",
        surface="operational",
        eligible=ELIGIBLE,
        packet=packet,
    )
    assert out["decision"] == "FAMILY"
    assert out["family"] == "ai-native"
    assert out["jev"]["invoked"] is True
    assert out["jev"]["agreement"]["family_agreement"] is False
    assert out["jev"]["agreement"]["adopted"] is False
    assert out["jev"]["decision_packet_ref"] == packet["output_hash"]


def test_jev_null_choice_does_not_force_a_family():
    canonical = _result(family="crypto-degen", family_confidence=0.7, confidence=0.7)
    packet = _choice(selected=None, probabilities={"ai-native": 0.45, "gaming-meta": 0.45})
    out = integrate_jev(
        canonical=canonical,
        mode="SHADOW",
        surface="operational",
        eligible=ELIGIBLE,
        packet=packet,
    )
    assert out["family"] == "crypto-degen"
    assert out["jev"]["agreement"]["hyperlex_choice_jev_null"] is True
    assert out["jev"]["agreement"]["adopted"] is False


def test_malformed_jev_probabilities_fail_closed():
    canonical = _result()
    for bad in (1.2, -0.01, True, math.nan, "0.5"):
        packet = _choice()
        packet["probabilities"] = {"ai-native": bad, "gaming-meta": 0.0}
        packet["output_hash"] = packet_output_hash(packet)
        out = integrate_jev(
            canonical=canonical,
            mode="SHADOW",
            surface="operational",
            eligible=ELIGIBLE,
            packet=packet,
        )
        assert out["family"] == "ai-native"
        assert out["jev"]["invoked"] is False
        assert out["jev"]["rejection"] == "malformed_probability"
    unnormalized = _choice(probabilities={"ai-native": 0.6, "gaming-meta": 0.6}, abstain_probability=0.1)
    out = integrate_jev(
        canonical=canonical,
        mode="SHADOW",
        surface="operational",
        eligible=ELIGIBLE,
        packet=unnormalized,
    )
    assert out["jev"]["rejection"] == "not_normalized"
    assert out["family"] == canonical["family"]


def test_jev_candidate_outside_eligible_set_is_rejected():
    canonical = _result()
    packet = _choice(
        candidate_set=["ai-native", "brainrot-aura"],
        probabilities={"ai-native": 0.7, "brainrot-aura": 0.2},
        selected="brainrot-aura",
    )
    out = integrate_jev(
        canonical=canonical,
        mode="SHADOW",
        surface="operational",
        eligible=ELIGIBLE,
        packet=packet,
    )
    assert out["jev"]["rejection"] == "candidate_outside_eligible"
    assert out["family"] == "ai-native"
    assert "brainrot-aura" not in out["family_distribution"]


def test_held_out_and_reserve_prohibit_jev_invocation():
    canonical = _result()
    packet = _choice()
    for surface in ("held_out", "evaluation_reserve", "settlement", "measurement"):
        out = integrate_jev(
            canonical=canonical,
            mode="SHADOW",
            surface=surface,
            eligible=ELIGIBLE,
            packet=packet,
        )
        assert out["jev"]["invoked"] is False
        assert out["jev"]["rejection"] == "exposure_prohibited"
        assert out["jev"]["decision_packet_ref"] is None
        assert jev_call_count(surface=surface, mode="SHADOW") == 0
        assert out["decision"] == canonical["decision"]
    plan = evaluation_plan()
    assert plan["jev_calls_on_reserve"] == 0
    assert plan["ambiguity_gold_from_disagreement"] is False
    assert plan["packet_brier"] is None
    assert plan["jev_is_calibration_truth"] is False
    assert plan["provenance_slices"] == ("OBSERVED", "INFERRED")


def test_provider_unavailable_falls_back_to_hyperlex():
    canonical = _result()
    out = integrate_jev(
        canonical=canonical,
        mode="SHADOW",
        surface="operational",
        eligible=ELIGIBLE,
        packet=None,
        provider_status="unavailable",
    )
    assert out["decision"] == "FAMILY"
    assert out["family"] == "ai-native"
    assert out["jev"]["invoked"] is False
    assert out["jev"]["rejection"] == "provider_unavailable"


def test_legacy_jevgate_maps_without_authorizing_gated_mode():
    mapped = map_legacy_jevgate(jevgate=True, no_jevgate=False, v2_jev_mode=None)
    assert mapped["legacy_gate"] == "jevgate-1"
    assert mapped["legacy_enabled"] is True
    assert mapped["v2_mode"] == "OFF"
    assert mapped["authorizes_v2_gated"] is False
    assert mapped["legacy_flag_changes_v2_canonical"] is False
    forced_off = map_legacy_jevgate(jevgate=True, no_jevgate=True, v2_jev_mode="SHADOW")
    assert forced_off["legacy_enabled"] is False
    assert forced_off["v2_mode"] == "SHADOW"
    try:
        map_legacy_jevgate(jevgate=True, no_jevgate=False, v2_jev_mode="GATED")
    except Exception as exc:
        assert exc.reason == "gated_not_authorized"
    else:
        raise AssertionError("GATED was authorized")
    try:
        validate_decision_packet({**_choice(), "canonical_family": "ai-native"}, eligible=ELIGIBLE)
    except Exception as exc:
        assert exc.reason == "forbidden_authority_field"
    else:
        raise AssertionError("canonical family field was accepted")


def test_evidence_floor_is_caller_configured():
    assert evidence_sufficient(0.8, 0.6) is True
    assert evidence_sufficient(0.4, 0.6) is False
    try:
        evidence_sufficient(0.8, 0.0)
    except Exception as exc:
        assert exc.reason == "evidence_floor_unconfigured"
    else:
        raise AssertionError("a zero evidence floor was accepted")
    original = _result()
    clone = copy.deepcopy(original)
    assert clone == original
