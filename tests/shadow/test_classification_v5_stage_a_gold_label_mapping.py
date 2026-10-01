"""Tests for HYPERLEX_V5_STAGE_A_GOLD_LABEL_MAPPING_V1."""

from __future__ import annotations

import pytest

from hyperlexical.classification_v5_stage_a_gold_label_mapping import (
    LABEL_MAPPING_INVALID,
    SUBTYPE_TO_GOLD,
    LabelMappingError,
    admission_invariants,
    gold_label,
    mapping_contract,
    validate_row_gold_mapping,
)


def _row(**kwargs):
    base = {
        "identity": "test",
        "evidence_subtype": "POSITIVE_EVIDENCE",
        "evidence_label": "EVIDENCE_PRESENT",
        "required_evidence_present": "true",
        "active_family_support": [{"family_id": "f1"}],
        "positive_evidence_spans": [{"text": "cue"}],
        "candidate_families": [],
        "missing_required_semantics": [],
        "notes": "",
    }
    base.update(kwargs)
    return base


def test_subtype_table_is_total_and_unique():
    assert set(SUBTYPE_TO_GOLD) == {
        "POSITIVE_EVIDENCE",
        "ORDINARY_DOMAIN_NONE",
        "HARD_NONE",
        "NEAR_DOMAIN_NONE",
        "GENERIC_NONE",
        "LEXICAL_LOOKALIKE_NONE",
        "SHORT_ATOM_NONE",
        "AMBIGUOUS_EVIDENCE",
    }
    assert SUBTYPE_TO_GOLD["POSITIVE_EVIDENCE"] == "EVIDENCE_PRESENT"
    assert SUBTYPE_TO_GOLD["AMBIGUOUS_EVIDENCE"] == "UNCERTAIN"
    for subtype, gold in SUBTYPE_TO_GOLD.items():
        if subtype != "POSITIVE_EVIDENCE" and subtype != "AMBIGUOUS_EVIDENCE":
            assert gold == "NO_EVIDENCE"


def test_positive_gold():
    assert gold_label(_row()) == "EVIDENCE_PRESENT"


def test_none_golds():
    for subtype in (
        "ORDINARY_DOMAIN_NONE",
        "HARD_NONE",
        "NEAR_DOMAIN_NONE",
        "GENERIC_NONE",
        "LEXICAL_LOOKALIKE_NONE",
        "SHORT_ATOM_NONE",
    ):
        assert (
            gold_label(
                _row(
                    evidence_subtype=subtype,
                    evidence_label="NO_EVIDENCE",
                    required_evidence_present="false",
                    active_family_support=[],
                    positive_evidence_spans=[],
                )
            )
            == "NO_EVIDENCE"
        )


def test_uncertain_gold():
    assert (
        gold_label(
            _row(
                evidence_subtype="AMBIGUOUS_EVIDENCE",
                evidence_label="UNCERTAIN",
                required_evidence_present="uncertain",
                active_family_support=[],
                positive_evidence_spans=[],
                missing_required_semantics=["INSUFFICIENT_CONTEXT"],
            )
        )
        == "UNCERTAIN"
    )


def test_family_ambiguity_is_present_not_uncertain():
    # Clear evidence + multiple families → Stage-A PRESENT (Stage-C later).
    assert (
        gold_label(
            _row(
                candidate_families=["A", "B"],
                active_family_support=[{"family_id": "A"}, {"family_id": "B"}],
            )
        )
        == "EVIDENCE_PRESENT"
    )


def test_fail_closed_unknown_subtype():
    with pytest.raises(LabelMappingError) as exc:
        gold_label(_row(evidence_subtype="NOT_A_SUBTYPE"))
    assert LABEL_MAPPING_INVALID in str(exc.value)


def test_fail_closed_positive_without_family():
    with pytest.raises(LabelMappingError):
        gold_label(_row(active_family_support=[]))


def test_fail_closed_required_mismatch():
    with pytest.raises(LabelMappingError):
        gold_label(_row(required_evidence_present="false"))


def test_admission_invariants_pass_clean_rows():
    rows = [
        _row(),
        _row(
            identity="n1",
            evidence_subtype="ORDINARY_DOMAIN_NONE",
            evidence_label="NO_EVIDENCE",
            required_evidence_present="false",
            active_family_support=[],
            positive_evidence_spans=[],
        ),
        _row(
            identity="u1",
            evidence_subtype="AMBIGUOUS_EVIDENCE",
            evidence_label="UNCERTAIN",
            required_evidence_present="uncertain",
            active_family_support=[],
            positive_evidence_spans=[],
            notes="MULTIPLE_PLAUSIBLE_INTERPRETATIONS",
        ),
    ]
    report = admission_invariants(rows)
    assert report["pass"] is True
    assert report["n_invalid"] == 0


def test_admission_flags_subtype_gold_mismatch():
    bad = _row(evidence_label="NO_EVIDENCE")
    assert "subtype_gold_mismatch" in validate_row_gold_mapping(bad)


def test_contract_forbids_model_derived_gold():
    contract = mapping_contract()
    assert "model_probability" in contract["FORBIDDEN_GOLD_DERIVATION_SOURCES"]
    assert "threshold_outcome" in contract["FORBIDDEN_GOLD_DERIVATION_SOURCES"]
    assert "Gold UNCERTAIN describes semantic uncertainty" in contract["CRITICAL_INVARIANT"]
