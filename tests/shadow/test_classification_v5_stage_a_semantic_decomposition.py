"""Unit pins for STAGE_A_SEMANTIC_DECOMPOSITION (spec/audit only)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_semantic_decomposition import (  # noqa: E402
    CRITICAL_DISTINCTIONS,
    DECOMPOSITION_RULE,
    DIAGNOSIS_RECEIPT_SHA256,
    FROZEN_V1R1_SUBTYPE_COUNTS,
    PRIMARY_DIAGNOSIS,
    assemble_decomposition_receipt,
    audit_rows,
    backward_map_final_label,
    candidate_objectives,
    decide_primary,
    derive_primitives,
    frozen_v1r1_audit,
    next_action_for,
    relation_taxonomy_recommendation,
    semantic_sufficiency_matrix,
    supervision_requirement,
)


def test_decomposition_pins():
    assert DECOMPOSITION_RULE == "STAGE_A_SEMANTIC_DECOMPOSITION"
    assert PRIMARY_DIAGNOSIS == "GATE1_SEMANTIC_TARGET_MISMATCH"
    assert DIAGNOSIS_RECEIPT_SHA256.startswith("c6ae58c7")
    assert CRITICAL_DISTINCTIONS["DOMAIN_RELEVANT_NE_EVIDENCE_PRESENT"] is True
    assert CRITICAL_DISTINCTIONS["LEXICAL_CUE_NE_EVIDENCE_RELATION"] is True
    assert CRITICAL_DISTINCTIONS["MODEL_UNCERTAINTY_NE_SEMANTIC_UNCERTAINTY"] is True
    assert FROZEN_V1R1_SUBTYPE_COUNTS["GENERIC_NONE"] == 0
    assert FROZEN_V1R1_SUBTYPE_COUNTS["SHORT_ATOM_NONE"] == 284


def test_backward_mapping_nonunique_none_and_uncertain():
    present = backward_map_final_label("EVIDENCE_PRESENT")
    assert present["unique"] is True
    assert present["implies"]["evidence_relation_present"] == 1
    none = backward_map_final_label("NO_EVIDENCE")
    assert none["unique"] is False
    uncertain = backward_map_final_label("UNCERTAIN")
    assert uncertain["unique"] is False
    assert uncertain["implies"]["semantic_resolvable"] == 0


def test_derive_primitives_short_atom_none():
    row = {
        "evidence_label": "NO_EVIDENCE",
        "evidence_subtype": "SHORT_ATOM_NONE",
        "required_evidence_present": "false",
        "missing_required_semantics": [
            "active_family_evidence_absent",
            "subtype:SHORT_ATOM_NONE",
        ],
        "notes": "v5_gen_wikt_atom_none",
    }
    derived = derive_primitives(row)
    assert derived["domain_relevant"] == {"status": "RULE_DERIVABLE", "value": 1}
    assert derived["evidence_relation_present"] == {
        "status": "RULE_DERIVABLE",
        "value": 0,
    }
    assert derived["semantic_resolvable"] == {"status": "RULE_DERIVABLE", "value": 1}


def test_derive_primitives_positive_and_ambiguous():
    pos = derive_primitives(
        {
            "evidence_label": "EVIDENCE_PRESENT",
            "evidence_subtype": "POSITIVE_EVIDENCE",
            "required_evidence_present": "true",
            "missing_required_semantics": [],
        }
    )
    assert pos["evidence_relation_present"]["value"] == 1
    amb = derive_primitives(
        {
            "evidence_label": "UNCERTAIN",
            "evidence_subtype": "AMBIGUOUS_EVIDENCE",
            "required_evidence_present": "uncertain",
            "missing_required_semantics": ["evidence_sufficiency_unresolved"],
            "notes": "v5_uncertain_remediate:INSUFFICIENT_CONTEXT",
        }
    )
    assert amb["semantic_resolvable"]["value"] == 0
    assert amb["domain_relevant"]["status"] == "REQUIRES_NEW_HUMAN_SETTLEMENT"
    assert amb["domain_relevant"]["optional_note_cause"] == "CONTEXT_INSUFFICIENT"


def test_audit_and_primary_relation_only():
    rows = [
        {
            "evidence_label": "EVIDENCE_PRESENT",
            "evidence_subtype": "POSITIVE_EVIDENCE",
            "required_evidence_present": "true",
            "missing_required_semantics": [],
        },
        {
            "evidence_label": "NO_EVIDENCE",
            "evidence_subtype": "SHORT_ATOM_NONE",
            "required_evidence_present": "false",
            "missing_required_semantics": ["active_family_evidence_absent"],
        },
        {
            "evidence_label": "NO_EVIDENCE",
            "evidence_subtype": "ORDINARY_DOMAIN_NONE",
            "required_evidence_present": "false",
            "missing_required_semantics": ["active_family_evidence_absent"],
        },
    ]
    # Prefer flag needs high domain/relation coverage; small synthetic set still
    # exercises derive paths. Decision uses frozen audit for primary seal.
    audit = audit_rows(rows)
    assert audit["n_rows"] == 3
    assert audit["status_counts"]["evidence_relation_present"]["DIRECTLY_SUPPORTED"] == 1
    assert audit["status_counts"]["evidence_relation_present"]["RULE_DERIVABLE"] == 2

    frozen = frozen_v1r1_audit()
    primary = decide_primary(frozen)
    assert primary["primary_decomposition"] == "RELATION_ONLY_DECOMPOSITION"
    assert supervision_requirement(primary["primary_decomposition"], frozen)[
        "requirement"
    ] == "NO_NEW_GOLD_REQUIRED"
    assert next_action_for(primary["primary_decomposition"]) == (
        "SPEC_STAGE_A_FACTORIZED_OBJECTIVE"
    )


def test_objectives_and_sufficiency():
    objs = candidate_objectives()
    assert objs["A_predict_final_class_directly"]["viable"] is False
    assert objs["D_relation_only_with_deterministic_metadata"]["viable"] is True
    matrix = semantic_sufficiency_matrix("RELATION_ONLY_DECOMPOSITION")
    assert matrix["domain_relevant_lexeme_only"]["representable"] is True
    assert matrix["domain_irrelevant_prose"]["representable"] is False
    tax = relation_taxonomy_recommendation()
    assert tax["recommendation"] == "BINARY_EVIDENCE_RELATION_PRESENCE"
    assert tax["full_taxonomy_necessary_now"] is False


def test_sealed_receipt():
    receipt = assemble_decomposition_receipt()
    assert receipt["DECOMPOSITION_STATE"] == "SEALED"
    assert receipt["PRIMARY_DECOMPOSITION"] == "RELATION_ONLY_DECOMPOSITION"
    assert receipt["dataset_consequence"] == "ANNOTATION_ONLY_CHANGE"
    assert receipt["minimum_new_gold_requirement"] == "NO_NEW_GOLD_REQUIRED"
    assert receipt["objective_change_justified"] is True
    assert receipt["architecture_change_justified"] is False
    assert receipt["TRAIN"] is False
    assert receipt["V1R2_CREATED"] is False
    assert receipt["STAGE_A_BEST_MUTATED"] is False
    assert receipt["MODEL_WIDE_BEST_MUTATED"] is False
    assert receipt["NEXT_ACTION"] == "SPEC_STAGE_A_FACTORIZED_OBJECTIVE"
    assert receipt["NEXT_ACTION_AUTHORIZED"] is False
    assert receipt["receipt_sha256"].startswith("93202898")
    assert len(receipt["receipt_sha256"]) == 64
