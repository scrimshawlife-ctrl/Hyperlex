"""Classification v3 evidence-gate invariant tests. No train / reserve / BEST."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v3_evidence_gate import (  # noqa: E402
    CURRENT_STATE,
    FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
    RULE,
    V2_SETTLEMENT,
    compose_decision,
    decide_evidence,
    evidence_gate_contract,
    may_invoke_retrieval,
    refuse_spent_reserve_identity,
    require_retrieval_allowed,
    subtype_label,
    validate_end_to_end_invariants,
    validate_example_label_pair,
    validate_probability_vector,
    EvidenceGateContractError,
)

SCHEMA_DIR = ROOT / "specs/007-hyperlexical-model/schemas/classification-v3"


def _load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def test_contract_seals_v2_fail_and_preregisters_gate():
    contract = evidence_gate_contract()
    assert contract["rule"] == RULE
    assert contract["current_state"] == CURRENT_STATE == "RUNNING"
    assert contract["train"] is False
    assert contract["spent_v2_reserve_reuse"] is False
    assert contract["false_evidence_entry_rate_on_none_max"] == FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX == 0.05
    assert V2_SETTLEMENT["HYPERLEX_CLASSIFICATION_V2"] == "RESERVE_FAILED"
    assert V2_SETTLEMENT["primary_failure"] == "APPLICABILITY_GENERALIZATION_FAILURE"
    assert V2_SETTLEMENT["production_promotion"] == "REJECTED"


def test_subtype_label_mapping_and_thresholds():
    assert subtype_label("POSITIVE_EVIDENCE") == "EVIDENCE_PRESENT"
    assert subtype_label("HARD_NONE") == "NO_EVIDENCE"
    assert subtype_label("AMBIGUOUS_EVIDENCE") == "UNCERTAIN"
    validate_example_label_pair("NO_EVIDENCE", "GENERIC_NONE")
    with pytest.raises(EvidenceGateContractError):
        validate_example_label_pair("EVIDENCE_PRESENT", "HARD_NONE")
    assert decide_evidence(0.9, none_threshold=0.2, present_threshold=0.8) == "EVIDENCE_PRESENT"
    assert decide_evidence(0.1, none_threshold=0.2, present_threshold=0.8) == "NO_EVIDENCE"
    assert decide_evidence(0.5, none_threshold=0.2, present_threshold=0.8) == "UNCERTAIN"
    with pytest.raises(EvidenceGateContractError):
        decide_evidence(0.5, none_threshold=0.8, present_threshold=0.2)


def test_retrieval_only_on_evidence_present():
    assert may_invoke_retrieval("EVIDENCE_PRESENT") is True
    assert may_invoke_retrieval("NO_EVIDENCE") is False
    assert may_invoke_retrieval("UNCERTAIN") is False
    require_retrieval_allowed("EVIDENCE_PRESENT")
    with pytest.raises(EvidenceGateContractError):
        require_retrieval_allowed("UNCERTAIN")
    with pytest.raises(EvidenceGateContractError):
        require_retrieval_allowed("NO_EVIDENCE")


def test_compose_and_end_to_end_invariants():
    none = compose_decision(evidence_decision="NO_EVIDENCE")
    assert none["decision_type"] == "NONE"
    validate_end_to_end_invariants(none, "NO_EVIDENCE")
    abstain = compose_decision(evidence_decision="UNCERTAIN")
    assert abstain["decision_type"] == "ABSTAIN"
    validate_end_to_end_invariants(abstain, "UNCERTAIN")
    family = compose_decision(
        evidence_decision="EVIDENCE_PRESENT",
        candidates=[
            {"family": "ai-native", "score": 0.9},
            {"family": "gaming-meta", "score": 0.1},
        ],
        family_score_min=0.5,
        family_margin_min=0.05,
    )
    assert family["decision_type"] == "FAMILY"
    validate_end_to_end_invariants(family, "EVIDENCE_PRESENT")
    ambiguous = compose_decision(
        evidence_decision="EVIDENCE_PRESENT",
        candidates=[
            {"family": "ai-native", "score": 0.9},
            {"family": "gaming-meta", "score": 0.88},
        ],
        family_score_min=0.5,
        family_margin_min=0.05,
    )
    assert ambiguous["decision_type"] == "AMBIGUOUS"
    validate_end_to_end_invariants(ambiguous, "EVIDENCE_PRESENT")
    with pytest.raises(EvidenceGateContractError):
        validate_end_to_end_invariants({"decision_type": "FAMILY", "family": "x"}, "UNCERTAIN")


def test_probabilities_and_spent_reserve_exclusion():
    validate_probability_vector(
        {"NO_EVIDENCE": 0.2, "EVIDENCE_PRESENT": 0.5, "UNCERTAIN": 0.3}
    )
    with pytest.raises(EvidenceGateContractError):
        validate_probability_vector(
            {"NO_EVIDENCE": 0.2, "EVIDENCE_PRESENT": 0.5, "UNCERTAIN": 0.4}
        )
    refuse_spent_reserve_identity("fresh", ["spent-a"])
    with pytest.raises(EvidenceGateContractError):
        refuse_spent_reserve_identity("spent-a", ["spent-a"])


def test_json_schemas_accept_minimal_valid_objects():
    example_schema = _load("evidence_example.v1.schema.json")
    decision_schema = _load("evidence_decision.v1.schema.json")
    candidates_schema = _load("family_candidates.v1.schema.json")
    digest = "a" * 64
    example = {
        "identity": digest,
        "text": "alpha beta",
        "evidence_label": "NO_EVIDENCE",
        "evidence_subtype": "HARD_NONE",
        "provenance": "OBSERVED",
        "split": "train",
        "source_sha256": digest,
    }
    jsonschema.validate(example, example_schema)
    evidence = {
        "schema_version": "hyperlex.classification.v3.evidence_decision.v1",
        "input_sha256": digest,
        "decision": "EVIDENCE_PRESENT",
        "probabilities": {
            "NO_EVIDENCE": 0.1,
            "EVIDENCE_PRESENT": 0.8,
            "UNCERTAIN": 0.1,
        },
        "evidence_score": 0.8,
        "decision_thresholds": {"present_threshold": 0.7, "none_threshold": 0.2},
        "model": {"checkpoint_sha256": digest, "config_sha256": digest},
    }
    jsonschema.validate(evidence, decision_schema)
    candidates = {
        "input_sha256": digest,
        "evidence_decision": "EVIDENCE_PRESENT",
        "candidates": [
            {"rank": 1, "family": "ai-native", "score": 0.9, "support_count": 3}
        ],
        "retrieval_config_sha256": digest,
    }
    jsonschema.validate(candidates, candidates_schema)
    bad = dict(example)
    bad["evidence_label"] = "EVIDENCE_PRESENT"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, example_schema)
