"""CPU tests for V6 operating-pipeline harden + QUAL-003 prep contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_operating_pipeline_harden import (
    OPERATING_QUALIFICATION_GATES,
    PHASE_RULE,
    QUAL_003_ID,
    WITNESS_REP_SYSTEM_MACRO_F1,
    WITNESS_REP_ZERO_FP,
    build_operating_receipt,
    classify_operating_reproduction,
    decide_operating_readiness,
    operating_pipeline_contract,
    qualification_003_preparation,
)


def test_contract_packages_gate_and_prepares_qual_003():
    c = operating_pipeline_contract()
    assert c["PHASE_RULE"] == PHASE_RULE
    assert "ANY_LABEL_ZERO_LABEL_gate" in c["architecture"]["flow"]
    assert c["architecture"]["encoder"]["mutable"] is False
    prep = c["qualification_003_preparation"]
    assert prep["QUALIFICATION_ID"] == QUAL_003_ID
    assert prep["scoring_authorized"] is False
    assert prep["QUAL_002"]["status"] == "EVALUATION_SPENT"
    assert OPERATING_QUALIFICATION_GATES["zero_label_false_positive_rate_max"] == 0.35
    assert OPERATING_QUALIFICATION_GATES["system_macro_f1_min"] == 0.30
    assert c["MODEL_WIDE_BEST_MUTATED"] is False


def test_witness_reproduction_and_readiness():
    metrics = {
        "system_macro_f1": WITNESS_REP_SYSTEM_MACRO_F1,
        "zero_label_false_positive_rate": WITNESS_REP_ZERO_FP,
        "positive_only_system_macro_f1": 0.4158,
    }
    rep = classify_operating_reproduction(metrics)
    assert rep["reproduction_class"] == "WITNESS_REPRODUCTION"
    d = decide_operating_readiness(
        package_ok=True,
        cold_load_ok=True,
        round_trip_ok=True,
        encoder_immutable=True,
        reproduction_ok=True,
    )
    assert d["HARDENING_STATE"] == "V6_OPERATING_PIPELINE_HARDENED"
    assert d["NEXT_ACTION"] == "BUILD_AND_SEAL_FRESH_V6_QUALIFICATION_SURFACE_003"
    prep = qualification_003_preparation()
    assert prep["status"] == "PREPARED_NOT_SEALED"
    receipt = build_operating_receipt(
        {"PHASE_RULE": PHASE_RULE, "HARDENING_STATE": d["HARDENING_STATE"]}
    )
    assert receipt["V6_OPERATING_PIPELINE_HARDEN_RECEIPT_SHA256"]
    assert receipt["QUAL_003_SCORED"] is False


def test_package_failure_blocks_qual():
    d = decide_operating_readiness(
        package_ok=False,
        cold_load_ok=True,
        round_trip_ok=True,
        encoder_immutable=True,
        reproduction_ok=True,
    )
    assert d["HARDENING_STATE"] == "V6_OPERATING_PIPELINE_HARDEN_FAILED"
    assert d["QUALIFICATION_READINESS"] == "V6_QUALIFICATION_BLOCKED_PACKAGE"
