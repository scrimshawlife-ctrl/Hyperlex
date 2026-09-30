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
    decision_seal,
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
    reserve_positive_census,
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
        "exact_copy_family_macro_f1",
        "prototype_family_macro_f1",
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


def test_reserved_positives_cannot_supply_training_support():
    reserved = [
        {
            "lineage": name,
            "class": "OBSERVED",
            "split": "train",
            "evaluation_reserve": True,
        }
        for name in ACTIVE_FAMILY_VOCABULARY
    ]
    reserved.append(_row("none"))
    try:
        readiness(reserved, loader_status="PASS")
    except Exception as exc:
        assert exc.reason == "evaluation_isolation"
    else:
        raise AssertionError("reserved rows cleared training support")
    census = reserve_positive_census(
        [
            {
                "state": "EVAL_SPENT",
                "evaluation_reserved": True,
                "labels": [{"lineage": "internet-slang", "class": "OBSERVED"}],
            },
            {
                "state": "TRAIN_CONSUMED",
                "evaluation_reserved": False,
                "labels": [{"lineage": "gaming-meta", "class": "OBSERVED"}],
            },
        ]
    )
    assert census["usable_for_training"] is False
    assert census["counts"]["internet-slang"]["OBSERVED"] == 1
    assert census["counts"]["internet-slang"]["training_eligible"] == 0
    assert census["counts"]["gaming-meta"]["training_eligible"] == 1
    assert "conflict-aggression" in census["no_settled_positive"]



def test_calibration_nll_matches_log_softmax_and_survives_underflow():
    import math

    from hyperlexical.classification_v2 import _mean_nll, _softmax, fit_temperature

    logits = [0.2, -0.4, 1.5]
    expected = -math.log(_softmax(logits, 1.0)[2])
    assert abs(_mean_nll([(logits, 2)], 1.0) - expected) < 1e-12
    extreme = _mean_nll([([0.0, 1000.0], 0)], 0.05)
    assert extreme > 1000
    chosen = fit_temperature(
        [([0.0, 1000.0], 0), ([1000.0, 0.0], 1)],
        surface="validation",
    )
    assert 0.05 <= chosen <= 5.0



def test_surface_form_ignores_family_and_splits_atom_from_prose():
    from hyperlexical.classification_v2_surface import (
        SURFACE_AMBIGUOUS,
        SURFACE_ATOM,
        SURFACE_PROSE,
        SURFACE_SHORTCUT_ABS_CORRELATION_MAX,
        surface_form,
    )

    assert surface_form("equip") == SURFACE_ATOM
    assert surface_form("pick 'em") == SURFACE_ATOM
    assert surface_form("meme") == SURFACE_ATOM
    assert surface_form("It is next to the River Avon, two miles upstream from Bristol Bridge.") == SURFACE_PROSE
    assert surface_form("An Internet meme depicting such an animal") == SURFACE_PROSE
    assert surface_form("404 coded sybau canon event") == SURFACE_AMBIGUOUS
    assert SURFACE_SHORTCUT_ABS_CORRELATION_MAX == 0.30


def test_surface_cells_share_applicability_authority():
    from hyperlexical.classification_v2_surface import surface_cell_weights

    rows = []
    rows.extend(
        {"lineage": "ai-native", "class": "OBSERVED", "split": "train", "text": "equip"}
        for _ in range(2)
    )
    rows.append(
        {
            "lineage": "ai-native",
            "class": "OBSERVED",
            "split": "train",
            "text": "A short lexical note about play, written as a definition.",
        }
    )
    rows.extend(
        {"lineage": "none", "class": "OBSERVED", "split": "train", "text": "stone"}
        for _ in range(4)
    )
    rows.append(
        {
            "lineage": "none",
            "class": "INFERRED",
            "split": "train",
            "text": "The house stands beside a stone bridge in the village.",
        }
    )
    weights = surface_cell_weights(rows, PROVENANCE_WEIGHTS)
    assert abs(sum(weights.values()) / len(weights) - 1.0) < 1e-12
    expected_support = {
        "FAMILY_PRESENT/ATOM": 2.0,
        "FAMILY_PRESENT/PROSE": 1.0,
        "NONE/ATOM": 4.0,
        "NONE/PROSE": PROVENANCE_WEIGHTS["inferred_none_applicability"],
    }
    aggregates = [weights[name] * expected_support[name] for name in expected_support]
    assert max(aggregates) - min(aggregates) < 1e-9


