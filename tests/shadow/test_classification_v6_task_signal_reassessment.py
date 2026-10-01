"""CPU tests for V6 task-signal reassessment contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_task_signal_reassessment import (
    ZERO_SHOT_REFERENCE,
    architecture_restart_allowed,
    audit_all_descriptions,
    classify_learning_curve,
    description_variants_for_label,
    oracle_description,
    reassessment_contract,
    select_primary_diagnosis,
)


def test_zero_shot_reference_frozen():
    c = reassessment_contract()
    assert c["zero_shot_reference"]["rep_system_macro_f1"] == ZERO_SHOT_REFERENCE[
        "rep_system_macro_f1"
    ]
    assert abs(c["zero_shot_reference"]["rep_system_macro_f1"] - 0.1622371780444463) < 1e-12
    assert c["advancement_floor_locked"] is True
    assert "another_architecture_family_bakeoff" in c["forbidden"]
    assert c["qual_policy"]["inspected"] is False


def test_description_audit_and_variants():
    audit = audit_all_descriptions()
    assert audit["n"] >= 16
    assert "counts" in audit
    v = description_variants_for_label("domain.gambling")
    assert set(v) == {
        "canonical_name",
        "canonical_full_definition",
        "positive_core",
        "definition_plus_exclusion",
    }
    o = oracle_description("domain.technology.ai_discourse")
    assert "required_parent" in o
    assert "NEAR_NEIGHBORS" in o


def test_learning_curve_and_diagnosis_routing():
    sat = classify_learning_curve(
        [
            {"fraction": 0.1, "rep_system_macro_f1": 0.11},
            {"fraction": 0.5, "rep_system_macro_f1": 0.13},
            {"fraction": 1.0, "rep_system_macro_f1": 0.134},
        ]
    )
    assert sat["class"] in {"EARLY_SATURATION", "DATA_LIMITED"}
    neg = classify_learning_curve(
        [
            {"fraction": 0.1, "rep_system_macro_f1": 0.15},
            {"fraction": 1.0, "rep_system_macro_f1": 0.10},
        ]
    )
    assert neg["class"] == "NEGATIVE_SCALING"

    # Strong semantic model clears floor → rebase
    d = select_primary_diagnosis(
        {
            "strong_semantic_rep": 0.25,
            "frozen_encoder_rep": 0.16,
            "full_finetune_rep": 0.13,
            "learning_curve": sat,
            "oracle_gain": 0.0,
            "label_description_instability": False,
            "catastrophic_task_adaptation": False,
        }
    )
    assert d["primary_diagnosis"] == "PRETRAINED_REPRESENTATION_MISMATCH"
    assert d["NEXT_ACTION"] == "REBASE_V6_ON_STRONGER_PRETRAINED_SEMANTIC_ENCODER"

    # Frozen beats fine-tune with drift
    d2 = select_primary_diagnosis(
        {
            "strong_semantic_rep": 0.17,
            "frozen_encoder_rep": 0.18,
            "full_finetune_rep": 0.12,
            "learning_curve": sat,
            "catastrophic_task_adaptation": True,
        }
    )
    assert d2["primary_diagnosis"] == "FINE_TUNING_DESTROYS_TRANSFER_GEOMETRY"
    assert d2["NEXT_ACTION"] == "DESIGN_PARAMETER_EFFICIENT_OR_FROZEN_V6_MODEL"

    gate = architecture_restart_allowed(
        best_diagnostic_rep=0.17,
        learning_curve=sat,
        margin_improved=False,
        stable_gap=True,
        beats_zero_shot=False,
    )
    assert gate["allowed"] is False
