"""UNCERTAIN surface remediation helpers — no train / reserve / BEST."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v2_surface import surface_form  # noqa: E402
from hyperlexical.classification_v5_stage_a import derive_label_provenance  # noqa: E402
from hyperlexical.classification_v5_stage_a_uncertain_surface_remediate import (  # noqa: E402
    PARENT_DIAGNOSIS,
    PARENT_SURFACE_SHA,
    REMEDIATE_RULE,
    SURFACE_RULE_V1R9,
    build_uncertain_example,
    evaluate_uncertain_readiness_gates,
    make_inferred_uncertain_bank,
    present_uncertain_boundary_conflict,
    remediate_contract,
    select_uncertain_pool,
    source_family,
    summarize_semantic_placement,
)
from hyperlexical.classification_v5_surface_readiness_gates import GATE_RULE  # noqa: E402


def test_uncertain_remediate_contract_frozen():
    contract = remediate_contract()
    assert contract["remediate_rule"] == REMEDIATE_RULE
    assert contract["parent_diagnosis"] == PARENT_DIAGNOSIS
    assert contract["parent_surface_dataset_sha256"] == PARENT_SURFACE_SHA
    assert contract["readiness_thresholds_modified"] is False
    assert contract["train"] is False
    assert contract["best"] == "UNCHANGED"
    assert contract["reserve"] is False
    assert contract["checkpoint_driven_acquisition"] is False
    assert SURFACE_RULE_V1R9.endswith("V1R9")
    assert GATE_RULE.endswith("GATES_V1")
    assert PARENT_SURFACE_SHA.startswith("c0fdd82d")


def test_build_uncertain_example_required_fields_and_reasons():
    row = build_uncertain_example(
        text="Editors mark flex as boastful slang while another sense insists on stretching only.",
        ambiguity_reason="CONFLICTING_EVIDENCE",
        provenance="OBSERVED",
        source_url="https://en.wiktionary.org/wiki/flex",
        topic_domain="social-evaluation",
        candidate_families=["social-evaluation"],
        label_authority="HUMAN_SETTLED",
    )
    assert row["evidence_subtype"] == "AMBIGUOUS_EVIDENCE"
    assert row["gold_label"] == "UNCERTAIN"
    assert row["required_evidence_present"] == "uncertain"
    assert row["ambiguity_reason"] == "CONFLICTING_EVIDENCE"
    assert row["source_provenance"] == "OBSERVED"
    assert row["label_authority"] == "HUMAN_SETTLED"
    assert row["label_derivation"] == "AMBIGUITY_SETTLEMENT"
    assert row["reviewer_state"] == "SETTLED"
    assert row["source_identity"]
    assert source_family(row["source_bucket"]) == "wik"
    lp = derive_label_provenance(row)
    assert lp["authority"] == "HUMAN_SETTLED"
    assert lp["evidence_basis"][0]["ambiguity_reason"] == "CONFLICTING_EVIDENCE"


def test_inferred_bank_covers_all_reasons_and_forms():
    rows = make_inferred_uncertain_bank(blocked=set(), per_reason=20)
    reasons = {r["ambiguity_reason"] for r in rows}
    assert reasons == {
        "INSUFFICIENT_CONTEXT",
        "CONFLICTING_EVIDENCE",
        "PARTIAL_REQUIRED_CORE",
        "MULTIPLE_PLAUSIBLE_INTERPRETATIONS",
        "UNRESOLVED_SOURCE_MEANING",
    }
    forms = {surface_form(r["text"]) for r in rows}
    assert "PROSE" in forms
    assert all(r["provenance"] == "INFERRED" for r in rows)


def test_select_pool_prefers_observed():
    obs = [
        build_uncertain_example(
            text=f"Observed conflicting attestation number {i} with enough prose tokens here.",
            ambiguity_reason="CONFLICTING_EVIDENCE",
            provenance="OBSERVED",
            source_url=f"https://en.wiktionary.org/wiki/x{i}",
            topic_domain="social-evaluation",
            label_authority="HUMAN_SETTLED",
        )
        for i in range(5)
    ]
    inf = [
        build_uncertain_example(
            text=f"Inferred conflicting attestation number {i} with enough prose tokens here.",
            ambiguity_reason="CONFLICTING_EVIDENCE",
            provenance="INFERRED",
            topic_domain="social",
        )
        for i in range(5)
    ]
    # Minimal other reasons to satisfy selector loops.
    for reason in (
        "INSUFFICIENT_CONTEXT",
        "PARTIAL_REQUIRED_CORE",
        "MULTIPLE_PLAUSIBLE_INTERPRETATIONS",
        "UNRESOLVED_SOURCE_MEANING",
    ):
        obs.append(
            build_uncertain_example(
                text=f"Observed {reason.lower()} prose example with sufficient token count present.",
                ambiguity_reason=reason,
                provenance="OBSERVED",
                source_url=f"https://en.wikipedia.org/wiki/{reason}",
                topic_domain="memetic",
                label_authority="HUMAN_SETTLED",
            )
        )
    selected = select_uncertain_pool(obs, inf, target_per_reason=3)
    conflicting = [r for r in selected if r["ambiguity_reason"] == "CONFLICTING_EVIDENCE"]
    assert any(r["provenance"] == "OBSERVED" for r in conflicting)
    assert sum(1 for r in conflicting if r["provenance"] == "OBSERVED") >= 3


def test_boundary_conflict_detects_absorption():
    present_id = "a" * 64
    rows = [
        {
            "identity": present_id,
            "evidence_label": "UNCERTAIN",
            "evidence_subtype": "AMBIGUOUS_EVIDENCE",
        }
    ]
    report = present_uncertain_boundary_conflict(rows, genuine_present_fn_ids=[present_id])
    assert report["PRESENT_UNCERTAIN_BOUNDARY_CONFLICT"] is True


def test_semantic_placement_summary_rates():
    placements = [
        {
            "ambiguity_reason": "INSUFFICIENT_CONTEXT",
            "nearest_present_cosine": 0.7,
            "nearest_none_cosine": 0.7,
            "present_minus_none_margin": 0.0,
            "boundary_class": "CENTERED_BETWEEN",
        },
        {
            "ambiguity_reason": "CONFLICTING_EVIDENCE",
            "nearest_present_cosine": 0.9,
            "nearest_none_cosine": 0.7,
            "present_minus_none_margin": 0.2,
            "boundary_class": "PRESENT_LIKE",
        },
        {
            "ambiguity_reason": "PARTIAL_REQUIRED_CORE",
            "nearest_present_cosine": 0.6,
            "nearest_none_cosine": 0.9,
            "present_minus_none_margin": -0.3,
            "boundary_class": "NONE_LIKE",
        },
        {
            "ambiguity_reason": "MULTIPLE_PLAUSIBLE_INTERPRETATIONS",
            "nearest_present_cosine": 0.72,
            "nearest_none_cosine": 0.71,
            "present_minus_none_margin": 0.01,
            "boundary_class": "CENTERED_BETWEEN",
        },
    ]
    summary = summarize_semantic_placement(placements)
    assert summary["n"] == 4
    assert abs(summary["placement_rates"]["CENTERED_BETWEEN"] - 0.5) < 1e-9


def test_uncertain_gates_fail_closed_without_semantic_placement():
    rows = []
    for reason in (
        "INSUFFICIENT_CONTEXT",
        "CONFLICTING_EVIDENCE",
        "PARTIAL_REQUIRED_CORE",
        "MULTIPLE_PLAUSIBLE_INTERPRETATIONS",
        "UNRESOLVED_SOURCE_MEANING",
    ):
        for i in range(55):
            prov = "OBSERVED" if i < 30 else "INFERRED"
            text = (
                f"{reason} example {i} with deliberately long prose so surface_form is PROSE "
                f"and evidence sufficiency stays unresolved for reviewers."
            )
            row = build_uncertain_example(
                text=text,
                ambiguity_reason=reason,
                provenance=prov,
                source_url=(
                    f"https://en.wiktionary.org/wiki/{reason}_{i}"
                    if prov == "OBSERVED"
                    else None
                ),
                topic_domain="memetic",
                label_authority="HUMAN_SETTLED" if prov == "OBSERVED" else None,
            )
            row["split"] = "train" if i < 40 else "validation"
            rows.append(row)
    report = evaluate_uncertain_readiness_gates(rows, semantic_placement=None)
    assert report["state"] == "PREREGISTERED"
    assert report["gates"]["semantic_placement"]["pass"] is False