def test_ambiguous_text_is_masked_and_family_weights_stay_on_the_formula():
    atom = {"lineage": "ai-native", "class": "OBSERVED", "split": "train", "text": "gyatt"}
    prose = {
        "lineage": "ai-native",
        "class": "OBSERVED",
        "split": "train",
        "text": "A clipped definition of a vernacular atom in ordinary prose.",
    }
    none_atom = {"lineage": "none", "class": "OBSERVED", "split": "train", "text": "granite"}
    none_prose = {
        "lineage": "none",
        "class": "OBSERVED",
        "split": "train",
        "text": "Granite is a common igneous rock.",
    }
    ambiguous = {
        "lineage": "ai-native",
        "class": "OBSERVED",
        "split": "train",
        "text": "404 coded sybau canon event",
    }
    rows = [atom, prose, none_atom, none_prose, ambiguous]
    rows.extend(_row(name) for name in ACTIVE_FAMILY_VOCABULARY if name != "ai-native")
    contract = freeze_training_contract(rows)
    masked = example_loss(ambiguous, contract)
    assert masked["applicability_weight"] is None
    assert masked["family_weight"] is not None
    assert masked["surface"] == "AMBIGUOUS"
    present = example_loss(atom, contract)
    assert present["applicability_weight"] == contract["surface_cell_weights"]["FAMILY_PRESENT/ATOM"]
    assert present["applicability_weight"] != (
        PROVENANCE_WEIGHTS["observed_non_none_applicability"]
        * contract["applicability_weights"]["FAMILY_PRESENT"]
    )
    audit = support_audit(rows)
    assert contract["family_weights"] == family_loss_weights(audit)


def test_surface_shortcut_guard_is_preregistered_at_point_three():
    from hyperlexical.classification_v2_surface import applicability_surface_report

    assert decision_seal()["body"]["surface_shortcut_abs_correlation_max"] == 0.30
    flat = [
        {"text": "one", "lineage": "ai-native", "probability": 0.40, "prediction": "NONE", "family_prediction": "ai-native"},
        {"text": "two", "lineage": "none", "probability": 0.60, "prediction": "FAMILY_PRESENT"},
        {
            "text": "This prose sentence keeps the same probability band as the atoms.",
            "lineage": "ai-native",
            "probability": 0.45,
            "prediction": "NONE",
            "family_prediction": "ai-native",
        },
        {
            "text": "This other prose sentence also stays near the middle of the range.",
            "lineage": "none",
            "probability": 0.55,
            "prediction": "FAMILY_PRESENT",
        },
    ]
    balanced = applicability_surface_report(flat)
    assert balanced["pass"] is True
    assert abs(balanced["corr_word_count_p_family_present"]) <= 0.30
    assert balanced["applicability_by_cell"]["NONE/PROSE"]["support"] == 1
    assert balanced["family_macro_f1_by_surface"]["ATOM"] == 1.0


def test_missing_surface_cell_blocks_readiness():
    from hyperlexical.classification_v2_surface import surface_census

    rows = [_row(name) for name in ACTIVE_FAMILY_VOCABULARY]
    rows.append(_row("none"))
    report = readiness(
        rows,
        loader_status="PASS",
        surface_report={"pass": False, "representation_leaks": [], "cells": {}, "ambiguous": {}},
    )
    assert report["ready"] is False
    assert "APPLICABILITY_SURFACE_SHORTCUT" in report["blockers"]
    empty = surface_census(
        [{"task": "classify", "split": "train", "lineage": "none", "text": "stone"}]
    )
    assert empty["pass"] is False
    assert "FAMILY_PRESENT/ATOM" in empty["missing"]["train"]


