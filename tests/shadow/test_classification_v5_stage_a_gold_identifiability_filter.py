"""Unit pins for APPLY_GOLD_IDENTIFIABILITY_FILTER / V1R2 membership filter."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_factorized_objective import (  # noqa: E402
    derive_factorized_annotation,
)
from hyperlexical.classification_v5_stage_a_gold_identifiability_filter import (  # noqa: E402
    CONTRACT_RECEIPT_SHA256_PIN,
    DATASET_VERSION,
    EXPECTED_EXCLUDE_N,
    EXPECTED_KEEP_N,
    EXPECTED_V1R1_N,
    FILTER_RULE,
    KEEP_DISPOSITIONS,
    NEXT_ACTION,
    SURFACE_ID,
    TRAIN_AUTHORIZED,
    assemble_filter_receipt,
)


def test_filter_pins():
    assert FILTER_RULE == "APPLY_GOLD_IDENTIFIABILITY_FILTER"
    assert DATASET_VERSION == "V1R2"
    assert SURFACE_ID.endswith("V1R2")
    assert TRAIN_AUTHORIZED is False
    assert CONTRACT_RECEIPT_SHA256_PIN.startswith("4ce0e5fa")
    assert EXPECTED_V1R1_N == 3585
    assert EXPECTED_KEEP_N == 3120
    assert EXPECTED_EXCLUDE_N == 465
    assert NEXT_ACTION == "AUTHORIZE_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN"
    assert "KEEP_GOLD" in KEEP_DISPOSITIONS


def test_assemble_receipt_immutable_flags():
    receipt = assemble_filter_receipt(
        dataset_sha256="a" * 64,
        annotation_sha256="b" * 64,
        exclusion_manifest_sha256="c" * 64,
        filter_result={
            "counts": {
                "parent_v1r1": 3585,
                "kept": 3120,
                "excluded": 465,
                "by_label": {
                    "EVIDENCE_PRESENT": 1215,
                    "NO_EVIDENCE": 1851,
                    "UNCERTAIN": 54,
                },
                "relation_loss_eligible": 3066,
            },
            "balance": {
                "relation_positive": 1215,
                "relation_negative": 1851,
                "resolvability_positive": 3066,
                "resolvability_negative": 54,
                "minimum_cell_support": 54,
            },
            "viability": "REPAIRED_SURFACE_VIABLE",
        },
        artifact_hashes={"EVIDENCE_SURFACE.jsonl": "a" * 64},
    )
    assert receipt["V1R2_CREATED"] is True
    assert receipt["V1R1_MUTATED"] is False
    assert receipt["AUTO_RELABEL"] is False
    assert receipt["TRAIN"] is False
    assert receipt["TRAIN_AUTHORIZED"] is False
    assert receipt["STAGE_A_BEST_MUTATED"] is False
    assert receipt["MODEL_WIDE_BEST_MUTATED"] is False
    assert receipt["NEXT_ACTION_AUTHORIZED"] is False
    assert receipt["PRIMARY_REPAIR_APPLIED"] == "FILTER_CONTEXT_DEPENDENT_GOLD"
    assert len(receipt["receipt_sha256"]) == 64


def test_no_relabel_helpers_keep_gold_fields():
    row = {
        "identity": "abc",
        "evidence_label": "NO_EVIDENCE",
        "evidence_subtype": "SHORT_ATOM_NONE",
        "text": "precipitation",
        "primary_cell": "SHORT_ATOM/NO_EVIDENCE",
        "missing_required_semantics": ["active_family_evidence_absent"],
        "required_evidence_present": "false",
        "notes": "v5_gen_wikt_atom_none",
        "split": "validation",
    }
    ann = derive_factorized_annotation(row)
    assert ann["source_gold_label"] == "NO_EVIDENCE"
    assert ann["evidence_relation_present"] == 0
