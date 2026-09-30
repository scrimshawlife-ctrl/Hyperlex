"""Unit tests for HYPERLEX_V5_STAGE_A_TWO_STAGE_DECISION_GRAPH_V1 + auth weights."""

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
    ARCHITECTURE_RECEIPT_SHA256,
    AUTHORIZE_RULE,
    EXPERIMENT_ID,
    FLAT_HEAD_STATUS,
    GATE1_THRESHOLDS,
    GATE2_PRESENT_THRESHOLDS,
    LAMBDA_GATE2,
    LAST_TRAINABLE_ENCODER_LAYERS,
    NO_DATA,
    TRAIN_ONCE_ACTION,
    TRAIN_RULE,
    TWO_STAGE_RULE,
    architecture_contract,
    calibrate_two_stage_thresholds,
    checkpoint_selection_score,
    decide_two_stage,
    gate1_target,
    gate2_eligible,
    gate2_target,
    gate1_confusion_matrix,
    gate2_confusion_matrix,
    loss_contract,
    resolve_two_stage_class_weights,
    runner_authorization_checks,
    select_checkpoint,
    two_stage_resolved_config,
)


def test_frozen_constants():
    assert TWO_STAGE_RULE == "HYPERLEX_V5_STAGE_A_TWO_STAGE_DECISION_GRAPH_V1"
    assert AUTHORIZE_RULE == "AUTHORIZE_V5_STAGE_A_TWO_STAGE_TRAIN_V1"
    assert TRAIN_RULE == "HYPERLEX_V5_STAGE_A_TWO_STAGE_TRAIN_V1"
    assert TRAIN_ONCE_ACTION == "TRAIN_V5_STAGE_A_TWO_STAGE_ONCE"
    assert EXPERIMENT_ID == "HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-001"
    assert ARCHITECTURE_RECEIPT_SHA256 == (
        "631427cc4c1b09bac1e3a2c5e081c7e9fc0947babda26c03cb73895f47754697"
    )
    assert LAMBDA_GATE2 == 1.0
    assert LAST_TRAINABLE_ENCODER_LAYERS == 2
    assert FLAT_HEAD_STATUS == "DEPRECATED_FOR_V5_STAGE_A_CANONICAL_DECISION"
    assert FLAT_STATUS_PARENT == FLAT_HEAD_STATUS
    assert len(GATE1_THRESHOLDS) * len(GATE2_PRESENT_THRESHOLDS) == 100
    assert ACCEPTANCE_GATES["EVIDENCE_PRESENT_recall_min"] == 0.70


def test_gate_gold_mapping():
    assert gate1_target("NO_EVIDENCE") == 0
    assert gate1_target("EVIDENCE_PRESENT") == 1
    assert gate1_target("UNCERTAIN") == 1
    assert gate2_eligible("NO_EVIDENCE") is False
    assert gate2_target("EVIDENCE_PRESENT") == 1
    assert gate2_target("UNCERTAIN") == 0
    with pytest.raises(ValueError, match="gate2_ineligible"):
        gate2_target("NO_EVIDENCE")


def test_resolve_class_weights_v1r9_shape_and_invariants():
    # Synthetic train mirroring V1R9 proportions at tiny scale.
    rows = (
        [{"evidence_label": "NO_EVIDENCE", "provenance": "OBSERVED"}] * 3
        + [{"evidence_label": "NO_EVIDENCE", "provenance": "INFERRED"}] * 30
        + [{"evidence_label": "EVIDENCE_PRESENT", "provenance": "OBSERVED"}] * 2
        + [{"evidence_label": "EVIDENCE_PRESENT", "provenance": "INFERRED"}] * 4
        + [{"evidence_label": "UNCERTAIN", "provenance": "OBSERVED"}] * 2
        + [{"evidence_label": "UNCERTAIN", "provenance": "INFERRED"}] * 1
    )
    artifact = resolve_two_stage_class_weights(
        rows,
        dataset_sha256="8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a",
        train_split_sha256="synthetic",
        code_revision="test",
    )
    assert artifact["Gate1"]["coverage"]["n_train"] == len(rows)
    assert artifact["Gate2"]["coverage"]["n_eligible"] == 9
    assert artifact["Gate2"]["coverage"]["n_none_excluded"] == 33
    g1 = artifact["literal_weights"]["gate1"]
    g2 = artifact["literal_weights"]["gate2"]
    for weight in list(g1.values()) + list(g2.values()):
        assert 0.50 <= weight <= 2.00
    # Required accounting fields present.
    for label in ("NO_EVIDENCE", "POSSIBLE_EVIDENCE"):
        acct = artifact["Gate1"][label]
        for key in (
            "rows",
            "OBSERVED_count",
            "INFERRED_count",
            "effective_count",
            "raw_weight",
            "normalized_weight",
            "final_weight",
        ):
            assert key in acct
    # NONE rows must not appear in Gate2 accounts.
    assert artifact["Gate2"]["UNCERTAIN"]["rows"] + artifact["Gate2"][
        "CONFIRMED_PRESENT"
    ]["rows"] == 9
    assert "CLASS_WEIGHT_ARTIFACT_SHA256" in artifact

    resolved = two_stage_resolved_config(
        dataset_sha256="8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a",
        class_weight_artifact=artifact,
        code_revision="test",
        tokenizer_identity="local_files_only:ModernBERT-base",
    )
    assert resolved["gate1_class_weights_literal"] == g1
    assert resolved["gate2_class_weights_literal"] == g2
    assert resolved["architecture_receipt_sha256"] == ARCHITECTURE_RECEIPT_SHA256
    assert resolved["experiment_id"] == EXPERIMENT_ID
    assert "training_config_sha256" in resolved