def test_corrected_shortcut_diagnostic_conditions_on_gold():
    from hyperlexical.classification_v2_surface import (
        APPLICABILITY_SURFACE_F1_MIN,
        NONE_SURFACE_GAP_ABS_MAX,
        RESIDUALIZED_LENGTH_CORRELATION_ABS_MAX,
        applicability_surface_report,
    )

    body = decision_seal()["body"]
    assert body["surface_shortcut_abs_correlation_max"] == 0.30
    assert body["none_surface_gap_abs_max"] == NONE_SURFACE_GAP_ABS_MAX == 0.10
    assert body["residualized_length_correlation_abs_max"] == RESIDUALIZED_LENGTH_CORRELATION_ABS_MAX == 0.30
    assert body["applicability_surface_f1_min"] == APPLICABILITY_SURFACE_F1_MIN == 0.80
    assert body["surface_shortcut_diagnostic"] == "gold_conditional_residualized"
    prose = "This definition keeps a stable probability inside its gold class."
    records = []
    records.extend(
        {
            "text": "atom",
            "lineage": "ai-native",
            "probability": 0.78,
            "prediction": "FAMILY_PRESENT",
            "family_prediction": "ai-native",
        }
        for _ in range(6)
    )
    records.extend(
        {
            "text": prose,
            "lineage": "ai-native",
            "probability": 0.91,
            "prediction": "FAMILY_PRESENT",
            "family_prediction": "ai-native",
        }
        for _ in range(12)
    )
    records.extend(
        {"text": "stone", "lineage": "none", "probability": 0.13, "prediction": "NONE"}
        for _ in range(12)
    )
    records.extend(
        {"text": prose, "lineage": "none", "probability": 0.13, "prediction": "NONE"}
        for _ in range(4)
    )
    report = applicability_surface_report(records)
    invariance = report["invariance"]
    assert report["pass"] is False
    assert abs(report["corr_word_count_p_family_present"]) > 0.30
    assert invariance["historical_blunt_guard"]["pass"] is False
    assert invariance["pass"] is True
    assert abs(invariance["family_surface_gap"] - 0.13) < 1e-9
    assert invariance["none_surface_gap"] == 0.0
    assert invariance["guard_results"]["none_surface_gap"] is True
    assert abs(invariance["residualized_length_correlation"]["correlation"]) < 1e-9
    assert invariance["conditional_length_correlation"]["FAMILY_PRESENT"]["correlation"] == 1.0
    assert invariance["conditional_length_correlation"]["NONE"]["correlation"] is None
    assert invariance["conditional_length_correlation"]["FAMILY_PRESENT"]["n"] == 18
    assert invariance["conditional_length_correlation"]["NONE"]["n"] == 16
    assert "surface_prose" in invariance["residualized_length_correlation"]["columns"]
    assert "gold_family_present" in invariance["residualized_length_correlation"]["columns"]


def test_none_surface_gap_is_the_shortcut_signal():
    from hyperlexical.classification_v2_surface import applicability_invariance

    prose = "This sentence is prose and should not raise applicability on none."
    records = [
        {
            "text": "atom",
            "lineage": "ai-native",
            "probability": 0.80,
            "prediction": "FAMILY_PRESENT",
            "family_prediction": "ai-native",
        },
        {
            "text": prose,
            "lineage": "ai-native",
            "probability": 0.80,
            "prediction": "FAMILY_PRESENT",
            "family_prediction": "ai-native",
        },
        {"text": "stone", "lineage": "none", "probability": 0.10, "prediction": "NONE"},
        {"text": prose, "lineage": "none", "probability": 0.40, "prediction": "NONE"},
    ]
    invariance = applicability_invariance(records)
    assert abs(invariance["none_surface_gap"] - 0.30) < 1e-12
    assert invariance["family_surface_gap"] == 0.0
    assert invariance["guard_results"]["none_surface_gap"] is False
    assert invariance["pass"] is False


