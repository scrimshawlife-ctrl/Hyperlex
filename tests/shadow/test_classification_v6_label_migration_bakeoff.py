"""CPU tests for V6 multi-level agreement, migration, bakeoff contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_architecture_bakeoff import (
    GENERALIZATION_GAP_GATE,
    bakeoff_contract,
    generalization_gap_pass,
    multilabel_f1,
    select_candidate,
)
from hyperlexical.classification_v6_human_ontology_settlement import dual_annotate_rows
from hyperlexical.classification_v6_label_migration import hierarchy_violation, migrate_row
from hyperlexical.classification_v6_multilabel_agreement import (
    three_level_agreement,
    wilson_interval,
)


def test_three_level_agreement_and_wilson():
    rows = [
        {"identity": "1", "text": "Casino blackjack odds and bookmaker vig."},
        {"identity": "2", "text": "Bitcoin airdrop on ethereum blockchain."},
        {"identity": "3", "text": "A pejorative insult and romantic dating partner."},
        {"identity": "4", "text": "An Abkhazian; a native or inhabitant of Abkhazia."},
        {"identity": "5", "text": "Software programming computer code debugger."},
    ]
    ann = dual_annotate_rows(rows)
    rep = three_level_agreement(ann)
    assert "level1_per_label" in rep
    assert "level2_per_example" in rep
    assert "level3_boundaries" in rep
    assert rep["acceptance_policy"]["cohen_kappa_sole_metric"] is False
    assert "gambling_vs_crypto" in rep["level3_boundaries"]
    ci = wilson_interval(8, 10)
    assert ci["lo"] is not None and ci["hi"] >= ci["lo"]


def test_migration_hierarchy_and_bakeoff_gates():
    row = migrate_row(
        {
            "identity": "x",
            "text": "LLM prompt for an agentic assistant model.",
            "evidence_label": "EVIDENCE_PRESENT",
            "gold_family": "ai-native",
            "split": "TRAIN",
        }
    )
    assert "domain.technology.ai_discourse" in row["domain_labels"]
    assert "domain.technology" in row["domain_labels"]
    assert hierarchy_violation(row["domain_labels"]) is False
    id_row = migrate_row(
        {
            "identity": "y",
            "text": "An Abkhazian inhabitant.",
            "evidence_label": "EVIDENCE_PRESENT",
            "gold_family": "identity-affiliation",
            "split": "TRAIN",
        }
    )
    assert id_row["human_resettlement_required"] is True
    c = bakeoff_contract()
    assert c["retrieval_first_core"] is False
    assert c["control_role"] == "CONTROL_NOT_ASSUMED_BACKBONE"
    assert generalization_gap_pass(0.5, 0.4) is True
    assert generalization_gap_pass(0.8, 0.5) is False
    assert GENERALIZATION_GAP_GATE["name"] == "GENERALIZATION_GAP_ACCEPTABLE"
    f1 = multilabel_f1([[1, 0], [0, 1]], [[1, 0], [0, 1]])
    assert f1["exact_match"] == 1.0
    sel = select_candidate(
        {
            "A_BASELINE_MULTIHEAD": {
                "DEV": {"system": {"macro_f1": 0.6}},
                "REP": {
                    "system": {"macro_f1": 0.55},
                    "hierarchy": {"hierarchy_violation_rate": 0.0},
                },
            }
        }
    )
    assert sel["advance"] is True
    assert sel["selected"] == "A_BASELINE_MULTIHEAD"
    assert sel["ranking"][0]["hierarchy_violation_rate_rep"] == 0.0
    assert sel["ranking"][0]["HIERARCHY_OK"] is True

    # Zero hierarchy violations must not be coerced to 1.0 via `0.0 or 1`.
    # Absolute REP floor must block near-chance macro-F1 from advancing.
    weak = select_candidate(
        {
            "A_BASELINE_MULTIHEAD": {
                "DEV": {"system": {"macro_f1": 0.019}},
                "REP": {
                    "system": {"macro_f1": 0.024},
                    "hierarchy": {"hierarchy_violation_rate": 0.0},
                },
            },
            "B_HIERARCHY_AWARE": {
                "DEV": {"system": {"macro_f1": 0.021}},
                "REP": {
                    "system": {"macro_f1": 0.016},
                    "hierarchy": {"hierarchy_violation_rate": 0.0},
                },
            },
        }
    )
    assert weak["advance"] is False
    assert weak["selected"] is None
    assert all(row["hierarchy_violation_rate_rep"] == 0.0 for row in weak["ranking"])
    assert all(row["ABS_REP_FLOOR_OK"] is False for row in weak["ranking"])
    assert GENERALIZATION_GAP_GATE["min_rep_system_macro_f1"] == 0.20
    assert GENERALIZATION_GAP_GATE["max_hierarchy_violation_rate_rep"] == 0.05
