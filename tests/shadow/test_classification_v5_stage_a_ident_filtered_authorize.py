"""Unit pins for AUTHORIZE_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_gold_identifiability_filter import (  # noqa: E402
    V1R2_ANNOTATION_SHA256_PIN,
    V1R2_DATASET_SHA256_PIN,
    V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
)
from hyperlexical.classification_v5_stage_a_ident_filtered_authorize import (  # noqa: E402
    AUTHORIZE_RULE,
    EXPECTED_RELATION_ELIGIBLE_TOTAL,
    EXPECTED_RELATION_TRAIN_ELIGIBLE,
    EXPECTED_RELATION_TRAIN_MASKED,
    EXPECTED_TRAIN_ROWS,
    EXPECTED_VALIDATION_ROWS,
    EXPERIMENT_ID,
    INITIALIZATION_POLICY,
    LITERAL_RELATION_WEIGHTS,
    LITERAL_RESOLVABILITY_WEIGHTS,
    SCIENTIFIC_QUESTION,
    SHORT_ATOM_POSITIVE_GENERALIZATION,
    TRAIN_ONCE_ACTION,
    verify_exclusion_integrity,
)


def test_authorize_pins():
    assert AUTHORIZE_RULE == "AUTHORIZE_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN"
    assert EXPERIMENT_ID == (
        "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001"
    )
    assert TRAIN_ONCE_ACTION == "TRAIN_STAGE_A_IDENT_FILTERED_FACTORIZED_ONCE"
    assert V1R2_DATASET_SHA256_PIN.startswith("492ed367")
    assert V1R2_ANNOTATION_SHA256_PIN.startswith("95d54365")
    assert V1R2_EXCLUSION_MANIFEST_SHA256_PIN.startswith("661c9edb")
    assert EXPECTED_TRAIN_ROWS == 2272
    assert EXPECTED_VALIDATION_ROWS == 848
    assert EXPECTED_RELATION_ELIGIBLE_TOTAL == 3066
    assert EXPECTED_RELATION_TRAIN_ELIGIBLE == 2233
    assert EXPECTED_RELATION_TRAIN_MASKED == 39
    assert SHORT_ATOM_POSITIVE_GENERALIZATION == "LOW_SUPPORT"
    assert "identifiable from the model-visible text" in SCIENTIFIC_QUESTION


def test_initialization_and_weights():
    assert INITIALIZATION_POLICY["stage_a_best_continuation"] is False
    assert INITIALIZATION_POLICY["base_encoder_source"] == "MODEL_WIDE_BEST"
    assert "failed_factorized_8a6981c1" in INITIALIZATION_POLICY[
        "forbidden_initializations"
    ]
    assert abs(LITERAL_RELATION_WEIGHTS["NO_EVIDENCE_RELATION"] - 0.8985774732156429) < 1e-12
    assert abs(LITERAL_RELATION_WEIGHTS["EVIDENCE_RELATION_PRESENT"] - 1.1014225267843571) < 1e-12
    assert abs(LITERAL_RESOLVABILITY_WEIGHTS["RESOLVABLE"] - 0.5) < 1e-12
    assert 0.50 <= LITERAL_RESOLVABILITY_WEIGHTS["UNRESOLVABLE"] <= 2.00


def test_exclusion_integrity_helper():
    kept = [f"k{i}" for i in range(3120)]
    excl = [f"e{i}" for i in range(465)]
    report = verify_exclusion_integrity(
        v1r2_identities=kept, exclusion_identities=excl
    )
    assert report["pass"] is True
    assert report["overlap"] == 0
