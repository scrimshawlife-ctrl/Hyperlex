"""Unit pins for REPAIR_IDENT_FILTERED_FACTORIZED_CHECKPOINT_SERIALIZATION."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_ident_filtered_checkpoint_repair import (  # noqa: E402
    INCOMPLETE_CHECKPOINT_PROMOTABILITY,
    INCOMPLETE_CHECKPOINT_STATUS,
    INCOMPLETE_SELECTED_CHECKPOINT_SHA256,
    NEXT_ACTION_ON_FAIL,
    NEXT_ACTION_ON_PASS,
    REPAIR_RULE,
    SELECTED_EPOCH,
    audit_candidate_sources,
    build_repair_receipt,
    classify_tensor_keys,
    serialization_regression_report,
    verify_selected_epoch_identity,
)
from hyperlexical.classification_v5_stage_a_gold_identifiability_filter import (  # noqa: E402
    V1R2_DATASET_SHA256_PIN,
)
from hyperlexical.classification_v5_stage_a_ident_filtered_authorize import (  # noqa: E402
    AUTHORIZED_AUTH_RECEIPT_SHA256,
    AUTHORIZED_TRAINING_CONFIG_SHA256,
    EXPERIMENT_ID,
)
from hyperlexical.classification_v5_stage_a_ident_filtered_promote import (  # noqa: E402
    PREVIOUS_STAGE_A_BEST_SHA256,
)
from hyperlexical.classification_v5_stage_a import BEST_SHA  # noqa: E402
from hyperlexical.layout import HIDDEN  # noqa: E402
from hyperlexical.save_pretrained import (  # noqa: E402
    FACTORIZED_HEAD_NAMES,
    assert_factorized_heads_in_flat,
    flatten_weight_tensors,
    require_factorized_heads_in_flat,
    split_weight_tensors,
)


def _complete_state():
    return {
        "encoder": {
            "encoder.layers.20.weight": [[0.0] * 4],
            "encoder.layers.21.weight": [[1.0] * 4],
        },
        "relation_head": {
            "weight": [[0.1] * HIDDEN, [0.2] * HIDDEN],
            "bias": [0.3, 0.4],
        },
        "resolvability_head": {
            "weight": [[0.5] * HIDDEN, [0.6] * HIDDEN],
            "bias": [0.7, 0.8],
        },
    }


def test_repair_constants():
    assert REPAIR_RULE == "REPAIR_IDENT_FILTERED_FACTORIZED_CHECKPOINT_SERIALIZATION"
    assert SELECTED_EPOCH == 11
    assert INCOMPLETE_SELECTED_CHECKPOINT_SHA256.startswith("8b2de447")
    assert PREVIOUS_STAGE_A_BEST_SHA256.startswith("cd2829c1")
    assert BEST_SHA.startswith("9fba0f66")
    assert INCOMPLETE_CHECKPOINT_STATUS == "SCIENTIFIC_SELECTED_STATE_REFERENCE"
    assert (
        INCOMPLETE_CHECKPOINT_PROMOTABILITY == "NON_PROMOTABLE_PACKAGING_ARTIFACT"
    )
    assert NEXT_ACTION_ON_FAIL == (
        "AUTHORIZE_REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN"
    )
    assert NEXT_ACTION_ON_PASS == (
        "RETRY_PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE"
    )
    assert FACTORIZED_HEAD_NAMES == ("relation_head", "resolvability_head")


def test_factorized_heads_survive_flatten_weight_tensors():
    flat = flatten_weight_tensors(_complete_state())
    assert "relation_head.weight" in flat
    assert "relation_head.bias" in flat
    assert "resolvability_head.weight" in flat
    assert "resolvability_head.bias" in flat
    report = require_factorized_heads_in_flat(flat)
    assert report["pass"] is True
    split = split_weight_tensors(flat)
    assert split["relation_head"]["bias"] == [0.3, 0.4]
    assert split["resolvability_head"]["bias"] == [0.7, 0.8]


def test_factorized_checkpoint_contains_both_heads():
    flat = flatten_weight_tensors(_complete_state())
    classified = classify_tensor_keys(list(flat.keys()))
    assert classified["has_all_required_heads"] is True
    assert classified["architecture"]["pass"] is True


def test_missing_relation_head_fails_load():
    state = _complete_state()
    del state["relation_head"]
    flat = flatten_weight_tensors(state)
    report = require_factorized_heads_in_flat(flat)
    assert report["pass"] is False
    assert "relation_head.weight" in report["missing"]
    try:
        assert_factorized_heads_in_flat(flat)
        raised = False
    except ValueError as exc:
        raised = True
        assert "relation_head" in str(exc)
    assert raised is True


def test_missing_resolvability_head_fails_load():
    state = _complete_state()
    del state["resolvability_head"]
    flat = flatten_weight_tensors(state)
    report = require_factorized_heads_in_flat(flat)
    assert report["pass"] is False
    assert "resolvability_head.bias" in report["missing"]


def test_wrong_head_shape_fails_load():
    state = _complete_state()
    state["relation_head"]["weight"] = [[0.1, 0.2], [0.3, 0.4]]  # not (2, HIDDEN)
    flat = flatten_weight_tensors(state)
    report = require_factorized_heads_in_flat(flat)
    assert report["pass"] is False
    assert report["shape_errors"]
    assert report["shape_errors"][0]["tensor"] == "relation_head.weight"


def test_cold_load_requires_no_trainer_memory_state():
    # Historical encoder-only selected checkpoint remains rejected without
    # residual trainer memory.
    historical_keys = [f"encoder.layers.{i}.weight" for i in range(12)]
    classified = classify_tensor_keys(historical_keys)
    assert classified["has_all_required_heads"] is False
    assert classified["missing_required_heads"] == [
        "relation_head.weight",
        "relation_head.bias",
        "resolvability_head.weight",
        "resolvability_head.bias",
    ]


def test_round_trip_save_load_preserves_logits_proxy():
    # Pure tensor round-trip stand-in: flatten → split preserves head values
    # that determine logits (no trainer memory).
    state = _complete_state()
    flat = flatten_weight_tensors(state)
    split = split_weight_tensors(flat)
    assert split["relation_head"]["weight"] == state["relation_head"]["weight"]
    assert split["relation_head"]["bias"] == state["relation_head"]["bias"]
    assert (
        split["resolvability_head"]["weight"]
        == state["resolvability_head"]["weight"]
    )
    assert (
        split["resolvability_head"]["bias"] == state["resolvability_head"]["bias"]
    )


def test_historical_incomplete_checkpoint_remains_rejected():
    audit = audit_candidate_sources(
        artifacts=[
            {
                "path": "selected/model.safetensors",
                "role": "selected_persisted",
                "epoch": 11,
                "sha256": INCOMPLETE_SELECTED_CHECKPOINT_SHA256,
                "keys": [f"encoder.layers.{i}.weight" for i in range(12)],
            }
        ]
    )
    assert audit["exact_selected_epoch_heads_available"] is False
    assert audit["authoritative_selected_head_source"] is None
    assert len(audit["recoverable_sources"]) == 0


def test_serialization_regression_report_pass():
    report = serialization_regression_report()
    assert report["pass"] is True
    assert report["flatten_preserves_relation_head"] is True
    assert report["flatten_preserves_resolvability_head"] is True
    assert report["require_factorized_heads_fail_on_incomplete"] is True
    assert report["historical_incomplete_rejected"] is True


def test_identity_and_fail_closed_receipt():
    identity = verify_selected_epoch_identity(
        experiment_id=EXPERIMENT_ID,
        selected_epoch=11,
        selected_encoder_sha256=INCOMPLETE_SELECTED_CHECKPOINT_SHA256,
        dataset_sha256=V1R2_DATASET_SHA256_PIN,
        training_config_sha256=AUTHORIZED_TRAINING_CONFIG_SHA256,
        authorization_sha256=AUTHORIZED_AUTH_RECEIPT_SHA256,
    )
    assert identity["pass"] is True
    audit = audit_candidate_sources(
        artifacts=[
            {
                "path": "epoch11",
                "role": "selected",
                "epoch": 11,
                "sha256": INCOMPLETE_SELECTED_CHECKPOINT_SHA256,
                "keys": [f"encoder.layers.{i}.weight" for i in range(12)],
            }
        ]
    )
    receipt = build_repair_receipt(
        source_audit=audit,
        identity=identity,
        serialization_tests=serialization_regression_report(),
        code_revision="testrev",
    )
    assert receipt["CHECKPOINT_REPAIR"] == "FAIL"
    assert receipt["REPAIR_STATUS"] == "REPAIR_NOT_POSSIBLE_WITHOUT_RETRAIN"
    assert receipt["PROMOTION_LOADABLE"] is False
    assert receipt["NEXT_ACTION"] == NEXT_ACTION_ON_FAIL
    assert receipt["SCIENTIFIC_RESULT"] == "SETTLED_PASS"
    assert receipt["SCIENTIFIC_RESULT_SOURCE"] == "original settled run"
    assert receipt["STAGE_A_BEST_MUTATED"] is False
    assert receipt["MODEL_WIDE_BEST_MUTATED"] is False
    assert receipt["STAGE_A_BEST"] == PREVIOUS_STAGE_A_BEST_SHA256
    assert receipt["MODEL_WIDE_BEST"] == BEST_SHA
    assert receipt["historical_incomplete_checkpoint"]["deleted"] is False
    assert receipt["CHECKPOINT_REPAIR_RECEIPT_SHA256"]
