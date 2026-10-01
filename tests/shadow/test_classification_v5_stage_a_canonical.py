"""Tests for HYPERLEX_V5_STAGE_A_CANONICAL_V1 freeze."""

from __future__ import annotations

import pytest

from hyperlexical.classification_v5_stage_a_canonical import (
    CANONICAL_ID,
    STAGE_A_BEST_SHA256,
    STAGE_A_RESEARCH_LOOP,
    V5_STAGE_A_STATE,
    build_canonical_forward,
    decide_canonical_stage_a,
    may_invoke_stage_b,
    stage_a_canonical_contract,
    verify_canonical_checkpoint_keys,
)
from hyperlexical.save_pretrained import assert_factorized_heads_in_flat


def test_canonical_pins():
    assert CANONICAL_ID == "HYPERLEX_V5_STAGE_A_CANONICAL_V1"
    assert STAGE_A_BEST_SHA256.startswith("f2b00c5d")
    assert V5_STAGE_A_STATE == "CANONICAL_FROZEN"
    assert STAGE_A_RESEARCH_LOOP == "CLOSED_FOR_CURRENT_FAILURE_CLASS"
    contract = stage_a_canonical_contract()
    assert contract["relation_threshold"] == 0.60
    assert contract["resolvability_threshold"] == 0.75
    assert contract["model_input"] == ["text"]
    assert contract["auto_relabel"] is False
    assert (
        contract["known_limitations"]["DOMAIN_IRRELEVANT_GENERALIZATION"]
        == "NOT_ESTABLISHED"
    )


def test_decision_and_forward():
    assert decide_canonical_stage_a(p_relation=0.9, p_resolvable=0.5) == "UNCERTAIN"
    assert (
        decide_canonical_stage_a(p_relation=0.9, p_resolvable=0.8) == "EVIDENCE_PRESENT"
    )
    assert decide_canonical_stage_a(p_relation=0.4, p_resolvable=0.8) == "NO_EVIDENCE"
    assert may_invoke_stage_b("EVIDENCE_PRESENT")
    assert not may_invoke_stage_b("NO_EVIDENCE")
    fwd = build_canonical_forward(
        stage_a_decision="EVIDENCE_PRESENT",
        p_relation=0.9,
        p_resolvable=0.8,
    )
    assert fwd["stage_a_decision"] == "EVIDENCE_PRESENT"
    assert fwd["objective_version"].startswith("HYPERLEX_V5_STAGE_A_FACTORIZED")
    assert fwd["legacy_aliases"]["status"] == "DEPRECATED_COMPATIBILITY_ONLY"


def test_serialization_fail_closed():
    keys = [f"encoder.{i}" for i in range(12)] + [
        "relation_head.weight",
        "relation_head.bias",
        "resolvability_head.weight",
        "resolvability_head.bias",
    ]
    assert verify_canonical_checkpoint_keys(keys)["pass"] is True
    assert verify_canonical_checkpoint_keys(keys[:12])["pass"] is False
    with pytest.raises(ValueError):
        assert_factorized_heads_in_flat({"encoder.x": [0.0]})
