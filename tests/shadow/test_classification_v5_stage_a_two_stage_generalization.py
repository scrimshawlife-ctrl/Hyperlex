"""Authorization pins for V1R1 two-stage generalization retrain."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_two_stage import (  # noqa: E402
    ARCHITECTURE_RECEIPT_SHA256,
    EXPERIMENT_ID as PRIOR_EXPERIMENT_ID,
)
from hyperlexical.classification_v5_stage_a_two_stage_generalization import (  # noqa: E402
    AUTHORIZE_RULE,
    AUTHORIZED_DATASET_SHA,
    AUTHORIZED_READINESS_SHA,
    AUTHORIZED_SURFACE_RECEIPT_SHA,
    EXPECTED_TRAIN_ROWS,
    EXPECTED_VALIDATION_ROWS,
    EXPERIMENT_ID,
    INITIALIZATION_POLICY,
    PARENT_STAGE_A_BEST_SHA,
    PARENT_TWO_STAGE_EXPERIMENT_ID,
    TRAIN_ONCE_ACTION,
    generalization_resolved_config,
    resolve_v1r1_two_stage_class_weights,
)


def test_experiment_identity_is_new_and_distinct():
    assert EXPERIMENT_ID == (
        "HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-GENERALIZATION-001"
    )
    assert EXPERIMENT_ID != PRIOR_EXPERIMENT_ID
    assert PARENT_TWO_STAGE_EXPERIMENT_ID == PRIOR_EXPERIMENT_ID
    assert AUTHORIZE_RULE == (
        "AUTHORIZE_V5_STAGE_A_TWO_STAGE_RETRAIN_ON_GENERALIZATION_SURFACE"
    )
    assert TRAIN_ONCE_ACTION == "TRAIN_V5_STAGE_A_TWO_STAGE_GENERALIZATION_ONCE"


def test_v1r1_pins_and_frozen_architecture():
    assert AUTHORIZED_DATASET_SHA.startswith("4095036e")
    assert AUTHORIZED_READINESS_SHA.startswith("c4b5fc07")
    assert AUTHORIZED_SURFACE_RECEIPT_SHA.startswith("3dbdd9b2")
    assert EXPECTED_TRAIN_ROWS == 2531
    assert EXPECTED_VALIDATION_ROWS == 1054
    assert ARCHITECTURE_RECEIPT_SHA256.startswith("631427cc")
    assert PARENT_STAGE_A_BEST_SHA.startswith("cd2829c1")


def test_initialization_policy_fresh_from_model_wide_best():
    assert INITIALIZATION_POLICY["stage_a_best_continuation"] is False
    assert INITIALIZATION_POLICY["base_encoder_source"] == "MODEL_WIDE_BEST"
    assert INITIALIZATION_POLICY["base_encoder_sha256"].startswith("9fba0f66")
    assert INITIALIZATION_POLICY["gate_heads"] == "fresh_xavier_uniform_bias_zeros"
    assert INITIALIZATION_POLICY["conflict_with_stage_a_best_continuation"] is False


def test_resolve_v1r1_weights_rejects_wrong_dataset_and_counts():
    rows = (
        [{"identity": f"n{i}", "evidence_label": "NO_EVIDENCE", "provenance": "INFERRED"}]
        for i in range(10)
    )
    try:
        resolve_v1r1_two_stage_class_weights(
            list(rows),
            dataset_sha256="0" * 64,
            train_split_sha256="x",
            train_identity_list_sha256="y",
            code_revision="t",
        )
        assert False, "expected dataset mismatch"
    except ValueError as exc:
        assert "dataset_mismatch" in str(exc)


def test_resolve_v1r1_weights_formula_on_matching_pins(monkeypatch):
    # Build a miniature train set then temporarily relax count/split pins via
    # direct gate helpers already covered elsewhere; here assert config binds.
    from hyperlexical.classification_v5_stage_a_two_stage import (
        compute_gate1_class_weights,
        compute_gate2_class_weights,
    )

    rows = (
        [
            {
                "evidence_label": "NO_EVIDENCE",
                "provenance": "OBSERVED",
                "identity": f"a{i}",
            }
            for i in range(4)
        ]
        + [
            {
                "evidence_label": "EVIDENCE_PRESENT",
                "provenance": "INFERRED",
                "identity": f"b{i}",
            }
            for i in range(4)
        ]
        + [
            {
                "evidence_label": "UNCERTAIN",
                "provenance": "OBSERVED",
                "identity": f"c{i}",
            }
            for i in range(2)
        ]
    )
    g1 = compute_gate1_class_weights(rows)
    g2 = compute_gate2_class_weights(rows)
    assert g1["accounts"]["NO_EVIDENCE"]["rows"] == 4
    assert g2["n_eligible_train"] == 6
    for weight in list(g1["class_weights"].values()) + list(g2["class_weights"].values()):
        assert 0.50 <= float(weight) <= 2.00

    # Config builder requires exact V1R1 pins; feed a synthetic weight artifact
    # shaped like the real one with those pins.
    artifact = {
        "CLASS_WEIGHT_ARTIFACT_SHA256": "ab" * 32,
        "literal_weights": {
            "gate1": dict(g1["class_weights"]),
            "gate2": dict(g2["class_weights"]),
        },
    }
    from hyperlexical import classification_v5_stage_a_two_stage_generalization as mod

    cfg = generalization_resolved_config(
        dataset_sha256=mod.AUTHORIZED_DATASET_SHA,
        class_weight_artifact=artifact,
        code_revision="test",
        tokenizer_identity="local_files_only:ModernBERT-base",
        train_split_sha256=mod.EXPECTED_TRAIN_SPLIT_SHA256,
        validation_split_sha256=mod.EXPECTED_VALIDATION_SPLIT_SHA256,
        train_identity_list_sha256=mod.EXPECTED_TRAIN_IDENTITY_LIST_SHA256,
        validation_identity_list_sha256=mod.EXPECTED_VALIDATION_IDENTITY_LIST_SHA256,
        readiness_sha256=mod.AUTHORIZED_READINESS_SHA,
        surface_receipt_sha256=mod.AUTHORIZED_SURFACE_RECEIPT_SHA,
    )
    assert cfg["experiment_id"] == EXPERIMENT_ID
    assert cfg["initialization_policy"]["stage_a_best_continuation"] is False
    assert cfg["split"]["TRAIN_ROWS"] == 2531
    assert "training_config_sha256" in cfg
    assert cfg["spent_reserve_access"].startswith("FORBIDDEN")


def test_train_pins_and_steps():
    from hyperlexical.classification_v5_stage_a_two_stage_generalization import (
        AUTHORIZED_AUTH_RECEIPT_SHA256,
        AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
        AUTHORIZED_TRAINING_CONFIG_SHA256,
        EXPECTED_GATE2_ELIGIBLE_ROWS,
        EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,
        EXPECTED_TRAIN_ROWS,
        INITIALIZATION_POLICY,
        LITERAL_GATE1_WEIGHTS,
        LITERAL_GATE2_WEIGHTS,
        DROP_LAST,
        full_pass_batch_indices,
    )
    assert AUTHORIZED_AUTH_RECEIPT_SHA256.startswith("f7d4f3ad")
    assert AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256.startswith("80b7f899")
    assert AUTHORIZED_TRAINING_CONFIG_SHA256.startswith("1527ae18")
    assert EXPECTED_TRAIN_ROWS == 2531
    assert EXPECTED_GATE2_ELIGIBLE_ROWS == 1246
    assert EXPECTED_OPTIMIZER_STEPS_PER_EPOCH == 317
    assert INITIALIZATION_POLICY["stage_a_best_continuation"] is False
    assert LITERAL_GATE1_WEIGHTS["NO_EVIDENCE"] == 1.0006485087033488
    assert LITERAL_GATE2_WEIGHTS["UNCERTAIN"] == 1.375376244120633
    steps = len(
        full_pass_batch_indices(
            EXPECTED_TRAIN_ROWS, batch_size=8, seed=42, drop_last=DROP_LAST
        )
    )
    assert steps == 317
