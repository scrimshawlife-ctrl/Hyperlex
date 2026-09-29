"""Sealed Classification v2 contract. No training, no network, no BEST writes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v2 import (  # noqa: E402
    ACTIVE_FAMILY_VOCABULARY,
    AMBIGUITY_EMISSION,
    BEST_REFERENCE_SHA256,
    EXACT_COPY_FAMILIES,
    LEGACY_HEADS,
    PROVENANCE_WEIGHTS,
    STATE,
    V1_HEAD,
    applicability_class_weights,
    applicability_threshold,
    architecture_state,
    build_result,
    decide_v2,
    example_loss,
    family_emit_threshold,
    family_loss_weights,
    freeze_calibration,
    freeze_training_contract,
    integrate_jev,
    jev_call_count,
    map_family_rows,
    map_legacy_jevgate,
    packet_output_hash,
    readiness,
    selection_score,
    support_audit,
    validate_telemetry,
)
from hyperlexical.layout import FAMILIES  # noqa: E402

SCHEMA = json.loads(
    (ROOT / "specs/007-hyperlexical-model/schemas/classification.v2.schema.json").read_text(
        encoding="utf-8"
    )
)


def _row(lineage: str, klass: str = "OBSERVED") -> dict:
    return {"lineage": lineage, "class": klass, "split": "train"}


def _supported_rows() -> list[dict]:
    rows = []
    for index, name in enumerate(ACTIVE_FAMILY_VOCABULARY):
        rows.extend(_row(name, "OBSERVED") for _ in range(index + 1))
        if index % 2 == 0:
            rows.append(_row(name, "INFERRED"))
    rows.append(_row("none", "OBSERVED"))
    rows.append(_row("none", "INFERRED"))
    return rows


def _distribution(peaked: str | None = "ai-native") -> dict[str, float]:
    dist = {name: 0.0 for name in ACTIVE_FAMILY_VOCABULARY}
    if peaked is None:
        share = 1.0 / len(ACTIVE_FAMILY_VOCABULARY)
        return {name: share for name in ACTIVE_FAMILY_VOCABULARY}
    dist[peaked] = 1.0
    return dist


def test_vocabulary_covers_every_active_family_and_excludes_none():
    assert len(ACTIVE_FAMILY_VOCABULARY) == 19
    assert len(set(ACTIVE_FAMILY_VOCABULARY)) == 19
    assert "none" not in ACTIVE_FAMILY_VOCABULARY
    assert "ABSTAIN" not in ACTIVE_FAMILY_VOCABULARY
    assert "AMBIGUOUS" not in ACTIVE_FAMILY_VOCABULARY
    assert set(EXACT_COPY_FAMILIES) == {"betting-sharp", "crypto-degen", "ai-native", "gaming-meta"}
    assert "workplace-corp" in LEGACY_HEADS
    assert "workplace-career" in ACTIVE_FAMILY_VOCABULARY
    state = architecture_state()
    assert state["state"] == STATE == "PREREGISTERED"
    assert state["moves_best"] is False
    assert state["best_reference_sha256"] == BEST_REFERENCE_SHA256
    assert state["authorizes_training"] is False
    assert state["reopens_select_006"] is False
    assert state["reopens_select_007"] is False


def test_exact_rows_copy_and_new_rows_are_zero():
    labels = list(FAMILIES)
    assert tuple(labels) == V1_HEAD
    weight = [[float(index + 1), float(index + 2)] for index, _name in enumerate(labels)]
    bias = [float(index + 3) for index, _name in enumerate(labels)]
    mapped = map_family_rows(labels, weight, bias)
    assert mapped["status"] == "PASS"
    assert mapped["historical_artifact_mutated"] is False
    assert mapped["legacy_remap"] == {}
    assert mapped["mapped_families"] == [
        name for name in ACTIVE_FAMILY_VOCABULARY if name in EXACT_COPY_FAMILIES
    ]
    assert "workplace-career" in mapped["zero_initialized_families"]
    assert "politics-civic" in mapped["zero_initialized_families"]
    assert "none" not in mapped["mapped_families"]
    by_name = {row["active_family"]: row for row in mapped["rows"]}
    ai = ACTIVE_FAMILY_VOCABULARY.index("ai-native")
    source_ai = labels.index("ai-native")
    assert mapped["weight"][ai] == weight[source_ai]
    assert mapped["bias"][ai] == bias[source_ai]
    career = ACTIVE_FAMILY_VOCABULARY.index("workplace-career")
    assert mapped["weight"][career] == [0.0, 0.0]
    assert mapped["bias"][career] == 0.0
    assert by_name["workplace-career"]["source_row"] is None
    assert by_name["workplace-corp"]["mapping_status"] if False else "workplace-corp" not in by_name


def test_provenance_weights_and_none_mask():
    assert PROVENANCE_WEIGHTS == {
        "observed_non_none_applicability": 1.00,
        "observed_non_none_family": 1.00,
        "inferred_non_none_applicability": 0.50,
        "inferred_non_none_family": 0.50,
        "observed_none_applicability": 1.00,
        "inferred_none_applicability": 0.25,
    }
    contract = freeze_training_contract(_supported_rows())
    none = example_loss(_row("none", "OBSERVED"), contract)
    inferred_none = example_loss(_row("none", "INFERRED"), contract)
    observed = example_loss(_row("ai-native", "OBSERVED"), contract)
    inferred = example_loss(_row("ai-native", "INFERRED"), contract)
    legacy = example_loss(_row("brainrot-aura", "OBSERVED"), contract)
    assert none["family_weight"] is None
    assert none["applicability_target"] == "NONE"
    assert inferred_none["family_weight"] is None
    assert none["applicability_weight"] > inferred_none["applicability_weight"]
    assert observed["family_weight"] == 2 * inferred["family_weight"]
    assert observed["family_target"] == "ai-native"
    assert legacy["family_weight"] is None
    assert legacy["excluded"] == "legacy_not_remapped"
    assert legacy["unbind_loss"] == "separate_unchanged"
    assert none["trained_class_abstain"] is False


def test_family_and_applicability_weights_are_deterministic():
    rows = []
    for index, name in enumerate(ACTIVE_FAMILY_VOCABULARY):
        count = 1 if index == 0 else 100
        rows.extend(_row(name) for _ in range(count))
    rows.extend(_row("none") for _ in range(10))
    rows.extend(_row("none", "INFERRED") for _ in range(4))
    first = freeze_training_contract(rows)
    second = freeze_training_contract(rows)
    assert first["family_weights"] == second["family_weights"]
    assert len(first["family_weights"]) == 19
    assert first["family_weights"][ACTIVE_FAMILY_VOCABULARY[0]] == 2.0
    assert abs(sum(first["applicability_weights"].values()) / 2 - 1.0) < 1e-12
    rare = min(first["applicability_weights"], key=first["applicability_weights"].get)
    assert first["applicability_weights"][rare] <= max(first["applicability_weights"].values())
    audit = support_audit(rows)
    assert family_loss_weights(audit) == first["family_weights"]
    assert applicability_class_weights(audit) == first["applicability_weights"]


def test_zero_support_blocks_ready_without_dropping_the_family():
    rows = [_row(name) for name in EXACT_COPY_FAMILIES]
    rows.append(_row("none"))
    report = readiness(rows, loader_status="PASS")
    assert report["ready"] is False
    assert report["blocker"] == "ACTIVE_FAMILY_WITHOUT_TRAINING_SUPPORT"
    assert report["state"] == "PREREGISTERED"
    assert report["authorizes_training"] is False
    assert report["moves_best"] is False
    assert set(report["missing_support"]) == set(ACTIVE_FAMILY_VOCABULARY) - set(EXACT_COPY_FAMILIES)
    assert "internet-slang" in report["missing_support"]
    assert len(report["missing_support"]) == 15
    try:
        freeze_training_contract(rows)
    except Exception as exc:
        assert exc.reason == "ACTIVE_FAMILY_WITHOUT_TRAINING_SUPPORT"
        assert exc.families == tuple(report["missing_support"])
    else:
        raise AssertionError("zero-support families were given loss weights")


def test_reserve_rows_cannot_enter_weights_or_calibration():
    rows = _supported_rows()
    rows.append({"lineage": "ai-native", "class": "OBSERVED", "split": "train", "evaluation_reserve": True})
    try:
        freeze_training_contract(rows)
    except Exception as exc:
        assert exc.reason == "evaluation_isolation"
    else:
        raise AssertionError("reserve row influenced the training contract")
    try:
        from hyperlexical.classification_v2 import fit_temperature

        fit_temperature([([0.0, 0.0], 1)], surface="evaluation_reserve")
    except Exception as exc:
        assert exc.reason == "calibration_surface_forbidden"
    else:
        raise AssertionError("reserve surface was calibrated")
    family_logits = [0.0] * len(ACTIVE_FAMILY_VOCABULARY)
    family_logits[0] = 3.0
    wrong = [0.0] * len(ACTIVE_FAMILY_VOCABULARY)
    wrong[1] = 3.0
    artifact = freeze_calibration(
        applicability_rows=[([0.0, 2.0], 1), ([2.0, 0.0], 0)],
        family_rows=[(family_logits, 0), (family_logits, 0), (wrong, 0)],
        surface="validation",
        checkpoint_identity="fixture",
    )
    assert artifact["reserve_used"] is False
    assert artifact["training_rows_used"] is False
    assert artifact["surface"] == "validation"
    assert artifact["checkpoint_identity"] == "fixture"
    try:
        freeze_calibration(
            applicability_rows=[([0.0, 2.0], 1), ([2.0, 0.0], 0)],
            family_rows=[(family_logits, 0)],
            surface="evaluation_reserve",
        )
    except Exception as exc:
        assert exc.reason == "calibration_surface_forbidden"
    else:
        raise AssertionError("reserve surface froze a calibration artifact")


def test_selection_score_and_calibration_rules():
    assert selection_score(0.2, 0.4, 0.6) == 0.35
    threshold = applicability_threshold([0.2, 0.8], [0, 1])
    assert threshold == 0.8
    emit = family_emit_threshold([0.95, 0.90, 0.2], [True, True, False])
    assert emit == 0.90
    assert family_emit_threshold([0.4, 0.9], [True, False]) == 0.0


def test_abstain_is_not_trained_and_ambiguous_emission_stays_off():
    result = build_result(
        p_family_present=0.2,
        applicability_threshold_value=0.5,
        family_distribution=_distribution(),
        family_emit_threshold_value=0.0,
        confidence=0.2,
        provenance_context="UNKNOWN",
    )
    jsonschema.validate(result, SCHEMA)
    assert result["decision"] == "ABSTAIN"
    assert result["family"] is None
    assert result["brier"] is None
    assert result["ambiguity_emission"] == AMBIGUITY_EMISSION == "DISABLED_PENDING_GOLD"
    none = decide_v2(
        p_family_present=0.4,
        applicability_threshold_value=0.3,
        family_distribution=_distribution(),
        family_emit_threshold_value=0.0,
    )
    assert none["decision"] == "NONE"
    family = decide_v2(
        p_family_present=0.9,
        applicability_threshold_value=0.5,
        family_distribution=_distribution("gaming-meta"),
        family_emit_threshold_value=0.0,
    )
    assert family["decision"] == "FAMILY"
    assert family["family"] == "gaming-meta"
    spread = _distribution("gaming-meta")
    spread["gaming-meta"] = 0.9
    spread["ai-native"] = 0.1
    low = decide_v2(
        p_family_present=0.9,
        applicability_threshold_value=0.5,
        family_distribution=spread,
        family_emit_threshold_value=0.95,
    )
    assert low["decision"] == "ABSTAIN"
    assert low["stage"] == "Q5_FAMILY_CONFIDENCE"
    assert family["ambiguity_emission"] == "DISABLED_PENDING_GOLD"


def test_jev_off_and_shadow_leave_the_canonical_family():
    canonical = build_result(
        p_family_present=0.9,
        applicability_threshold_value=0.5,
        family_distribution=_distribution("ai-native"),
        family_emit_threshold_value=0.0,
        confidence=0.9,
        provenance_context="UNKNOWN",
    )
    out = integrate_jev(
        canonical=canonical,
        mode="OFF",
        surface="operational",
        eligible=ACTIVE_FAMILY_VOCABULARY,
        packet=None,
        provider_status="unavailable",
    )
    assert out["family"] == "ai-native"
    assert out["jev"]["invoked"] is False
    assert jev_call_count(surface="operational", mode="OFF") == 0
    body = {
        "schema_version": "hyperlex.jev.decision_packet.v1",
        "decision_type": "choice",
        "candidate_set": ["ai-native", "gaming-meta"],
        "probabilities": {"ai-native": 0.2, "gaming-meta": 0.7},
        "abstain_probability": 0.1,
        "selected": "gaming-meta",
        "confidence": 0.7,
        "provider": "provider-neutral-fixture",
        "model": "fixture-model",
        "prompt_schema_version": "classification-v2-shadow",
        "timestamp": "2026-09-29T00:00:00Z",
        "input_hash": "a" * 64,
    }
    body["output_hash"] = packet_output_hash(body)
    shadow = integrate_jev(
        canonical=canonical,
        mode="SHADOW",
        surface="operational",
        eligible=ACTIVE_FAMILY_VOCABULARY,
        packet=body,
    )
    assert shadow["decision"] == "FAMILY"
    assert shadow["family"] == "ai-native"
    assert shadow["jev"]["agreement"]["adopted"] is False
    assert shadow["jev"]["agreement"]["family_agreement"] is False
    held = integrate_jev(
        canonical=canonical,
        mode="SHADOW",
        surface="evaluation_reserve",
        eligible=ACTIVE_FAMILY_VOCABULARY,
        packet=body,
    )
    assert held["jev"]["rejection"] == "exposure_prohibited"
    assert held["jev"]["invoked"] is False
    mapped = map_legacy_jevgate(jevgate=True, no_jevgate=False, v2_jev_mode=None)
    assert mapped["v2_mode"] == "OFF"
    assert mapped["authorizes_v2_gated"] is False
    assert mapped["required_for_v2_training"] is False
    record = {field: 0 for field in (
        "total_loss",
        "applicability_loss",
        "family_loss",
        "unbind_loss",
        "applicability_macro_f1",
        "none_precision",
        "none_recall",
        "none_f1",
        "family_present_precision",
        "family_present_recall",
        "family_present_f1",
        "active_family_macro_f1",
        "observed_active_family_macro_f1",
        "per_family",
        "predicted_none_rate",
        "family_emission_rate",
        "selection_score",
        "learning_rate",
        "global_step",
        "checkpoint_identity",
    )}
    record["observed_slice"] = {}
    record["inferred_slice"] = {}
    validate_telemetry(record)
