"""Unit pins for factorized-relation SETTLED_FAIL diagnosis (read-only)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_factorized_relation_diagnose import (  # noqa: E402
    DATASET_CONSEQUENCES,
    DIAGNOSE_RULE,
    FAILED_CHECKPOINT_SHA256,
    FROZEN_OBSERVED_OUTCOME,
    NEXT_ACTIONS,
    PRIMARY_DIAGNOSES,
    assemble_diagnosis_receipt,
    classify_adaptation_depth,
    classify_layer_finding,
    classify_pooling,
    classify_token_signal,
    context_sufficiency_class,
    dataset_consequence,
    decide_next_action,
    decide_primary_diagnosis,
    irreducible_overlap_test,
    matched_pair_identifiability,
    normalize_text,
)


def test_diagnose_pins():
    assert DIAGNOSE_RULE == "DIAGNOSE_STAGE_A_FACTORIZED_RELATION_SETTLED_FAIL"
    assert FAILED_CHECKPOINT_SHA256.startswith("8a6981c1")
    assert FROZEN_OBSERVED_OUTCOME["n_threshold_passing"] == 0
    assert FROZEN_OBSERVED_OUTCOME["scientific_disposition"] == "SETTLED_FAIL"
    assert abs(FROZEN_OBSERVED_OUTCOME["SHORT_ATOM_NONE_relation_FPR"] - 0.539) < 0.01


def test_layer_and_adaptation_classifiers():
    assert (
        classify_layer_finding(
            best_layer=22, last_layer=22, best_ba=0.72, last_ba=0.71, any_separates=True
        )
        == "LAST_LAYER_BEST"
    )
    assert (
        classify_layer_finding(
            best_layer=10, last_layer=22, best_ba=0.75, last_ba=0.60, any_separates=True
        )
        == "INTERMEDIATE_LAYER_BETTER"
    )
    assert (
        classify_layer_finding(
            best_layer=5, last_layer=22, best_ba=0.55, last_ba=0.54, any_separates=False
        )
        == "NO_LAYER_SEPARATES"
    )
    assert (
        classify_adaptation_depth(
            layer_finding="NO_LAYER_SEPARATES", best_layer=5, n_layers=23
        )
        == "DEEPER_ADAPTATION_NOT_SUPPORTED"
    )
    assert (
        classify_adaptation_depth(
            layer_finding="INTERMEDIATE_LAYER_BETTER", best_layer=8, n_layers=23
        )
        == "DEEPER_ADAPTATION_JUSTIFIED"
    )
    assert (
        classify_adaptation_depth(
            layer_finding="LAST_LAYER_BEST", best_layer=22, n_layers=23
        )
        == "LAST_TWO_SUFFICIENT"
    )


def test_pooling_and_token_classifiers():
    assert (
        classify_pooling(cls_ba=0.55, best_alt_ba=0.62, best_alt_name="mean")
        == "POOLING_INFORMATION_LOSS"
    )
    assert (
        classify_pooling(cls_ba=0.72, best_alt_ba=0.73, best_alt_name="mean")
        == "CLS_SUFFICIENT"
    )
    assert (
        classify_pooling(cls_ba=0.55, best_alt_ba=0.56, best_alt_name="mean")
        == "POOLING_NOT_PRIMARY"
    )
    assert (
        classify_token_signal(
            token_ba=0.65, cls_ba=0.55, token_margin=0.05, cls_margin=0.01
        )
        == "TOKEN_SIGNAL_PRESENT_CLS_LOST"
    )
    assert (
        classify_token_signal(
            token_ba=0.52, cls_ba=0.51, token_margin=0.0, cls_margin=0.0
        )
        == "TOKEN_SIGNAL_ABSENT"
    )


def test_context_and_identifiability():
    assert normalize_text("  Foo   BAR ") == "foo bar"
    lexeme_none = {
        "evidence_label": "NO_EVIDENCE",
        "evidence_subtype": "SHORT_ATOM_NONE",
        "missing_required_semantics": ["active_family_evidence_absent"],
        "text": "bruh",
        "notes": "v5_gen_wikt_atom_none",
        "required_evidence_present": "false",
    }
    assert context_sufficiency_class(lexeme_none) == "LEXEME_ONLY"
    assert matched_pair_identifiability(lexeme_none) == "TEXT_IDENTIFIABLE"
    # NONE lexeme-only remains text-identifiable even when paired (negative
    # short atom is supported by bare lexeme). PRESENT lexeme-only with
    # wiktionary provenance requires external dictionary context.
    present_lexeme = {
        "evidence_label": "EVIDENCE_PRESENT",
        "evidence_subtype": "POSITIVE_EVIDENCE",
        "missing_required_semantics": [],
        "text": "crown",
        "notes": "v5_gen_wikt_atom_present:gaming-meta",
        "required_evidence_present": "true",
        "pair_group_id": "pg1",
    }
    assert matched_pair_identifiability(present_lexeme) == "REQUIRES_EXTERNAL_CONTEXT"
    assert context_sufficiency_class(present_lexeme) == "CONTEXT_DEPENDENT_RELATION"


def test_irreducible_and_primary_input_deficit():
    irr = irreducible_overlap_test(
        {
            "layer_finding": "NO_LAYER_SEPARATES",
            "linear_ba": 0.52,
            "nonlinear_ba": 0.53,
            "pooling_finding": "POOLING_NOT_PRIMARY",
            "best_pooling_ba": 0.54,
            "token_finding": "TOKEN_SIGNAL_ABSENT",
            "token_ba": 0.52,
            "exact_cross_label_collisions": 2,
            "short_atom_cross_label_collisions": 1,
            "requires_external_context_fraction": 0.40,
            "missing_input_material": True,
        }
    )
    assert irr["IRREDUCIBLE_SEMANTIC_OVERLAP"] is True
    primary = decide_primary_diagnosis(
        {
            "layer_finding": "NO_LAYER_SEPARATES",
            "adaptation_depth": "DEEPER_ADAPTATION_NOT_SUPPORTED",
            "pooling_finding": "POOLING_NOT_PRIMARY",
            "token_finding": "TOKEN_SIGNAL_ABSENT",
            "irreducible_overlap": irr,
            "missing_input_material": True,
            "requires_external_context_fraction": 0.40,
            "short_atom_cross_label_collisions": 1,
            "linear_ba": 0.52,
            "nonlinear_ba": 0.53,
            "best_pooling_ba": 0.54,
            "displacement_class": "mostly_preserved_parent_geometry",
        }
    )
    assert primary["primary_diagnosis"] == "IRREDUCIBLE_SEMANTIC_OVERLAP"
    assert decide_next_action(primary["primary_diagnosis"]) == "STOP_STAGE_A_RESEARCH"
    assert primary["primary_diagnosis"] in PRIMARY_DIAGNOSES
    assert decide_next_action(primary["primary_diagnosis"]) in NEXT_ACTIONS


def test_primary_model_input_deficit_without_full_irreducible():
    primary = decide_primary_diagnosis(
        {
            "layer_finding": "LAST_LAYER_BEST",
            "adaptation_depth": "LAST_TWO_SUFFICIENT",
            "pooling_finding": "POOLING_NOT_PRIMARY",
            "token_finding": "MIXED_TOKEN_SIGNAL",
            "irreducible_overlap": {"IRREDUCIBLE_SEMANTIC_OVERLAP": False},
            "missing_input_material": True,
            "requires_external_context_fraction": 0.35,
            "short_atom_cross_label_collisions": 0,
            "linear_ba": 0.55,
            "nonlinear_ba": 0.56,
            "best_pooling_ba": 0.57,
            "displacement_class": "reshaped_but_not_label_separating",
        }
    )
    assert primary["primary_diagnosis"] == "MODEL_INPUT_INFORMATION_DEFICIT"
    assert decide_next_action(primary["primary_diagnosis"]) == (
        "REVISE_GOLD_IDENTIFIABILITY_CONTRACT"
    )
    assert (
        dataset_consequence(
            primary["primary_diagnosis"],
            {"missing_input_material": True, "subtype_BA_gain": 0.43},
        )
        == "GOLD_CONTRACT_REPAIR_REQUIRED"
    )
    assert (
        dataset_consequence(
            primary["primary_diagnosis"],
            {"missing_input_material": True, "subtype_BA_gain": 0.0},
        )
        == "INPUT_ENRICHMENT_REQUIRED"
    )
    assert "INPUT_ENRICHMENT_REQUIRED" in DATASET_CONSEQUENCES


def test_assemble_receipt_immutable_flags():
    audit = {
        "layer_finding": "NO_LAYER_SEPARATES",
        "adaptation_depth": "DEEPER_ADAPTATION_NOT_SUPPORTED",
        "pooling_finding": "POOLING_NOT_PRIMARY",
        "token_finding": "TOKEN_SIGNAL_ABSENT",
        "irreducible_overlap": {
            "IRREDUCIBLE_SEMANTIC_OVERLAP": False,
            "checks": {},
        },
        "missing_input_material": True,
        "requires_external_context_fraction": 0.40,
        "short_atom_cross_label_collisions": 3,
        "exact_cross_label_collisions": 3,
        "linear_ba": 0.51,
        "nonlinear_ba": 0.52,
        "best_pooling_ba": 0.53,
        "displacement_class": "mostly_preserved_parent_geometry",
    }
    receipt = assemble_diagnosis_receipt(audit)
    assert receipt["TRAIN"] is False
    assert receipt["STAGE_A_BEST_MUTATED"] is False
    assert receipt["MODEL_WIDE_BEST_MUTATED"] is False
    assert receipt["V1R2_CREATED"] is False
    assert receipt["NEXT_ACTION_AUTHORIZED"] is False
    assert receipt["FAILED_CHECKPOINT_SHA256"].startswith("8a6981c1")
    assert len(receipt["receipt_sha256"]) == 64
