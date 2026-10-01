"""Unit pins for Stage-A gold identifiability contract V1."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_gold_identifiability_contract import (  # noqa: E402
    CONTRACT_ID,
    CONTRACT_RULE,
    CONTRACT_STATE,
    DIAGNOSIS_RECEIPT_SHA256,
    MODEL_INPUT,
    TRAIN_AUTHORIZED,
    assemble_contract_receipt,
    classify_row,
    decide_primary_repair,
    identifiability_state,
    short_atom_disposition,
    uncertain_failure_type,
)


def test_contract_pins():
    assert CONTRACT_ID == "HYPERLEX_STAGE_A_GOLD_IDENTIFIABILITY_CONTRACT_V1"
    assert CONTRACT_RULE == "REVISE_GOLD_IDENTIFIABILITY_CONTRACT"
    assert CONTRACT_STATE == "FROZEN_SPEC"
    assert TRAIN_AUTHORIZED is False
    assert MODEL_INPUT == ("text",)
    assert DIAGNOSIS_RECEIPT_SHA256.startswith("827c0e2b")


def test_short_atom_present_context_dependent():
    row = {
        "identity": "x",
        "evidence_label": "EVIDENCE_PRESENT",
        "evidence_subtype": "POSITIVE_EVIDENCE",
        "primary_cell": "SHORT_ATOM/EVIDENCE_PRESENT",
        "text": "crown",
        "notes": "v5_gen_wikt_atom_present:gaming-meta",
        "missing_required_semantics": [],
        "required_evidence_present": "true",
        "pair_group_id": "pg1",
    }
    assert short_atom_disposition(row) == "CONTEXT_DEPENDENT_RELATION"
    info = identifiability_state(row)
    assert info["identifiability_state"] == "INVALID_GOLD_FOR_TEXT_ONLY_MODEL"
    classified = classify_row(row, {"evidence_relation_present": 1, "semantic_resolvable": 1})
    assert classified["admissible_for_relation_training"] is False
    assert classified["admissible_for_end_to_end_eval"] is False
    assert classified["recommended_disposition"] == "EXCLUDE_FROM_TEXT_ONLY_STAGE_A"


def test_lexeme_only_none_text_identifiable():
    row = {
        "identity": "y",
        "evidence_label": "NO_EVIDENCE",
        "evidence_subtype": "SHORT_ATOM_NONE",
        "primary_cell": "SHORT_ATOM/NO_EVIDENCE",
        "text": "precipitation",
        "notes": "v5_gen_wikt_atom_none",
        "missing_required_semantics": ["active_family_evidence_absent"],
        "required_evidence_present": "false",
        "pair_group_id": "pg2",
    }
    assert short_atom_disposition(row) == "LEXEME_ONLY"
    info = identifiability_state(row)
    assert info["identifiability_state"] == "TEXT_IDENTIFIABLE"
    classified = classify_row(row, {"evidence_relation_present": 0, "semantic_resolvable": 1})
    assert classified["admissible_for_relation_training"] is True
    assert classified["recommended_disposition"] == "KEEP_GOLD"


def test_prose_present_self_contained():
    row = {
        "identity": "z",
        "evidence_label": "EVIDENCE_PRESENT",
        "evidence_subtype": "POSITIVE_EVIDENCE",
        "primary_cell": "PROSE/EVIDENCE_PRESENT",
        "text": "The crew started to vibe code the prototype overnight.",
        "notes": "v5_src_hub",
        "missing_required_semantics": [],
        "required_evidence_present": "true",
    }
    assert short_atom_disposition(row) == "SELF_CONTAINED_RELATION"
    assert identifiability_state(row)["identifiability_state"] == "TEXT_IDENTIFIABLE"


def test_uncertain_failure_types():
    multi = {
        "identity": "u1",
        "evidence_label": "UNCERTAIN",
        "evidence_subtype": "AMBIGUOUS_EVIDENCE",
        "notes": "v5_uncertain:MULTI_SENSE",
        "missing_required_semantics": ["evidence_sufficiency_unresolved"],
        "text": "ambiguous phrase with multiple readings here",
        "primary_cell": None,
        "required_evidence_present": "uncertain",
    }
    assert uncertain_failure_type(multi) == "GENUINE_TEXTUAL_UNCERTAINTY"
    ctx = {
        **multi,
        "notes": "v5_uncertain_wiki:UNRESOLVED_SOURCE_MEANING:memetic",
    }
    assert uncertain_failure_type(ctx) == "MISSING_ANNOTATION_CONTEXT"
    c = classify_row(ctx, {"evidence_relation_present": "MASKED", "semantic_resolvable": 0})
    assert c["recommended_disposition"] == "EXCLUDE_FROM_TEXT_ONLY_STAGE_A"
    c2 = classify_row(multi, {"evidence_relation_present": "MASKED", "semantic_resolvable": 0})
    assert c2["recommended_disposition"] == "KEEP_FOR_RESOLVABILITY_ONLY"


def test_no_auto_relabel_and_decision():
    aggregate = {
        "identifiability_counts": {"INVALID_GOLD_FOR_TEXT_ONLY_MODEL": 300},
        "disposition_counts": {
            "EXCLUDE_FROM_TEXT_ONLY_STAGE_A": 400,
            "REQUIRES_HUMAN_RESETTLEMENT": 0,
            "KEEP_GOLD_BUT_MASK_RELATION": 10,
            "KEEP_GOLD": 3000,
        },
        "repaired_surface_viability": "REPAIRED_SURFACE_VIABLE",
        "NEW_DATASET_VERSION_REQUIRED": True,
    }
    decision = decide_primary_repair(aggregate)
    assert decision["primary_repair"] == "FILTER_CONTEXT_DEPENDENT_GOLD"
    assert decision["NEXT_ACTION_AUTHORIZED"] is False
    receipt = assemble_contract_receipt(row_classifications=[], aggregate=aggregate)
    assert receipt["TRAIN_AUTHORIZED"] is False
    assert receipt["DATASET_MUTATED"] is False
    assert receipt["STAGE_A_BEST_MUTATED"] is False
    assert receipt["MODEL_WIDE_BEST_MUTATED"] is False
    assert receipt["AUTO_RELABEL"] is False
    assert len(receipt["receipt_sha256"]) == 64