def test_residual_length_within_gold_fails_when_surface_means_match():
    from hyperlexical.classification_v2_surface import applicability_invariance

    short = "A short prose note is here."
    long = "A much longer prose note that keeps adding ordinary words until the count is high."
    records = [
        {"text": "atom", "lineage": "none", "probability": 0.20, "prediction": "NONE"},
        {"text": "rock", "lineage": "none", "probability": 0.20, "prediction": "NONE"},
        {"text": short, "lineage": "none", "probability": 0.05, "prediction": "NONE"},
        {"text": long, "lineage": "none", "probability": 0.35, "prediction": "NONE"},
        {
            "text": "equip",
            "lineage": "ai-native",
            "probability": 0.80,
            "prediction": "FAMILY_PRESENT",
            "family_prediction": "ai-native",
        },
        {
            "text": short,
            "lineage": "ai-native",
            "probability": 0.80,
            "prediction": "FAMILY_PRESENT",
            "family_prediction": "ai-native",
        },
    ]
    invariance = applicability_invariance(records)
    assert abs(invariance["none_surface_gap"]) < 1e-9
    assert invariance["guard_results"]["none_surface_gap"] is True
    assert invariance["within_cell_length_correlation"]["NONE/PROSE"]["n"] == 2
    prose_correlation = invariance["within_cell_length_correlation"]["NONE/PROSE"]["correlation"]
    assert prose_correlation is not None and abs(prose_correlation - 1.0) < 1e-12
    assert abs(invariance["residualized_length_correlation"]["correlation"]) > 0.30
    assert invariance["guard_results"]["residualized_length_correlation"] is False
    assert invariance["pass"] is False


def test_family_fusion_standardizes_both_components():
    from hyperlexical.classification_v2_prototype import (
        FUSION_ALPHA,
        FUSION_BETA,
        LAMBDA_PROTO,
        PROTO_TAU,
        fuse_family_logits,
        population_standardize,
    )

    body = decision_seal()["body"]
    assert body["family_fusion_alpha"] == FUSION_ALPHA == 1.0
    assert body["family_fusion_beta"] == FUSION_BETA == 1.0
    assert body["family_prototype_tau"] == PROTO_TAU == 0.10
    assert body["family_prototype_lambda"] == LAMBDA_PROTO == 0.5
    assert body["family_hard_negative_multiplier"] == 2.0
    assert body["family_prototypes"] == "frozen"
    assert body["selection_score"].startswith("0.50*active_family_macro_f1")
    base = fuse_family_logits([0.1, 0.2, 0.4], [3.0, -1.0, 0.5])
    scaled = fuse_family_logits([1.0, 2.0, 4.0], [30.0, -10.0, 5.0])
    assert all(abs(left - right) < 1e-9 for left, right in zip(base, scaled))
    assert population_standardize([2.0, 2.0, 2.0]) == [0.0, 0.0, 0.0]
    assert abs(sum(base)) < 1e-9


def test_prototype_contrastive_loss_weights_recorded_hard_negatives():
    from hyperlexical.classification_v2_prototype import (
        CONFUSABLE_COSINE,
        HARD_NEGATIVE_MULTIPLIER,
        PROTO_TAU,
        confusion_clusters,
        cosine_matrix,
        denominator_multipliers,
        hard_negatives,
        prototype_contrastive_nll,
    )

    names = ("alpha", "beta", "gamma", "delta")
    vectors = [
        [1.0, 0.0, 0.0],
        [0.9, 0.1, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]
    matrix = cosine_matrix(vectors)
    negatives = hard_negatives(matrix, names, 3)
    assert list(negatives) == list(names)
    assert negatives["alpha"][0]["family"] == "beta"
    assert all(item["family"] != "alpha" for item in negatives["alpha"])
    assert len(negatives["alpha"]) == 3
    pairs = [
        {"cosine": 0.91, "left": "alpha", "right": "beta"},
        {"cosine": 0.2, "left": "gamma", "right": "delta"},
    ]
    assert confusion_clusters([pairs[0]], names) == [["alpha", "beta"]]
    assert CONFUSABLE_COSINE == 0.80
    multipliers = denominator_multipliers(names, negatives)
    assert multipliers[0][0] == 1.0
    assert HARD_NEGATIVE_MULTIPLIER in multipliers[0]
    cosine = [0.2, 0.2, -0.4, -0.5]
    plain = [1.0, 1.0, 1.0, 1.0]
    weighted = prototype_contrastive_nll(cosine, 0, multipliers[0])
    unweighted = prototype_contrastive_nll(cosine, 0, plain)
    assert weighted > unweighted
    assert prototype_contrastive_nll([1.0, -1.0], 0, [1.0, 1.0]) < prototype_contrastive_nll(
        [-1.0, 1.0], 0, [1.0, 1.0]
    )
    assert PROTO_TAU == 0.10
