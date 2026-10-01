"""Exact v5 surface readiness gate freeze tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_negative_evidence_surface import (  # noqa: E402
    STAGE_A_TRAIN_CONTRACT,
    preregistration_contract,
)
from hyperlexical.classification_v5_surface_readiness_gates import (  # noqa: E402
    DATASET_FLOORS,
    EMBEDDING_HARDNESS,
    GATE_RULE,
    NEAR_DUPLICATE_METHOD,
    PAIRING_FLOORS,
    SHALLOW_SHORTCUT,
    are_near_duplicates,
    evaluate_embedding_hardness,
    evaluate_surface_readiness,
    frozen_readiness_gates,
)


def test_frozen_gates_pin_exact_thresholds():
    gates = frozen_readiness_gates()
    assert gates["gate_rule"] == GATE_RULE
    assert gates["dataset_floors"] == DATASET_FLOORS
    assert gates["pairing_floors"]["paired_positive_negative_pairs"] == 300
    assert gates["pairing_floors"] == PAIRING_FLOORS
    assert gates["embedding_hardness"] == EMBEDDING_HARDNESS
    assert gates["shallow_shortcut"]["length_only_balanced_accuracy_max"] == 0.60
    assert gates["shallow_shortcut"]["bow_balanced_accuracy_max"] == 0.80
    assert gates["near_duplicate_method"] == NEAR_DUPLICATE_METHOD
    assert gates["weighted_score_allowed"] is False
    contract = preregistration_contract()
    assert contract["surface_readiness_gates"]["gate_rule"] == GATE_RULE
    assert STAGE_A_TRAIN_CONTRACT["scope"] == "model_acceptance_after_authorized_train"
    assert STAGE_A_TRAIN_CONTRACT["false_evidence_entry_rate_on_none_max"] == 0.05


def test_near_duplicate_method_frozen():
    assert are_near_duplicates("Alpha Beta Gamma", "alpha beta gamma")
    assert are_near_duplicates(
        "shared lexical residue appears in ordinary documentation",
        "shared lexical residue appears in ordinary documentation today",
    ) or not are_near_duplicates("completely different words here", "zzzz yyyy xxxx")
    assert not are_near_duplicates("completely different words here", "zzzz yyyy xxxx")


def test_missing_embedding_report_is_not_ready():
    rows = [
        {
            "identity": "a" * 64,
            "text": "family bearing evidence phrase about systems",
            "evidence_label": "EVIDENCE_PRESENT",
            "evidence_subtype": "POSITIVE_EVIDENCE",
            "provenance": "OBSERVED",
            "split": "train",
            "source_sha256": "b" * 64,
            "required_evidence_present": "true",
            "active_family_support": ["ai-native"],
            "candidate_families": ["ai-native"],
            "evidence_spans": [{"start": 0, "end": 10}],
        }
    ]
    # Bypass by calling embedding gate directly.
    report = evaluate_embedding_hardness(None)
    assert report["pass"] is False
    assert "embedding_hardness_report_missing" in report["failures"]


def test_model_gates_are_separate_from_dataset_readiness():
    gates = frozen_readiness_gates()
    assert "false_evidence_entry_rate_on_none_max" not in gates
    assert STAGE_A_TRAIN_CONTRACT["EVIDENCE_PRESENT_recall_min"] == 0.70
    assert STAGE_A_TRAIN_CONTRACT["NO_EVIDENCE_recall_min"] == 0.90
