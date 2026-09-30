"""Unit tests for HYPERLEX_V5_STAGE_A_TWO_STAGE_DECISION_GRAPH_V1 (spec only)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a import (  # noqa: E402
    ACCEPTANCE_GATES,
    BEST_SHA,
    FLAT_HEAD_STATUS as FLAT_STATUS_PARENT,
)
from hyperlexical.classification_v5_stage_a_two_stage import (  # noqa: E402
    AUTHORIZE_RULE,
    EXPERIMENT_ID,
    FLAT_HEAD_STATUS,
    GATE1_THRESHOLDS,
    GATE2_PRESENT_THRESHOLDS,
    LAMBDA_GATE2,
    LAST_TRAINABLE_ENCODER_LAYERS,
    NO_DATA,
    TWO_STAGE_RULE,
    architecture_contract,
    calibrate_two_stage_thresholds,
    checkpoint_selection_score,
    compute_gate1_class_weights,
    compute_gate2_class_weights,
    decide_two_stage,
    design_freeze_receipt,
    gate1_target,
    gate2_eligible,
    gate2_target,
    gate1_confusion_matrix,
    gate2_confusion_matrix,
    loss_contract,
    select_checkpoint,
)


def test_frozen_constants():
    assert TWO_STAGE_RULE == "HYPERLEX_V5_STAGE_A_TWO_STAGE_DECISION_GRAPH_V1"
    assert AUTHORIZE_RULE == "AUTHORIZE_V5_STAGE_A_TWO_STAGE_TRAIN_V1"
    assert EXPERIMENT_ID == "HLX-CLASSIFICATION-V5-STAGE-A-005-TWO-STAGE"
    assert LAMBDA_GATE2 == 1.0
    assert LAST_TRAINABLE_ENCODER_LAYERS == 2
    assert FLAT_HEAD_STATUS == "DEPRECATED_FOR_V5_STAGE_A_CANONICAL_DECISION"
    assert FLAT_STATUS_PARENT == FLAT_HEAD_STATUS
    assert GATE1_THRESHOLDS == [round(0.50 + 0.05 * i, 2) for i in range(10)]
    assert GATE2_PRESENT_THRESHOLDS == GATE1_THRESHOLDS
    assert len(GATE1_THRESHOLDS) * len(GATE2_PRESENT_THRESHOLDS) == 100
    assert ACCEPTANCE_GATES["EVIDENCE_PRESENT_recall_min"] == 0.70
    assert ACCEPTANCE_GATES["NO_EVIDENCE_recall_min"] == 0.90
    assert ACCEPTANCE_GATES["false_evidence_entry_rate_on_none_max"] == 0.05


def test_gate_gold_mapping():
    assert gate1_target("NO_EVIDENCE") == 0
    assert gate1_target("EVIDENCE_PRESENT") == 1
    assert gate1_target("UNCERTAIN") == 1
    assert gate2_eligible("EVIDENCE_PRESENT") is True
    assert gate2_eligible("UNCERTAIN") is True
    assert gate2_eligible("NO_EVIDENCE") is False
    assert gate2_target("EVIDENCE_PRESENT") == 1
    assert gate2_target("UNCERTAIN") == 0
    with pytest.raises(ValueError, match="LABEL_MAPPING_INVALID"):
        gate1_target("NOT_A_LABEL")
    with pytest.raises(ValueError, match="gate2_ineligible"):
        gate2_target("NO_EVIDENCE")


def test_gate2_none_excluded_from_weights_and_loss_scope():
    rows = [
        {"evidence_label": "NO_EVIDENCE", "provenance": "OBSERVED"},
        {"evidence_label": "NO_EVIDENCE", "provenance": "INFERRED"},
        {"evidence_label": "EVIDENCE_PRESENT", "provenance": "OBSERVED"},
        {"evidence_label": "UNCERTAIN", "provenance": "INFERRED"},
    ]
    g1 = compute_gate1_class_weights(rows)
    assert set(g1["class_weights"]) == {"NO_EVIDENCE", "POSSIBLE_EVIDENCE"}
    # Gate-1 effective: NONE = 1.0 + 0.5; POSSIBLE = 1.0 + 0.5
    assert g1["effective_counts"]["NO_EVIDENCE"] == pytest.approx(1.5)
    assert g1["effective_counts"]["POSSIBLE_EVIDENCE"] == pytest.approx(1.5)
    g2 = compute_gate2_class_weights(rows)
    assert g2["n_eligible_train"] == 2
    assert g2["effective_counts"]["CONFIRMED_PRESENT"] == pytest.approx(1.0)
    assert g2["effective_counts"]["UNCERTAIN"] == pytest.approx(0.5)
    for weight in list(g1["class_weights"].values()) + list(
        g2["class_weights"].values()
    ):
        assert 0.50 <= weight <= 2.00
    none_only = [
        {"evidence_label": "NO_EVIDENCE", "provenance": "OBSERVED"},
    ]
    with pytest.raises(ValueError, match="NO_DATA"):
        compute_gate2_class_weights(none_only)
    assert loss_contract()["gate2"]["none_rows_contribute"] is False
    assert loss_contract()["lambda_gate2"] == 1.0
    assert loss_contract()["focal_forbidden"] is True


def test_decide_two_stage_policy():
    assert (
        decide_two_stage(
            p_possible=0.40,
            p_confirmed=0.99,
            gate1_threshold=0.50,
            gate2_present_threshold=0.50,
        )
        == "NO_EVIDENCE"
    )
    assert (
        decide_two_stage(
            p_possible=0.80,
            p_confirmed=0.90,
            gate1_threshold=0.50,
            gate2_present_threshold=0.85,
        )
        == "EVIDENCE_PRESENT"
    )
    assert (
        decide_two_stage(
            p_possible=0.80,
            p_confirmed=0.60,
            gate1_threshold=0.50,
            gate2_present_threshold=0.85,
        )
        == "UNCERTAIN"
    )


def test_threshold_grid_and_selection_order():
    # Perfect separable synthetic val: NONE low possible; PRESENT high both;
    # UNCERTAIN high possible / low confirmed.
    golds = (
        ["NO_EVIDENCE"] * 20
        + ["EVIDENCE_PRESENT"] * 10
        + ["UNCERTAIN"] * 10
    )
    p_possible = [0.10] * 20 + [0.95] * 10 + [0.90] * 10
    p_confirmed = [0.10] * 20 + [0.95] * 10 + [0.20] * 10
    result = calibrate_two_stage_thresholds(
        golds=golds, p_possible=p_possible, p_confirmed=p_confirmed
    )
    assert result["n_candidates"] == 100
    assert result["feasible"] is True
    assert result["disposition"] == "SETTLED_PASS"
    assert result["chosen"]["gate1_threshold"] >= 0.50
    # Among passing, higher Gate-1 / Gate-2 preferred after metric ties.
    assert result["chosen"]["metrics"]["acceptance_pass"] is True

    # Impossible: always predict PRESENT for NONE → false entry.
    bad = calibrate_two_stage_thresholds(
        golds=["NO_EVIDENCE"] * 10 + ["EVIDENCE_PRESENT"] * 10,
        p_possible=[0.99] * 20,
        p_confirmed=[0.99] * 20,
    )
    assert bad["feasible"] is False
    assert bad["disposition"] == "SETTLED_FAIL"
    assert bad["chosen"] is None


def test_checkpoint_selection_independent_of_thresholds():
    assert checkpoint_selection_score(gate1_macro_f1=0.8, gate2_macro_f1=0.6) == pytest.approx(
        0.70
    )
    candidates = [
        {
            "epoch": 3,
            "selection_score": 0.70,
            "gate1_false_possible_entry_rate": 0.04,
            "gate2_confirmed_present_recall": 0.80,
        },
        {
            "epoch": 2,
            "selection_score": 0.70,
            "gate1_false_possible_entry_rate": 0.02,
            "gate2_confirmed_present_recall": 0.70,
        },
        {
            "epoch": 1,
            "selection_score": 0.65,
            "gate1_false_possible_entry_rate": 0.01,
            "gate2_confirmed_present_recall": 0.99,
        },
    ]
    best = select_checkpoint(candidates)
    assert best["epoch"] == 2  # same score, lower false-entry


def test_confusion_and_architecture_forbid_extras():
    golds = ["NO_EVIDENCE", "EVIDENCE_PRESENT", "UNCERTAIN", "NO_EVIDENCE"]
    p_possible = [0.1, 0.9, 0.85, 0.8]
    p_confirmed = [0.1, 0.9, 0.2, 0.9]
    g1 = gate1_confusion_matrix(
        golds, p_possible=p_possible, gate1_threshold=0.5
    )
    assert g1["matrix"][0][0] == 1  # NONE→NONE
    assert g1["matrix"][0][1] == 1  # NONE→POSSIBLE (leak)
    g2 = gate2_confusion_matrix(
        golds,
        p_possible=p_possible,
        p_confirmed=p_confirmed,
        gate1_threshold=0.5,
        gate2_present_threshold=0.7,
    )
    assert g2["n_eligible"] == 2
    assert g2["matrix"] != NO_DATA
    arch = architecture_contract()
    assert arch["forbidden_additions"] == [
        "mlp_head",
        "attention_block",
        "prototype",
        "retrieval",
        "family_head",
    ]
    assert arch["trainable"]["mutate_best"] is False
    assert arch["pooling"] == "last_hidden_state[:,0]"


def test_design_freeze_receipt_not_authorized():
    receipt = design_freeze_receipt(code_revision="testrev")
    assert receipt["DESIGN_STATE"] == "FROZEN"
    assert receipt["TRAIN"] is False
    assert receipt["TRAIN_AUTHORIZED"] is False
    assert receipt["AUTHORIZE_RULE_NEXT"] == AUTHORIZE_RULE
    assert receipt["BEST"] == "UNCHANGED"
    assert receipt["BEST_SHA256"] == BEST_SHA
    assert receipt["RESERVE"] == "unused"
    assert receipt["compatibility"]["v1r9_dataset_unchanged"] is True
    assert "design_receipt_sha256" in receipt
