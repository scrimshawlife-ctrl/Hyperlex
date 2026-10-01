"""Unit pins for TRAIN_STAGE_A_IDENT_FILTERED_FACTORIZED_ONCE."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_ident_filtered_authorize import (  # noqa: E402
    AUTHORIZED_AUTH_RECEIPT_SHA256,
    AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
    AUTHORIZED_TRAINING_CONFIG_SHA256,
    EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,
    EXPECTED_TRAIN_ROWS,
    EXPECTED_VALIDATION_ROWS,
    EXPERIMENT_ID,
    INITIALIZATION_POLICY,
    LITERAL_RELATION_WEIGHTS,
    LITERAL_RESOLVABILITY_WEIGHTS,
    TRAIN_ONCE_ACTION,
    TRAIN_RULE,
    build_v1r2_ident_filtered_split_witness,
)
from hyperlexical.classification_v5_stage_a_gold_identifiability_filter import (  # noqa: E402
    V1R2_DATASET_SHA256_PIN,
)


def test_train_once_pins():
    assert TRAIN_ONCE_ACTION == "TRAIN_STAGE_A_IDENT_FILTERED_FACTORIZED_ONCE"
    assert TRAIN_RULE == "HYPERLEX_V5_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN_V1"
    assert EXPERIMENT_ID == (
        "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001"
    )
    assert AUTHORIZED_AUTH_RECEIPT_SHA256.startswith("6341d083")
    assert AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256.startswith("13e8d0ca")
    assert AUTHORIZED_TRAINING_CONFIG_SHA256.startswith("e252f1ba")
    assert EXPECTED_TRAIN_ROWS == 2272
    assert EXPECTED_VALIDATION_ROWS == 848
    assert EXPECTED_OPTIMIZER_STEPS_PER_EPOCH == 284
    assert INITIALIZATION_POLICY["stage_a_best_continuation"] is False
    assert INITIALIZATION_POLICY["base_encoder_source"] == "MODEL_WIDE_BEST"


def test_literal_weights_match_authorization():
    assert abs(LITERAL_RELATION_WEIGHTS["NO_EVIDENCE_RELATION"] - 0.8985774732156429) < 1e-12
    assert abs(LITERAL_RELATION_WEIGHTS["EVIDENCE_RELATION_PRESENT"] - 1.1014225267843571) < 1e-12
    assert abs(LITERAL_RESOLVABILITY_WEIGHTS["RESOLVABLE"] - 0.5) < 1e-12
    assert abs(LITERAL_RESOLVABILITY_WEIGHTS["UNRESOLVABLE"] - 1.7030222347950057) < 1e-12


def test_split_witness_builder_rejects_wrong_dataset(tmp_path):
    rows = [
        {"identity": f"t{i}", "split": "train", "evidence_label": "NO_EVIDENCE"}
        for i in range(EXPECTED_TRAIN_ROWS)
    ] + [
        {"identity": f"v{i}", "split": "validation", "evidence_label": "NO_EVIDENCE"}
        for i in range(EXPECTED_VALIDATION_ROWS)
    ]
    dataset = tmp_path / "EVIDENCE_SURFACE.jsonl"
    # Wrong SHA must fail closed before split hashing.
    try:
        build_v1r2_ident_filtered_split_witness(
            rows,
            dataset_sha256="0" * 64,
            dataset_path=str(dataset),
            code_revision="deadbeef",
        )
        raised = False
    except ValueError as exc:
        raised = True
        assert "dataset_mismatch" in str(exc)
    assert raised
    assert V1R2_DATASET_SHA256_PIN.startswith("492ed367")
