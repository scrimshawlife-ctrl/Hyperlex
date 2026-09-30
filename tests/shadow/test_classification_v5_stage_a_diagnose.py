"""Read-only Stage-A settled-fail diagnosis unit tests. No GPU."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_diagnose import (  # noqa: E402
    CONTROLLED_RULE,
    DIAGNOSE_RULE,
    attach_row_features,
    controlled_comparison,
    counterfactual_gate_accounting,
    decide_diagnostic,
    error_cohort,
    interpret_controlled_gap,
    token_length_bucket,
)


def test_frozen_rules_and_buckets():
    assert DIAGNOSE_RULE.startswith("HYPERLEX_V5_STAGE_A_DIAGNOSE")
    assert CONTROLLED_RULE == "HYPERLEX_V5_STAGE_A_CONTROLLED_COMPARISON_V1"
    assert token_length_bucket("a b") == "1-2"
    assert token_length_bucket(" ".join(["t"] * 10)) == "9-16"
    assert decide_diagnostic(0.90) == "EVIDENCE_PRESENT"
    assert decide_diagnostic(0.10) == "NO_EVIDENCE"
    assert decide_diagnostic(0.52) == "UNCERTAIN"
    assert (
        error_cohort("NO_EVIDENCE", "EVIDENCE_PRESENT", "ORDINARY_DOMAIN_NONE")
        == "ORDINARY_DOMAIN_FALSE_PRESENT"
    )


def test_interpret_controlled_gap_rules():
    persist = interpret_controlled_gap(
        raw_deltas={"false_evidence_entry_rate": 0.12},
        controlled_deltas={"false_evidence_entry_rate": 0.08},
        coverage=0.70,
    )
    assert persist["state"] == "PROVENANCE_GAP_PERSISTS"
    explained = interpret_controlled_gap(
        raw_deltas={"false_evidence_entry_rate": 0.12},
        controlled_deltas={"false_evidence_entry_rate": 0.01},
        coverage=0.70,
    )
    assert explained["state"] == "PROVENANCE_GAP_EXPLAINED_BY_DISTRIBUTION"
    low = interpret_controlled_gap(
        raw_deltas={"false_evidence_entry_rate": 0.12},
        controlled_deltas={"false_evidence_entry_rate": 0.08},
        coverage=0.40,
    )
    assert low["state"] == "INSUFFICIENT_MATCHED_SUPPORT"


def _row(
    *,
    identity: str,
    label: str,
    subtype: str,
    provenance: str,
    decision: str,
    text: str,
    p_present: float,
    authority: str = "CANONICAL_RULE",
    derivation: str = "NEGATIVE_EXCLUSION",
    source_family: str = "hub",
    topic: str = "geology",
):
    form = "PROSE" if len(text.split()) >= 4 else "ATOM"
    return {
        "identity": identity,
        "evidence_label": label,
        "evidence_subtype": subtype,
        "provenance": provenance,
        "decision": decision,
        "text": text,
        "ATOM_PROSE": form,
        "definition_style": "NON_DEFINITION",
        "token_length_bucket": token_length_bucket(text),
        "source_family": source_family,
        "topic_domain": topic,
        "label_authority": authority,
        "label_derivation": derivation,
        "reviewer_state": "UNREVIEWED_RULE_DERIVED",
        "rule_id": "RULE",
        "mean_probs": {
            "EVIDENCE_PRESENT": p_present,
            "NO_EVIDENCE": 1.0 - p_present,
            "UNCERTAIN": 0.0,
        },
        "nearest_positive_similarity": 0.75,
        "nearest_none_similarity": 0.70,
        "positive_minus_none_margin": 0.05,
        "positive_neighbor_similarity_bucket": "0.70-0.80",
        "error_cohort": error_cohort(label, decision, subtype),
        "label_provenance": {
            "authority": authority,
            "derivation": derivation,
            "reviewer_state": "UNREVIEWED_RULE_DERIVED",
            "rule_id": "RULE",
            "rule_version": "1",
            "rule_sha256": "a" * 64,
            "decision_sha256": "b" * 64,
            "source_labels": [],
            "evidence_basis": [{"type": "EXCLUSION_RULE", "reference": "x"}],
        },
        "required_evidence_present": "false" if label == "NO_EVIDENCE" else "true",
        "active_family_support": [],
        "pair_group_id": None,
        "paired_positive_identity": None,
        "source_url": None,
        "word_count": len(text.split()),
    }


def test_controlled_comparison_and_accounting():
    rows = []
    # Build matched strata: OBSERVED worse false-entry than INFERRED on same stratum.
    for i in range(8):
        rows.append(
            _row(
                identity=f"obs{i}",
                label="NO_EVIDENCE",
                subtype="ORDINARY_DOMAIN_NONE",
                provenance="OBSERVED",
                decision="EVIDENCE_PRESENT" if i < 4 else "NO_EVIDENCE",
                text="this is ordinary geology prose text here",
                p_present=0.8 if i < 4 else 0.1,
            )
        )
        rows.append(
            _row(
                identity=f"inf{i}",
                label="NO_EVIDENCE",
                subtype="ORDINARY_DOMAIN_NONE",
                provenance="INFERRED",
                decision="NO_EVIDENCE",
                text="this is ordinary geology prose text here",
                p_present=0.1,
            )
        )
    for i in range(6):
        rows.append(
            _row(
                identity=f"pos{i}",
                label="EVIDENCE_PRESENT",
                subtype="POSITIVE_EVIDENCE",
                provenance="INFERRED",
                decision="EVIDENCE_PRESENT",
                text="slang meme atom vibes here now",
                p_present=0.9,
                derivation="MAPPED",
                authority="CANONICAL_RULE",
            )
        )
    report = controlled_comparison(rows)
    assert report["rule"] == CONTROLLED_RULE
    assert report["exact_strata"]["n_strata"] >= 1
    assert "interpretation" in report
    accounting = counterfactual_gate_accounting(rows)
    assert "minimum_corrections" in accounting
    assert accounting["minimum_corrections"]["false_PRESENT_to_non_PRESENT"] >= 0


def test_attach_row_features_without_embeddings():
    surface = [
        {
            "identity": "x1",
            "text": "short atom",
            "evidence_label": "NO_EVIDENCE",
            "evidence_subtype": "HARD_NONE",
            "provenance": "INFERRED",
            "required_evidence_present": "false",
            "active_family_support": [],
            "source_bucket": "v5_src_inf_HARD_NONE_0",
            "topic_domain": "wiki",
            "source_url": None,
            "pair_group_id": None,
            "paired_positive_identity": None,
        }
    ]
    enriched = attach_row_features(
        surface,
        provenance_by_id={},
        embeddings=None,
        probs=[{"NO_EVIDENCE": 0.9, "EVIDENCE_PRESENT": 0.05, "UNCERTAIN": 0.05}],
        decisions=["NO_EVIDENCE"],
    )
    assert enriched[0]["ATOM_PROSE"] in {"ATOM", "PROSE", "AMBIGUOUS"}
    assert enriched[0]["token_length_bucket"] in {
        "1-2",
        "3-4",
        "5-8",
        "9-16",
        "17-32",
        "33+",
    }
