"""Tests for V5 pipeline surface-mismatch diagnosis."""

from __future__ import annotations

from hyperlexical.classification_v5_pipeline_diagnose import (
    NEXT_ACTION,
    PRIMARY_DIAGNOSIS,
    diagnose_pipeline_eval,
    seal_diagnosis_receipt,
)


def test_diagnose_surface_mismatch():
    eval_receipt = {
        "PIPELINE_EVAL_PASS": False,
        "PIPELINE_EVAL_RECEIPT_SHA256": "abc",
        "evaluation": {
            "gating": {"pass": True},
            "metrics": {
                "false_evidence_entry_rate_on_none": 0.19488817891373802,
                "primary_gate_pass": False,
                "family_emission_precision": 0.76,
            },
        },
    }
    diag = diagnose_pipeline_eval(eval_receipt)
    assert diag["PRIMARY_DIAGNOSIS"] == PRIMARY_DIAGNOSIS
    assert diag["findings"]["surface_mismatch"] is True
    assert diag["findings"]["index_encoder_parent_mismatch"] is True
    assert diag["findings"]["entry_gating_intact"] is True
    assert diag["NEXT_ACTION"] == NEXT_ACTION
    sealed = seal_diagnosis_receipt(diag)
    assert "PIPELINE_DIAGNOSIS_RECEIPT_SHA256" in sealed
