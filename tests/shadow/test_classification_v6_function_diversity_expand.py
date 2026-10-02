"""CPU tests for EXPAND_V6_FUNCTION_DIVERSITY_AND_POSITIVE_REPRESENTATION."""

from __future__ import annotations

from hyperlexical.classification_v6_function_diversity_expand import (
    FUNCTION_VOCAB,
    PHASE_RULE,
    REVIEW_RECEIPT_SHA256,
    build_expand_receipt,
    classify_outcome,
    diversity_audit_pass,
    expand_contract,
    none_preserved,
    source_style,
)


def test_expand_contract_freezes_gate_and_blocks_qual003():
    c = expand_contract()
    assert c["PHASE_RULE"] == PHASE_RULE
    assert c["QUALIFICATION_USED_FOR_OPTIMIZATION"] is False
    assert c["frozen"]["ANY_LABEL_threshold"] == 0.22499999999999998
    assert c["frozen"]["ontology_changed"] is False
    assert "retune_ANY_LABEL_threshold" in c["forbidden"]
    assert "use_QUAL_003_rows_for_training" in c["forbidden"]
    assert "select_by_model_misclassification" in c["forbidden"]
    assert c["parent_review_receipt_sha256"] == REVIEW_RECEIPT_SHA256
    assert c["train_policy"]["keep_NONE_gate_frozen"] is True
    assert set(FUNCTION_VOCAB) == set(c["diversity_targets"]["function_vocab"])
    assert source_style("v6_expand_wiki_culture:memetic") == "encyclopedic_positive"
    assert source_style("v6_wikt_present:gaming-meta") == "wiktionary_sense"


def test_diversity_audit_and_outcome_advance():
    audit = {
        "disjointness_pass": True,
        "qual003_blocked": True,
        "rep": {
            "zero_label_share": 0.60,
            "function_n": 160,
            "function_non_wikt_share": 0.30,
            "function_medium_long_share": 0.55,
            "domain_function_pairs_n": 10,
            "per_function_support": {lab: 20 for lab in FUNCTION_VOCAB},
        },
        "train": {"per_function_support": {lab: 50 for lab in FUNCTION_VOCAB}},
    }
    d = diversity_audit_pass(audit)
    assert d["pass"] is True
    none = none_preserved(
        {
            "zero_label_false_positive_rate": 0.10,
            "zero_label_exact_rejection": 0.90,
        }
    )
    assert none["pass"] is True
    outcome = classify_outcome(
        diversity_pass=True,
        none=none,
        candidate={
            "FUNCTION_macro_f1": 0.28,
            "positive_only_system_macro_f1": 0.45,
            "system_macro_f1": 0.40,
        },
        baseline={
            "FUNCTION_macro_f1": 0.22,
            "positive_only_system_macro_f1": 0.41,
            "system_macro_f1": 0.37,
        },
    )
    assert outcome["OUTCOME"] == "V6_FUNCTION_DIVERSITY_ADVANCE"
    assert (
        outcome["NEXT_ACTION"]
        == "HARDEN_V6_POSITIVE_SEMANTIC_GENERALIZATION"
    )
    receipt = build_expand_receipt(
        {"OUTCOME": outcome["OUTCOME"], "NEXT_ACTION": outcome["NEXT_ACTION"]},
        sealed_at="2026-10-02T00:00:00Z",
    )
    assert receipt["NONE_GATE_MUTATED"] is False
    assert receipt["SYSTEM_EXPAND_RECEIPT_SHA256"]


def test_outcome_redesign_when_support_ok_but_function_weak():
    none = none_preserved(
        {
            "zero_label_false_positive_rate": 0.12,
            "zero_label_exact_rejection": 0.85,
        }
    )
    outcome = classify_outcome(
        diversity_pass=True,
        none=none,
        candidate={
            "FUNCTION_macro_f1": 0.12,
            "positive_only_system_macro_f1": 0.40,
            "system_macro_f1": 0.35,
        },
        baseline={
            "FUNCTION_macro_f1": 0.22,
            "positive_only_system_macro_f1": 0.41,
            "system_macro_f1": 0.37,
        },
    )
    assert outcome["OUTCOME"] == "V6_FUNCTION_DIVERSITY_NO_ADVANCE"
    assert outcome["NEXT_ACTION"] == "REDESIGN_V6_FUNCTION_PREDICTION"


def test_continue_acquisition_when_diversity_fails():
    outcome = classify_outcome(
        diversity_pass=False,
        none=none_preserved(
            {
                "zero_label_false_positive_rate": 0.10,
                "zero_label_exact_rejection": 0.90,
            }
        ),
        candidate={
            "FUNCTION_macro_f1": 0.30,
            "positive_only_system_macro_f1": 0.50,
            "system_macro_f1": 0.45,
        },
        baseline={
            "FUNCTION_macro_f1": 0.22,
            "positive_only_system_macro_f1": 0.41,
            "system_macro_f1": 0.37,
        },
    )
    assert outcome["OUTCOME"] == "V6_FUNCTION_DIVERSITY_NO_ADVANCE"
    assert outcome["NEXT_ACTION"] == "CONTINUE_V6_FUNCTION_DATA_ACQUISITION"
