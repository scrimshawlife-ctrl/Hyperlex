"""Mixed-failure remediation helpers — no train / reserve / BEST."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_mixed_remediate import (  # noqa: E402
    PARENT_DIAGNOSIS,
    PARENT_SURFACE_SHA,
    REMEDIATE_RULE,
    SURFACE_RULE_V1R8,
    TRAIN_ORDINARY_OBSERVED_FLOOR,
    TRAIN_PRESENT_OBSERVED_FLOOR,
    assign_component_splits_mixed,
    remediate_contract,
    stamp_source_buckets_mixed,
)
from hyperlexical.classification_v5_stage_a_surface_remediate import (  # noqa: E402
    build_near_dup_components,
)
from hyperlexical.classification_v5_surface_readiness_gates import GATE_RULE  # noqa: E402
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402


def _ex(
    text: str,
    *,
    subtype: str,
    label: str,
    prov: str = "INFERRED",
    topic: str = "chemistry",
    url: str | None = None,
    fam: str | None = None,
):
    identity = normalized_text_sha256(text)
    row = {
        "identity": identity,
        "text": text,
        "evidence_subtype": subtype,
        "evidence_label": label,
        "provenance": prov,
        "required_evidence_present": (
            "true"
            if label == "EVIDENCE_PRESENT"
            else ("uncertain" if label == "UNCERTAIN" else "false")
        ),
        "active_family_support": [fam or "gaming-meta"] if label == "EVIDENCE_PRESENT" else [],
        "source_sha256": identity,
        "topic_domain": topic if label != "EVIDENCE_PRESENT" else (fam or "gaming-meta"),
        "source_url": url,
        "split": "train",
        "pair_group_id": None,
        "paired_positive_identity": None,
        "shared_cues": [],
        "evidence_spans": (
            [{"start": 0, "end": max(1, len(text))}] if label == "EVIDENCE_PRESENT" else []
        ),
        "notes": "",
    }
    return row


def test_mixed_contract_frozen():
    contract = remediate_contract()
    assert contract["remediate_rule"] == REMEDIATE_RULE
    assert contract["parent_diagnosis"] == PARENT_DIAGNOSIS
    assert contract["parent_surface_dataset_sha256"] == PARENT_SURFACE_SHA
    assert contract["readiness_thresholds_modified"] is False
    assert contract["train"] is False
    assert contract["best"] == "UNCHANGED"
    assert contract["provenance_causality"] == "NOT_ESTABLISHED"
    assert SURFACE_RULE_V1R8.endswith("V1R8")
    assert GATE_RULE.endswith("GATES_V1")
    assert TRAIN_ORDINARY_OBSERVED_FLOOR >= 100
    assert TRAIN_PRESENT_OBSERVED_FLOOR >= 100


def test_wikipedia_source_bucket_distinct_from_wiktionary():
    wiki = _ex(
        "Ordinary anatomy prose from encyclopedia lead paragraph about bones.",
        subtype="ORDINARY_DOMAIN_NONE",
        label="NO_EVIDENCE",
        prov="OBSERVED",
        topic="anatomy",
        url="https://en.wikipedia.org/wiki/Bone",
    )
    wikt = _ex(
        "Ordinary anatomy sense definition without active family evidence here.",
        subtype="ORDINARY_DOMAIN_NONE",
        label="NO_EVIDENCE",
        prov="OBSERVED",
        topic="anatomy",
        url="https://en.wiktionary.org/wiki/bone",
    )
    stamped = stamp_source_buckets_mixed([wiki, wikt])
    assert stamped[0]["source_bucket"].startswith("v5_src_wp_anatomy_")
    assert stamped[1]["source_bucket"].startswith("v5_src_wik_anatomy_")


def test_mixed_split_protects_train_ordinary_observed():
    rows = []
    # Plenty of OBSERVED ordinary so both val provenance and train floor can hold.
    for i in range(80):
        rows.append(
            _ex(
                f"observed ordinary chemistry notebook entry {i} with mineral measurements",
                subtype="ORDINARY_DOMAIN_NONE",
                label="NO_EVIDENCE",
                prov="OBSERVED",
                topic="chemistry",
                url=f"https://en.wikipedia.org/wiki/Chem_{i}",
            )
        )
    for i in range(80):
        rows.append(
            _ex(
                f"observed positive gaming meta slang evidence span example {i}",
                subtype="POSITIVE_EVIDENCE",
                label="EVIDENCE_PRESENT",
                prov="OBSERVED",
                fam="gaming-meta",
            )
        )
    for i in range(40):
        rows.append(
            _ex(
                f"inferred ordinary geology fill row {i} without slang evidence",
                subtype="ORDINARY_DOMAIN_NONE",
                label="NO_EVIDENCE",
                prov="INFERRED",
                topic="geology",
            )
        )
    # Other subtypes for validation floors (small synthetic).
    for subtype, label, n in (
        ("HARD_NONE", "NO_EVIDENCE", 70),
        ("NEAR_DOMAIN_NONE", "NO_EVIDENCE", 70),
        ("GENERIC_NONE", "NO_EVIDENCE", 60),
        ("LEXICAL_LOOKALIKE_NONE", "NO_EVIDENCE", 60),
        ("SHORT_ATOM_NONE", "NO_EVIDENCE", 50),
        ("AMBIGUOUS_EVIDENCE", "UNCERTAIN", 50),
    ):
        for i in range(n):
            rows.append(
                _ex(
                    f"{subtype.lower()} synthetic row marker {i} unique text body",
                    subtype=subtype,
                    label=label,
                    prov="INFERRED",
                    topic="generic",
                )
            )

    comps = build_near_dup_components(rows)
    assigned = assign_component_splits_mixed(comps)
    support = assigned["support_floors"]
    # With 80 OBSERVED ordinary / PRESENT available, mixed split must retain
    # a non-zero train OBSERVED slice (V1R7 drained ordinary OBSERVED to 0).
    assert support["train_ord_obs"] >= 20
    assert support["train_pos_obs"] >= 20
    assert support["train_ord_obs"] <= 80
    assert support["train_pos_obs"] <= 80
