"""Fail-closed contract tests for UNCERTAIN label-surface audit."""

from __future__ import annotations

from hyperlexical.classification_v5_stage_a_uncertain_label_surface_audit import (
    FROZEN_AMBIGUITY_REASONS,
    MISSING_FIELD,
    NO_DATA,
    NOT_COMPUTABLE,
    classify_boundary,
    data_completeness_blocks_clean,
    decide_diagnosis,
    extract_ambiguity_reason,
    metric_with_denominator,
    reason_support_table,
    required_field_bundle,
    valid_probabilities,
)


def test_frozen_reasons_preserved_including_zero_support():
    table = reason_support_table({}, {})
    assert set(table) == set(FROZEN_AMBIGUITY_REASONS)
    for reason, row in table.items():
        assert row["train_support"] == 0
        assert row["validation_support"] == 0
        assert row["reason_state"] == NO_DATA
        assert "UNDER_SUPPORTED_REASON" in row["flags"]


def test_missing_required_fields_fail_closed():
    row = {
        "identity": "x",
        "text": "hello",
        "evidence_subtype": "AMBIGUOUS_EVIDENCE",
        "evidence_label": "UNCERTAIN",
        "required_evidence_present": "uncertain",
        "source_sha256": "abc",
        "split": "validation",
        "source_bucket": "src",
    }
    bundle = required_field_bundle(row, label_provenance=None, source_provenance=None)
    assert bundle["audit_row_state"] == MISSING_FIELD
    assert "ambiguity_reason" in bundle["missing_required_fields"]
    assert "label_authority" in bundle["missing_required_fields"]


def test_ambiguity_reason_from_provenance_only():
    row = {"evidence_label": "UNCERTAIN"}
    lp = {
        "evidence_basis": [
            {"ambiguity_reason": "MULTIPLE_PLAUSIBLE_INTERPRETATIONS", "type": "CANONICAL_MAPPING"}
        ]
    }
    reason, state = extract_ambiguity_reason(row, lp)
    assert reason == "MULTIPLE_PLAUSIBLE_INTERPRETATIONS"
    assert state == "OBSERVED_VALUE"


def test_no_inference_of_reason_from_notes():
    row = {"notes": "INSUFFICIENT_CONTEXT somehow", "evidence_label": "UNCERTAIN"}
    reason, state = extract_ambiguity_reason(row, None)
    assert reason is None
    assert state == MISSING_FIELD


def test_invalid_probabilities_not_renormalized():
    probs, state = valid_probabilities(
        {"P_NO_EVIDENCE": 0.5, "P_EVIDENCE_PRESENT": 0.5, "P_UNCERTAIN": 0.5}
    )
    assert probs is None
    assert state == "INVALID_OR_MISSING"


def test_boundary_not_computable_without_embeddings():
    klass, state = classify_boundary(None, 0.9)
    assert klass is None
    assert state == NOT_COMPUTABLE


def test_metric_denominator_preserved():
    m = metric_with_denominator(0.59, n_eligible=61, n_excluded_missing=0)
    assert m["n_eligible"] == 61
    assert m["value"] == 0.59


def test_clean_blocked_by_low_coverage():
    assert data_completeness_blocks_clean(
        uncertain_missing_required_frac=0.0,
        probability_coverage=0.5,
        representation_coverage=1.0,
        ambiguity_reason_coverage=1.0,
    )


def test_under_supported_next_action():
    diag, nxt = decide_diagnosis(
        data_completeness_blocker=False,
        under_supported_reasons=["INSUFFICIENT_CONTEXT"],
        boundary_conflict=False,
        source_skew=False,
        mixed_surface_issues=False,
        clean_enough=False,
    )
    assert diag == "UNCERTAIN_SURFACE_UNDER_SUPPORTED"
    assert nxt == "EXPAND_V5_UNCERTAIN_SURFACE"
