"""Frozen gates + cell assignment for BUILD_V5_STAGE_A_GENERALIZATION_SURFACE_V1."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_generalization_surface import (  # noqa: E402
    CELL_TRAIN_FLOOR,
    CRITICAL_CELLS,
    CRITICAL_VAL_FLOOR,
    DESIGN_RULE_REMEDIATE,
    EMBEDDING_HARDNESS,
    GATE_RULE,
    PAIRING_FLOORS,
    PRIMARY_CELLS,
    SHALLOW_SHORTCUT,
    SURFACE_BALANCE,
    SURFACE_RULE,
    SURFACE_RULE_V1R1,
    assign_primary_cell,
    compute_remediation_targets,
    frozen_generalization_gates,
    preregistration_contract,
    source_family,
)


def test_preregistration_pins_parallel_gates_not_v1r9():
    contract = preregistration_contract()
    assert contract["surface_rule"] == SURFACE_RULE
    assert contract["gate_rule"] == GATE_RULE
    assert contract["train"] is False
    assert contract["best_pointers"]["status"] == "UNCHANGED"
    gates = frozen_generalization_gates()
    assert gates["gate_rule"] == GATE_RULE
    assert gates["cell_train_floor"] == CELL_TRAIN_FLOOR
    assert gates["critical_val_floor"] == CRITICAL_VAL_FLOOR
    assert set(gates["primary_cells"]) == set(PRIMARY_CELLS)
    assert set(gates["critical_cells"]) == set(CRITICAL_CELLS)
    assert gates["pairing_floors"] == PAIRING_FLOORS
    assert gates["surface_balance"]["median_token_count_ratio_min"] == 0.85
    assert gates["surface_balance"]["atom_rate_abs_diff_max"] == 0.10
    assert SURFACE_BALANCE["median_token_count_ratio_max"] == 1.18
    assert gates["lexical_overlap"]["top_100_token_jaccard_min"] == 0.35
    assert EMBEDDING_HARDNESS["median_nearest_opposite_label_cosine_min"] == 0.65
    assert EMBEDDING_HARDNESS["frac_nearest_opposite_cosine_ge_0_75_min"] == 0.40
    assert SHALLOW_SHORTCUT["tfidf_balanced_accuracy_max"] == 0.75
    assert SHALLOW_SHORTCUT["length_only_balanced_accuracy_max"] == 0.57
    assert gates["weighted_score_allowed"] is False


def test_primary_cell_assignment_priority():
    assert (
        assign_primary_cell(text="rizz", evidence_label="EVIDENCE_PRESENT")
        == "SHORT_ATOM/EVIDENCE_PRESENT"
    )
    assert (
        assign_primary_cell(text="zx9", evidence_label="NO_EVIDENCE")
        == "SHORT_ATOM/NO_EVIDENCE"
    )
    assert (
        assign_primary_cell(
            text="Rizz is internet slang for charismatic appeal in dating contexts.",
            evidence_label="EVIDENCE_PRESENT",
        )
        == "DEFINITION_STYLE/EVIDENCE_PRESENT"
    )
    assert (
        assign_primary_cell(
            text="Xylem vessels transport water from roots through the plant stem tissue.",
            evidence_label="NO_EVIDENCE",
        )
        == "ORDINARY_PROSE/NO_EVIDENCE"
    )
    assert (
        assign_primary_cell(
            text="Online forums discussed internet habits without a clear slang family cue.",
            evidence_label="NO_EVIDENCE",
        )
        == "PROSE/NO_EVIDENCE"
    )


def test_wiktionary_shards_collapse_to_one_source_family():
    a = {
        "identity": "aa" * 32,
        "source_bucket": "v5_src_wik_botany_1",
        "source_url": "https://en.wiktionary.org/wiki/x",
        "evidence_subtype": "POSITIVE_EVIDENCE",
        "provenance": "OBSERVED",
    }
    b = {
        "identity": "bb" * 32,
        "source_bucket": "v5_src_wik_gaming_2",
        "source_url": "https://en.wiktionary.org/wiki/y",
        "evidence_subtype": "ORDINARY_DOMAIN_NONE",
        "provenance": "OBSERVED",
    }
    assert source_family(a) == "wiktionary_aggregate"
    assert source_family(b) == "wiktionary_aggregate"


def test_remediation_targets_dilution_math_and_frozen_gates():
    # Sealed V1 baseline counts from readiness freeze.
    baseline = {
        "median_token_ratio": 1.3846153846153846,
        "domain_deficits": {
            "need_none": {
                "astronomy": {"target_24": 17},
                "betting-sharp": {"target_24": 17},
                "crypto-degen": {"target_24": 12},
                "internet-slang": {"target_24": 16},
                "mathematics": {"target_24": 15},
                "technology-ai": {"target_24": 18},
            },
            "need_present": {"near-domain": {"target_24": 6}},
        },
        "wiktionary_share": {
            "EVIDENCE_PRESENT": {
                "count": 341,
                "n": 1223,
                "required_new_nonwik_at_0_24": 198,
                "required_new_nonwik_at_0_25": 141,
            },
            "NO_EVIDENCE": {
                "count": 329,
                "n": 1202,
                "required_new_nonwik_at_0_24": 169,
                "required_new_nonwik_at_0_25": 114,
            },
        },
    }
    targets = compute_remediation_targets(baseline)
    assert targets["strategy"] == "FRESH_NON_WIKTIONARY_MATCHED_CONTRAST_ADDITIONS"
    assert targets["required_new_nonwik_present"] == 198
    assert targets["required_new_nonwik_none"] == 169
    assert targets["gate_max_source_share"] == 0.25
    assert targets["acquisition_target_max_source_share"] == 0.24
    assert targets["length_direction"]["longer_label_needed"] == "NO_EVIDENCE"
    assert targets["fresh_short_atom_present"] == 40
    assert SURFACE_RULE_V1R1.endswith("V1R1")
    assert DESIGN_RULE_REMEDIATE.startswith("REMEDIATE_")
    # Readiness contract must remain frozen during remediation.
    gates = frozen_generalization_gates()
    assert gates["source_diversity"]["max_source_family_share"] == 0.25
    assert gates["shallow_shortcut"]["tfidf_balanced_accuracy_max"] == 0.75
    assert gates["surface_balance"]["median_token_count_ratio_max"] == 1.18
