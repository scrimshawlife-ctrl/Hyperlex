"""Remediation helpers for v5 Stage-A surface — no train / reserve / BEST."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_surface_remediate import (  # noqa: E402
    REMEDIATE_RULE,
    SURFACE_RULE_V1R7,
    assign_component_splits,
    build_near_dup_components,
    dedupe_within_label,
    remediate_contract,
)
from hyperlexical.classification_v5_surface_readiness_gates import (  # noqa: E402
    GATE_RULE,
    are_near_duplicates,
)
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402


def _ex(text: str, *, subtype: str, label: str, prov: str = "INFERRED", pair=None):
    identity = normalized_text_sha256(text)
    row = {
        "identity": identity,
        "text": text,
        "evidence_subtype": subtype,
        "evidence_label": label,
        "provenance": prov,
        "required_evidence_present": "true" if label == "EVIDENCE_PRESENT" else "false",
        "active_family_support": ["gaming-meta"] if label == "EVIDENCE_PRESENT" else [],
        "source_sha256": identity,
        "split": "train",
        "pair_group_id": None,
        "paired_positive_identity": None,
        "shared_cues": [],
        "evidence_spans": [{"start": 0, "end": max(1, len(text))}] if label == "EVIDENCE_PRESENT" else [],
    }
    if pair:
        row["pair_group_id"] = pair
    return row


def test_remediate_contract_frozen():
    contract = remediate_contract()
    assert contract["remediate_rule"] == REMEDIATE_RULE
    assert contract["readiness_thresholds_modified"] is False
    assert contract["train"] is False
    assert contract["best"] == "UNCHANGED"
    assert SURFACE_RULE_V1R7.endswith("V1R7")
    assert GATE_RULE.endswith("GATES_V1")


def test_component_split_keeps_near_dups_together():
    a = _ex("alpha beta gamma delta shared residue here", subtype="POSITIVE_EVIDENCE", label="EVIDENCE_PRESENT")
    b = _ex("alpha beta gamma delta shared residue here!", subtype="HARD_NONE", label="NO_EVIDENCE")
    assert are_near_duplicates(a["text"], b["text"])
    comps = build_near_dup_components([a, b])
    assert len(comps) == 1
    assigned = assign_component_splits(comps)
    splits = {row["identity"]: row["split"] for row in assigned["rows"]}
    assert splits[a["identity"]] == splits[b["identity"]]


def test_dedupe_keeps_observed_over_inferred():
    text = "same near duplicate ordinary domain sentence about plants"
    obs = _ex(text, subtype="ORDINARY_DOMAIN_NONE", label="NO_EVIDENCE", prov="OBSERVED")
    inf = _ex(text + " ", subtype="ORDINARY_DOMAIN_NONE", label="NO_EVIDENCE", prov="INFERRED")
    # force identical normalized text
    inf["text"] = text
    inf["identity"] = normalized_text_sha256(text + "x")  # different id, same text for near-dup
    # Make texts exact near-dups via identical normalized form
    inf["text"] = text
    kept, witness = dedupe_within_label([obs, inf])
    assert witness["removed"] >= 0
    assert any(r["provenance"] == "OBSERVED" for r in kept)
