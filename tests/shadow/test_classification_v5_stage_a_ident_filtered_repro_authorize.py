"""Unit pins for AUTHORIZE_REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a import BEST_SHA  # noqa: E402
from hyperlexical.classification_v5_stage_a_gold_identifiability_filter import (  # noqa: E402
    V1R2_ANNOTATION_SHA256_PIN,
    V1R2_DATASET_SHA256_PIN,
    V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
)
from hyperlexical.classification_v5_stage_a_ident_filtered_authorize import (  # noqa: E402
    AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
    AUTHORIZED_TRAINING_CONFIG_SHA256,
    EXPECTED_TRAIN_ROWS,
    EXPECTED_VALIDATION_ROWS,
    LITERAL_RELATION_WEIGHTS,
    LITERAL_RESOLVABILITY_WEIGHTS,
)
from hyperlexical.classification_v5_stage_a_ident_filtered_repro_authorize import (  # noqa: E402
    AUTHORIZE_RULE,
    EXPERIMENT_ID,
    PARENT_EXPERIMENT,
    REPRODUCTION_REASON,
    SERIALIZATION_FIX_COMMIT,
    TRAIN_ONCE_ACTION,
    authorize_reproduction,
    verify_class_weight_identity,
    verify_split_identity,
)
from hyperlexical.classification_v5_stage_a_two_stage_generalization import (  # noqa: E402
    PARENT_STAGE_A_BEST_SHA,
)


WEIGHTS_PATH = (
    ROOT
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001"
    / "IDENT_FILTERED_FACTORIZED_CLASS_WEIGHTS.json"
)


def _weights():
    return json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))


def test_repro_authorize_pins():
    assert AUTHORIZE_RULE == "AUTHORIZE_REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN"
    assert EXPERIMENT_ID == (
        "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-REPRO-001"
    )
    assert PARENT_EXPERIMENT == (
        "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001"
    )
    assert REPRODUCTION_REASON == "SELECTED_FACTORIZED_HEADS_NOT_SERIALIZED"
    assert TRAIN_ONCE_ACTION == "REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN_ONCE"
    assert SERIALIZATION_FIX_COMMIT.startswith("9edf8fc")
    assert V1R2_DATASET_SHA256_PIN.startswith("492ed367")
    assert V1R2_ANNOTATION_SHA256_PIN.startswith("95d54365")
    assert V1R2_EXCLUSION_MANIFEST_SHA256_PIN.startswith("661c9edb")
    assert AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256.startswith("13e8d0ca")
    assert AUTHORIZED_TRAINING_CONFIG_SHA256.startswith("e252f1ba")
    assert BEST_SHA.startswith("9fba0f66")
    assert PARENT_STAGE_A_BEST_SHA.startswith("cd2829c1")


def test_class_weight_identity_reuses_sealed_literals():
    report = verify_class_weight_identity(_weights())
    assert report["pass"] is True
    assert report["recomputed"] is False
    assert report["CLASS_WEIGHT_ARTIFACT_SHA256"].startswith("13e8d0ca")
    assert report["relation"] == LITERAL_RELATION_WEIGHTS
    assert report["resolvability"] == LITERAL_RESOLVABILITY_WEIGHTS


def test_class_weight_mismatch_fails():
    bad = _weights()
    bad["literal_weights"]["relation"]["NO_EVIDENCE_RELATION"] = 0.5
    try:
        verify_class_weight_identity(bad)
        raised = False
    except ValueError as exc:
        raised = True
        assert "REPRODUCTION_CONFIG_MISMATCH" in str(exc)
    assert raised is True


def test_split_identity_pins():
    report = verify_split_identity(
        train_rows=EXPECTED_TRAIN_ROWS,
        validation_rows=EXPECTED_VALIDATION_ROWS,
        train_split_sha256="d0eb1f10329d859bbc51a9774727442f455e9b2dab030b21dcd871d31f396727",
        validation_split_sha256="52f234ce807f1e67fd6b896ecdd45c733cf146bd1dc9b25f98fbd93809a9f8e2",
        train_identity_sha256="69ef5c7813c2666ec21dd770423f8f82caa661edc91841af00e95e3e47f886d7",
        validation_identity_sha256="03add594c4f2e1e96d1c094a3ac9c45775bc02ebf80faa0ed7c840a7da44290c",
        relation_eligible_train_sha256="2ac99867ae66d9c3c0b8e30227df11c5da5dfc4caa190dbc4ae667df78954ad4",
        relation_masked_train_sha256="77b431716025dbf9d944c862003f5f439ac29f1801dcfaa336f587177ddbccbf",
    )
    assert report["pass"] is True
    assert report["TRAIN_ROWS"] == 2272
    assert report["VALIDATION_ROWS"] == 848


def test_authorize_reproduction_bundle():
    bundle = authorize_reproduction(
        class_weight_artifact=_weights(),
        code_revision="testrev",
    )
    auth = bundle["authorization"]
    assert auth["TRAIN_AUTHORIZED"] is True
    assert auth["TRAINING_STATUS"] == "AUTHORIZED_NOT_STARTED"
    assert auth["SCIENTIFIC_RESULT"] == "NOT_COMPUTABLE"
    assert auth["TRAINING_RUN_LIMIT"] == 1
    assert auth["NEXT_ACTION"] == TRAIN_ONCE_ACTION
    assert auth["EXPERIMENT_ID"] == EXPERIMENT_ID
    assert auth["PARENT_EXPERIMENT"] == PARENT_EXPERIMENT
    assert auth["REPRODUCTION_REASON"] == REPRODUCTION_REASON
    assert auth["SCIENTIFIC_CONFIG_PARITY"] == "PASS"
    assert auth["MODEL_WIDE_BEST_MUTATED"] is False
    assert auth["CURRENT_STAGE_A_BEST_MUTATED"] is False
    assert auth["V1R2_MUTATED"] is False
    assert auth["STAGE_B_MUTATED"] is False
    assert auth["spent_reserve_access_for_train_val_select_threshold_diag"] is False
    assert auth["save_policy"]["require_factorized_heads_in_flat"] is True
    assert bundle["serialization_regression_tests"]["pass"] is True
    assert bundle["rng_contract"]["pass"] is True
    assert bundle["scientific_parity"]["pass"] is True
    assert bundle["training_config"]["seed"] == 42
    assert bundle["training_config"]["lambda_resolvability"] == 1.0
    assert bundle["training_config"]["require_factorized_heads_in_flat"] is True
    assert bundle["training_config"]["original_training_config_sha256"] == (
        AUTHORIZED_TRAINING_CONFIG_SHA256
    )
    assert auth["threshold_grids"]["n_pairs"] == 100
    assert auth["threshold_grids"]["do_not_force_original_winning_pair"] is True
    assert auth["SHORT_ATOM_POSITIVE_GENERALIZATION"] == "LOW_SUPPORT"
    assert auth["DOMAIN_IRRELEVANT_GENERALIZATION"] == "NOT_ESTABLISHED"
    assert auth["receipt_sha256"]
