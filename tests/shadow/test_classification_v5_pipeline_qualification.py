"""Tests for V5 pipeline qualification contracts (no GPU / no network)."""

from __future__ import annotations

from hyperlexical.classification_v5_pipeline_qualification import (
    DEPENDENCY_MANIFEST_SHA256_PIN,
    GATE_FALSE_ENTRY_MAX,
    QUALIFICATION_ID,
    QUALIFY_RULE,
    build_qualification_receipt,
    disposition_from_results,
    qualification_binding,
    score_qualification_rows,
    verify_package_binding,
)
from hyperlexical.classification_v5_stage_a_canonical import STAGE_A_BEST_SHA256
from hyperlexical.classification_v5_stage_b import FROZEN_INDEX_SHA256


def test_binding_and_gates_frozen():
    assert QUALIFY_RULE.startswith("QUALIFY_HYPERLEX_V5_PIPELINE")
    assert QUALIFICATION_ID.endswith("QUALIFICATION_001")
    bind = qualification_binding()
    assert bind["STAGE_A_BEST"] == STAGE_A_BEST_SHA256
    assert bind["STAGE_B_INDEX"] == FROZEN_INDEX_SHA256
    assert bind["dependency_manifest_sha256"] == DEPENDENCY_MANIFEST_SHA256_PIN
    assert bind["primary_gates"]["false_entry_on_NONE_max"] == GATE_FALSE_ENTRY_MAX
    assert bind["hub_publish_authorized"] is False
    ok = verify_package_binding(bind)
    assert ok["pass"] is True


def test_disposition_and_scoring_helpers():
    pass_disp = disposition_from_results(
        integrity_pass=True,
        metrics={
            "primary_gate_pass": True,
            "gating": {"pass": True},
        },
    )
    assert pass_disp["QUALIFICATION_DISPOSITION"] == "QUALIFICATION_PASS"
    assert pass_disp["RELEASE_ELIGIBLE"] is True
    assert pass_disp["HUB_PUBLISH_AUTHORIZED"] is False
    fail_disp = disposition_from_results(
        integrity_pass=True,
        metrics={"primary_gate_pass": False, "gating": {"pass": True}},
    )
    assert fail_disp["QUALIFICATION_DISPOSITION"] == "QUALIFICATION_FAIL"
    invalid = disposition_from_results(integrity_pass=False, metrics=None)
    assert invalid["QUALIFICATION_DISPOSITION"] == "QUALIFICATION_INVALID"

    rows = [
        {
            "identity": "a",
            "evidence_label": "NO_EVIDENCE",
            "gold_decision_type": "NONE",
            "gold_family": None,
            "is_short_atom": False,
            "evidence_subtype": "ORDINARY_DOMAIN_NONE",
        },
        {
            "identity": "b",
            "evidence_label": "EVIDENCE_PRESENT",
            "gold_decision_type": "FAMILY",
            "gold_family": "memetic",
            "is_short_atom": False,
            "evidence_subtype": "POSITIVE_EVIDENCE",
        },
    ]
    forwards = [
        {
            "stage_a_decision": "NO_EVIDENCE",
            "stage_b_executed": False,
            "final_decision": "NO_EVIDENCE",
            "predicted_family": None,
            "family_score": None,
            "runner_up_family": None,
            "runner_up_score": None,
            "margin": None,
            "p_relation": 0.1,
            "p_resolvable": 0.9,
        },
        {
            "stage_a_decision": "EVIDENCE_PRESENT",
            "stage_b_executed": True,
            "final_decision": "FAMILY",
            "predicted_family": "memetic",
            "family_score": 0.9,
            "runner_up_family": "gaming-meta",
            "runner_up_score": 0.1,
            "margin": 0.8,
            "p_relation": 0.9,
            "p_resolvable": 0.9,
        },
    ]
    metrics = score_qualification_rows(rows, forwards)
    assert metrics["false_evidence_entry_rate_on_none"] == 0.0
    assert metrics["present_recall"] == 1.0
    assert metrics["none_recall"] == 1.0
    assert metrics["family_emission_precision"] == 1.0
    assert metrics["primary_gate_pass"] is True

    receipt = build_qualification_receipt(
        code_revision="deadbeef",
        surface_hashes={"qualification_rows_sha256": "a" * 64},
        composition={"pass": True, "n": 2},
        disjointness={"pass": True},
        identifiability={"pass": True},
        metrics=metrics,
        cold_load={"pass": True},
        integrity_pass=True,
        scored_at="2026-10-01T00:00:00Z",
    )
    assert "QUALIFICATION_RECEIPT_SHA256" in receipt
    assert receipt["RELEASE_ELIGIBLE"] is True
