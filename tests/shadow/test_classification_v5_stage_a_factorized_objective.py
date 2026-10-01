"""Unit pins for SPEC_STAGE_A_FACTORIZED_OBJECTIVE."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_factorized_objective import (  # noqa: E402
    ARCHITECTURE_CHANGE_REQUIRED,
    AUTHORIZED_DATASET_SHA,
    EXPECTED_ROW_COUNT,
    EXPECTED_SUBTYPE_COUNTS,
    FACTORIZED_ANNOTATION_SHA256_PIN,
    FACTORIZED_OBJECTIVE_SPEC,
    MASKED,
    NEXT_ACTION,
    OBJECTIVE_ID,
    OBJECTIVE_RECEIPT_SHA256_PIN,
    POSSIBLE_EVIDENCE_STATUS,
    TRAIN_AUTHORIZED,
    UNKNOWN,
    UnsupportedSubtypeError,
    assemble_objective_receipt,
    build_annotations,
    decide_stage_a,
    derive_factorized_annotation,
    relation_loss_eligible,
    resolvability_loss_eligible,
)


def _row(
    *,
    identity: str,
    label: str,
    subtype: str,
    extra: dict | None = None,
) -> dict:
    payload = {
        "identity": identity,
        "evidence_label": label,
        "evidence_subtype": subtype,
        "required_evidence_present": {
            "EVIDENCE_PRESENT": "true",
            "NO_EVIDENCE": "false",
            "UNCERTAIN": "uncertain",
        }[label],
        "missing_required_semantics": [],
        "provenance": "INFERRED",
    }
    if extra:
        payload.update(extra)
    return payload


def test_objective_pins():
    assert OBJECTIVE_ID == "HYPERLEX_V5_STAGE_A_FACTORIZED_RELATION_OBJECTIVE_V1"
    assert FACTORIZED_OBJECTIVE_SPEC == "FROZEN"
    assert TRAIN_AUTHORIZED is False
    assert ARCHITECTURE_CHANGE_REQUIRED is False
    assert POSSIBLE_EVIDENCE_STATUS == "DEPRECATED_AS_STAGE_A_TRAINING_TARGET"
    assert NEXT_ACTION == "AUTHORIZE_STAGE_A_FACTORIZED_RELATION_TRAIN"
    assert AUTHORIZED_DATASET_SHA.startswith("4095036e")
    assert EXPECTED_ROW_COUNT == 3585
    assert EXPECTED_SUBTYPE_COUNTS["GENERIC_NONE"] == 0


def test_deterministic_derivation_and_masks():
    pos = derive_factorized_annotation(
        _row(
            identity="a" * 64,
            label="EVIDENCE_PRESENT",
            subtype="POSITIVE_EVIDENCE",
        )
    )
    assert pos["evidence_relation_present"] == 1
    assert pos["semantic_resolvable"] == 1
    assert pos["domain_relevant_derived"] == 1
    assert relation_loss_eligible(pos) is True
    assert resolvability_loss_eligible(pos) is True

    none = derive_factorized_annotation(
        _row(
            identity="b" * 64,
            label="NO_EVIDENCE",
            subtype="SHORT_ATOM_NONE",
        )
    )
    assert none["evidence_relation_present"] == 0
    assert none["semantic_resolvable"] == 1
    assert relation_loss_eligible(none) is True

    amb = derive_factorized_annotation(
        _row(
            identity="c" * 64,
            label="UNCERTAIN",
            subtype="AMBIGUOUS_EVIDENCE",
        )
    )
    assert amb["evidence_relation_present"] == MASKED
    assert amb["semantic_resolvable"] == 0
    assert amb["domain_relevant_derived"] == UNKNOWN
    assert relation_loss_eligible(amb) is False
    assert resolvability_loss_eligible(amb) is True


def test_unknown_subtype_fail_closed():
    with pytest.raises(UnsupportedSubtypeError):
        derive_factorized_annotation(
            _row(
                identity="d" * 64,
                label="NO_EVIDENCE",
                subtype="GENERIC_NONE",
            )
        )


def test_no_model_derived_annotation_fields():
    with pytest.raises(ValueError, match="MODEL_DERIVED_FIELD_FORBIDDEN"):
        derive_factorized_annotation(
            _row(
                identity="e" * 64,
                label="EVIDENCE_PRESENT",
                subtype="POSITIVE_EVIDENCE",
                extra={"p_possible": 0.9},
            )
        )


def test_decision_logic():
    assert (
        decide_stage_a(
            p_evidence_relation_present=0.9,
            p_resolvable=0.2,
            relation_threshold=0.5,
            resolvability_threshold=0.5,
        )
        == "UNCERTAIN"
    )
    assert (
        decide_stage_a(
            p_evidence_relation_present=0.9,
            p_resolvable=0.8,
            relation_threshold=0.5,
            resolvability_threshold=0.5,
        )
        == "EVIDENCE_PRESENT"
    )
    assert (
        decide_stage_a(
            p_evidence_relation_present=0.1,
            p_resolvable=0.8,
            relation_threshold=0.5,
            resolvability_threshold=0.5,
        )
        == "NO_EVIDENCE"
    )


def test_identity_preservation_and_counts():
    # Build a miniature surface matching sealed subtype proportions is heavy;
    # instead verify build_annotations integrity gates reject wrong counts.
    rows = []
    # Wrong total → fail.
    with pytest.raises(ValueError, match="ROW_COUNT_MISMATCH"):
        build_annotations(rows, source_dataset_sha256=AUTHORIZED_DATASET_SHA)

    # Correct total but wrong subtypes → fail on subtype pin.
    fake = []
    for i in range(EXPECTED_ROW_COUNT):
        fake.append(
            _row(
                identity=f"{i:064x}",
                label="EVIDENCE_PRESENT",
                subtype="POSITIVE_EVIDENCE",
            )
        )
    with pytest.raises(ValueError, match="SUBTYPE_COUNT_MISMATCH"):
        build_annotations(fake, source_dataset_sha256=AUTHORIZED_DATASET_SHA)


def test_duplicate_identity_rejected():
    rows = [
        _row(
            identity="f" * 64,
            label="EVIDENCE_PRESENT",
            subtype="POSITIVE_EVIDENCE",
        ),
        _row(
            identity="f" * 64,
            label="EVIDENCE_PRESENT",
            subtype="POSITIVE_EVIDENCE",
        ),
    ]
    # Pad to expected count with unique ids of wrong subtype mix — hit dup first.
    # Actually build_annotations checks len first, then dups while iterating.
    # Construct EXPECTED_ROW_COUNT with a duplicate at the end.
    rows = []
    for i in range(EXPECTED_ROW_COUNT - 1):
        # Use subtype mix that will later fail subtype counts if we get there;
        # duplicate should fire first when last row repeats identity 0.
        subtype_cycle = [
            ("EVIDENCE_PRESENT", "POSITIVE_EVIDENCE"),
            ("NO_EVIDENCE", "SHORT_ATOM_NONE"),
            ("UNCERTAIN", "AMBIGUOUS_EVIDENCE"),
        ]
        label, subtype = subtype_cycle[i % 3]
        rows.append(
            _row(identity=f"{i:064x}", label=label, subtype=subtype)
        )
    rows.append(
        _row(
            identity=f"{0:064x}",
            label="EVIDENCE_PRESENT",
            subtype="POSITIVE_EVIDENCE",
        )
    )
    with pytest.raises(ValueError, match="DUPLICATE_IDENTITY"):
        build_annotations(rows, source_dataset_sha256=AUTHORIZED_DATASET_SHA)


def test_receipt_frozen_flags_without_full_surface():
    # Minimal synthetic bundle for receipt assembly shape.
    bundle = {
        "FACTORIZED_ANNOTATION_SHA256": "0" * 64,
        "counts": {
            "n_rows": EXPECTED_ROW_COUNT,
            "relation_positive": 1535,
            "relation_negative": 1851,
            "relation_masked": 199,
            "resolvable_positive": 3386,
            "resolvable_negative": 199,
            "relation_loss_eligible": 3386,
            "resolvability_loss_eligible": 3585,
        },
        "derivation_witness": {"witness_sha256": "1" * 64},
        "manifest": {"manifest_sha256": "2" * 64},
    }
    receipt = assemble_objective_receipt(
        annotation_bundle=bundle, enforce_pins=False
    )
    assert receipt["FACTORIZED_OBJECTIVE_SPEC"] == "FROZEN"
    assert receipt["ANNOTATION_DERIVATION"] == "SEALED"
    assert receipt["TRAIN_AUTHORIZED"] is False
    assert receipt["ARCHITECTURE_CHANGE_REQUIRED"] is False
    assert receipt["NEXT_ACTION"] == "AUTHORIZE_STAGE_A_FACTORIZED_RELATION_TRAIN"
    assert receipt["NEXT_ACTION_AUTHORIZED"] is False
    assert len(receipt["receipt_sha256"]) == 64


def test_sealed_pins():
    assert FACTORIZED_ANNOTATION_SHA256_PIN.startswith("4ac88450")
    assert OBJECTIVE_RECEIPT_SHA256_PIN.startswith("45746d70")
    assert len(FACTORIZED_ANNOTATION_SHA256_PIN) == 64
    assert len(OBJECTIVE_RECEIPT_SHA256_PIN) == 64
