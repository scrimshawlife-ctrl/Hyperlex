"""Unit pins for V1R1 generalization-retrain Gate-1 diagnosis."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_generalization_retrain_diagnose import (  # noqa: E402
    DIAGNOSE_RULE,
    FAILED_CHECKPOINT_SHA256,
    FROZEN_OBSERVED_OUTCOME,
    classify_gate1_error,
    classify_representation_state,
    decide_next_action,
    decide_primary_diagnosis,
    justified_changes,
    semantic_core_class,
)


def test_diagnose_pins():
    assert DIAGNOSE_RULE == "DIAGNOSE_V5_STAGE_A_GENERALIZATION_RETRAIN_SETTLED_FAIL"
    assert FAILED_CHECKPOINT_SHA256.startswith("26841d5f")
    assert FROZEN_OBSERVED_OUTCOME["SHORT_ATOM_NONE_false_entry"] == 0.546
    assert FROZEN_OBSERVED_OUTCOME["n_threshold_passing"] == 0


def test_gate1_error_codes():
    assert classify_gate1_error(evidence_label="NO_EVIDENCE", p_possible=0.1) == "TRUE_NONE"
    assert (
        classify_gate1_error(evidence_label="NO_EVIDENCE", p_possible=0.9)
        == "FALSE_POSSIBLE"
    )
    assert (
        classify_gate1_error(evidence_label="EVIDENCE_PRESENT", p_possible=0.9)
        == "TRUE_POSSIBLE"
    )
    assert (
        classify_gate1_error(evidence_label="UNCERTAIN", p_possible=0.1) == "FALSE_NONE"
    )


def test_representation_and_semantic_helpers():
    assert (
        classify_representation_state(
            none_present_cosine=0.99,
            mean_none_margin=0.0,
            mean_present_margin=0.0,
        )
        == "SHORT_ATOM_REPRESENTATION_COLLAPSED"
    )
    assert (
        classify_representation_state(
            none_present_cosine=0.80,
            mean_none_margin=0.08,
            mean_present_margin=0.08,
        )
        == "SHORT_ATOM_REPRESENTATION_SEPARABLE"
    )
    row = {
        "evidence_label": "NO_EVIDENCE",
        "evidence_subtype": "SHORT_ATOM_NONE",
        "missing_required_semantics": ["active_family_evidence_absent"],
        "text": "bruh",
        "notes": "v5_gen_wikt_atom_none",
        "required_evidence_present": "false",
    }
    assert semantic_core_class(row) == "LEXEME_ONLY"


def test_primary_diagnosis_semantic_mismatch_path():
    primary = decide_primary_diagnosis(
        {
            "data_coverage_dominant": False,
            "lexical_association": {
                "false_possible_high_assoc_fraction": 0.70,
                "true_none_high_assoc_fraction": 0.40,
            },
            "probe_results": {
                "A_existing_head": {"short_atom_ba": 0.52},
                "B_logistic": {"short_atom_ba": 0.54},
                "C_nonlinear": {"short_atom_ba": 0.55},
            },
            "representation_state": "SHORT_ATOM_REPRESENTATION_PARTIAL",
            "semantic_core": {
                "short_atom_counts": {
                    "LEXEME_ONLY": 140,
                    "LEXEME_PLUS_RELATION": 30,
                    "EXPLICIT_EVIDENCE_CORE": 150,
                }
            },
            "threshold_impossibility": {"class": "STRUCTURAL_CLASS_OVERLAP"},
        }
    )
    assert primary["primary_diagnosis"] == "GATE1_SEMANTIC_TARGET_MISMATCH"
    assert decide_next_action(primary["primary_diagnosis"]) == (
        "STAGE_A_SEMANTIC_DECOMPOSITION"
    )
    justified = justified_changes(primary["primary_diagnosis"])
    assert justified["dataset_change_justified"] is False
    assert justified["semantic_decomposition_justified"] is True
    assert justified["objective_change_justified"] is True
