"""Mixed remediation plan tests. No training, no reserve, no ontology mutation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v2_mixed_remediation import (  # noqa: E402
    ACTIVE_FAMILY_VOCABULARY,  # snapshot matching mixed_remediation module internal state
    AUDIT_ARTIFACT_SHA,
    AUDIT_DECISION,
    BEST_SHA,
    REMEDIATION_RULE,
    TARGET_TRAIN_DEFINITIONS,
    assemble_remediation,
    data_expansion_plan,
    next_engineering_action,
    ontology_refactor_candidates,
    remediation_contract,
)
from hyperlexical.classification_v2_separability_audit import (  # noqa: E402
    AUDIT_SCHEMA,
    COLLAPSE_CLUSTER,
    SPARSE_FOCUS,
)


def _audit_stub() -> dict:
    support = {
        family: {
            "inferred": 0,
            "n": 1 if family in SPARSE_FOCUS else 6,
            "n_val_definitions": 58 if family == "internet-slang" else 2,
            "observed": 1 if family in SPARSE_FOCUS else 6,
        }
        for family in ACTIVE_FAMILY_VOCABULARY
    }
    family_status = {family: "OVERLAPPING" for family in ACTIVE_FAMILY_VOCABULARY}
    for family in SPARSE_FOCUS:
        family_status[family] = "UNDER_SUPPORTED"
    family_status["gaming-meta"] = "UNRESOLVED"
    family_status["relationship-dating"] = "NOISY"
    pair_rows = []
    collapse = list(COLLAPSE_CLUSTER)
    for index, left in enumerate(collapse):
        for right in collapse[index + 1 :]:
            pair_rows.append(
                {
                    "family_a": left,
                    "family_b": right,
                    "flags": ["ONTOLOGY_OVERLAP", "REPRESENTATION_COLLAPSE"],
                    "embedding": {"cross_family_similarity": 0.7},
                    "probe": {"f1": 0.33, "status": "OK"},
                    "lexical": {"shared_token_ratio": 0.1},
                }
            )
    return {
        "schema": AUDIT_SCHEMA,
        "decision": AUDIT_DECISION,
        "artifact_sha256": AUDIT_ARTIFACT_SHA,
        "best_sha256": BEST_SHA,
        "train": False,
        "reserve_scored": False,
        "moves_best": False,
        "family_status": family_status,
        "support": support,
        "sparse_treatment": [
            {
                "family": family,
                "additional_data_plausibly_resolves": True,
                "ontology_failure_from_support_alone": False,
            }
            for family in SPARSE_FOCUS
        ],
        "suspected_label_noise": [
            {
                "family": "relationship-dating",
                "identity": "abc",
                "nearest_family": "approval-disapproval",
                "score": 0.9,
                "text": "example",
            }
        ],
        "boundary_evidence": [
            {
                "family": family,
                "nearest_competing_families": ["approval-disapproval"],
                "positive_semantic_cues": ["cue"],
                "exclusion_cues": ["exclude"],
                "shared_overlapping_cues": {},
            }
            for family in ACTIVE_FAMILY_VOCABULARY
        ],
        "pair_rows": pair_rows,
    }


def test_remediation_contract_is_non_mutating():
    contract = remediation_contract()
    assert contract["rule"] == REMEDIATION_RULE
    assert contract["train"] is False
    assert contract["mutates_ontology"] is False
    assert contract["reserve_scored"] is False
    assert contract["moves_best"] is False
    assert contract["encoder_updated"] is False
    assert contract["audit_artifact_sha256"] == AUDIT_ARTIFACT_SHA
    assert contract["target_train_definitions"] == TARGET_TRAIN_DEFINITIONS == 12


def test_data_expansion_prioritizes_sparse_focus_and_blocks_auto_promote():
    plans = data_expansion_plan(_audit_stub())
    by_family = {row["family"]: row for row in plans}
    for family in SPARSE_FOCUS:
        assert family in by_family
        assert by_family[family]["priority"] == 0
        assert by_family[family]["train_needed"] >= TARGET_TRAIN_DEFINITIONS - 2
        assert by_family[family]["val_definitions_are_not_auto_promoted"] is True
    assert by_family["internet-slang"]["n_val_definitions"] == 58


def test_ontology_candidates_do_not_mutate_and_find_collapse_component():
    candidates = ontology_refactor_candidates(_audit_stub())
    assert candidates
    large = max(candidates, key=lambda row: int(row.get("component_size") or 1))
    assert large["action"] == "REVIEW_MERGE_OR_SPLIT"
    assert large["apply_to_active_ontology"] is False
    assert large["component_size"] >= 10


def test_assemble_remediation_seals_training_gate_and_next_action():
    artifact = assemble_remediation(_audit_stub())
    assert artifact["remediation_state"] == "SEALED"
    assert artifact["training_gate"]["allow_encoder_training"] is False
    assert artifact["training_gate"]["allow_reserve_scoring"] is False
    assert artifact["mutates_ontology"] is False
    assert artifact["phases"][0]["phase"] == "PHASE_A_DATA_AND_NOISE"
    assert artifact["phases"][0]["blocks_training"] is True
    action = next_engineering_action(artifact)
    assert "PHASE_A_DATA_AND_NOISE" in action
    assert "internet-slang" in action
    assert "Do not train" in action
    assert len(artifact["artifact_sha256"]) == 64