def test_resolve_rejects_wrong_dataset():
    with pytest.raises(ValueError, match="dataset_mismatch"):
        resolve_two_stage_class_weights(
            [{"evidence_label": "NO_EVIDENCE", "provenance": "OBSERVED"}],
            dataset_sha256="0" * 64,
            train_split_sha256="x",
            code_revision="t",
        )


def test_decide_and_threshold_settled_fail():
    assert (
        decide_two_stage(
            p_possible=0.4,
            p_confirmed=0.99,
            gate1_threshold=0.5,
            gate2_present_threshold=0.5,
        )
        == "NO_EVIDENCE"
    )
    bad = calibrate_two_stage_thresholds(
        golds=["NO_EVIDENCE"] * 10 + ["EVIDENCE_PRESENT"] * 10,
        p_possible=[0.99] * 20,
        p_confirmed=[0.99] * 20,
    )
    assert bad["disposition"] == "SETTLED_FAIL"


def test_checkpoint_and_runner_checks():
    assert checkpoint_selection_score(gate1_macro_f1=0.8, gate2_macro_f1=0.6) == pytest.approx(
        0.70
    )
    best = select_checkpoint(
        [
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
        ]
    )
    assert best["epoch"] == 2
    checks = runner_authorization_checks(
        train_authorized=True,
        experiment_id=EXPERIMENT_ID,
        dataset_sha256="8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a",
        architecture_receipt_sha256=ARCHITECTURE_RECEIPT_SHA256,
        resolved_config_sha256="abc",
        authorized_config_sha256="abc",
        best_sha256=BEST_SHA,
        surface_readiness="PASS",
        label_mapping="PASS",
        label_provenance_invalid_rows=0,
        prior_run_count=0,
        reserve_consumed=False,
        class_weight_artifact_sha256="w",
        authorized_class_weight_artifact_sha256="w",
    )
    assert checks["pass"] is True
    bad = runner_authorization_checks(
        train_authorized=False,
        experiment_id=EXPERIMENT_ID,
        dataset_sha256="8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a",
        architecture_receipt_sha256=ARCHITECTURE_RECEIPT_SHA256,
        resolved_config_sha256="abc",
        authorized_config_sha256="abc",
        best_sha256=BEST_SHA,
        surface_readiness="PASS",
        label_mapping="PASS",
        label_provenance_invalid_rows=0,
        prior_run_count=0,
        reserve_consumed=False,
        class_weight_artifact_sha256="w",
        authorized_class_weight_artifact_sha256="w",
    )
    assert bad["pass"] is False


def test_confusion_architecture_loss():
    golds = ["NO_EVIDENCE", "EVIDENCE_PRESENT", "UNCERTAIN", "NO_EVIDENCE"]
    p_possible = [0.1, 0.9, 0.85, 0.8]
    p_confirmed = [0.1, 0.9, 0.2, 0.9]
    g1 = gate1_confusion_matrix(golds, p_possible=p_possible, gate1_threshold=0.5)
    assert g1["matrix"][0][0] == 1
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
    assert arch["trainable"]["mutate_best"] is False
    assert loss_contract()["lambda_gate2"] == 1.0
    assert loss_contract()["focal_forbidden"] is True
