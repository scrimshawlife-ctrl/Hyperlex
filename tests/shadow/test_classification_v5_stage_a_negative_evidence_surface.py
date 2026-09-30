"""Classification v5 Stage-A negative-evidence surface tests. No train / reserve / BEST."""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_negative_evidence_surface import (  # noqa: E402
    ACQUISITION_FLOORS,
    SCHEMA_SHA,
    STAGE_A_TRAIN_CONTRACT,
    SURFACE_RULE,
    VALIDATION_FLOORS,
    assign_splits,
    build_example,
    build_surface,
    classify_hub_subtype,
    collect_pools,
    load_blocked_ids,
    ordinary_domain_fill_rows,
    preregistration_contract,
    select_balanced_pools,
    validate_row,
)
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402

SCHEMA_DIR = ROOT / "specs/007-hyperlexical-model/schemas/classification-v5"
ONTOLOGY = (
    "ai-native",
    "gaming-meta",
    "crypto-degen",
    "betting-sharp",
    "internet-slang",
)


def _row(
    text: str,
    *,
    lineage: str,
    klass: str = "OBSERVED",
    split: str = "train",
    task: str = "classify",
    evidence_subtype: str | None = None,
    topic_domain: str | None = None,
) -> dict:
    payload = {
        "text": text,
        "lineage": lineage,
        "class": klass,
        "split": split,
        "task": task,
        "jev": "OFF",
        "surface": "train",
        "evaluation_reserve": False,
        "held_out": False,
    }
    if evidence_subtype is not None:
        payload["evidence_subtype"] = evidence_subtype
    if topic_domain is not None:
        payload["topic_domain"] = topic_domain
    return payload


def test_preregistration_and_schema_pin():
    contract = preregistration_contract()
    assert contract["state"] == "PREREGISTERED"
    assert contract["train"] is False
    assert contract["best"] == "UNCHANGED"
    assert contract["stage_a_train_contract"]["false_evidence_entry_rate_on_none_max"] == 0.05
    assert STAGE_A_TRAIN_CONTRACT["EVIDENCE_PRESENT_recall_min"] == 0.70
    assert STAGE_A_TRAIN_CONTRACT["NO_EVIDENCE_recall_min"] == 0.90
    path = SCHEMA_DIR / "evidence_example.v1.schema.json"
    observed = hashlib.sha256(path.read_bytes()).hexdigest()
    assert observed == SCHEMA_SHA["evidence_example.v1"]
    assert SURFACE_RULE == "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1"


def test_subtype_mapping_and_forced_ordinary():
    assert (
        classify_hub_subtype(
            _row("family bearing evidence phrase about systems", lineage="ai-native"),
            positive_token_union=set(),
        )
        == "POSITIVE_EVIDENCE"
    )
    assert (
        classify_hub_subtype(
            _row("ok", lineage="none"),
            positive_token_union=set(),
        )
        == "SHORT_ATOM_NONE"
    )
    forced = classify_hub_subtype(
        _row(
            "Granite is a common igneous rock.",
            lineage="none",
            evidence_subtype="ORDINARY_DOMAIN_NONE",
            topic_domain="geology",
        ),
        positive_token_union=set(),
    )
    assert forced == "ORDINARY_DOMAIN_NONE"


def test_load_blocked_ids_excludes_train_consumed_but_keeps_spent_reserves():
    spent_text = "spent reserve phrase one"
    free_text = "free train consumed phrase"
    blocked = load_blocked_ids(
        ledger={
            "identities": [
                {
                    "normalized_text_sha256": normalized_text_sha256(spent_text),
                    "state": "EVAL_SPENT",
                    "evaluation_spent": True,
                },
                {
                    "normalized_text_sha256": normalized_text_sha256(free_text),
                    "state": "TRAIN_CONSUMED",
                    "training_consumed": True,
                },
            ]
        },
        spent_row_files=[[{"text": spent_text, "identity": normalized_text_sha256(spent_text)}]],
    )
    assert normalized_text_sha256(spent_text) in blocked
    assert normalized_text_sha256(free_text) not in blocked


def test_ordinary_domain_bank_covers_labels():
    rows = ordinary_domain_fill_rows(blocked_ids=set())
    domains = {row["topic_domain"] for row in rows}
    assert len(rows) >= 400
    assert len(domains) >= 8


def test_build_surface_meets_floors_and_can_be_ready():
    rows = []
    for i in range(820):
        if i % 5 == 0:
            text = f"rizz{i}"
        elif i % 5 == 1:
            text = f"agent prompt {i} meta"
        elif i % 5 == 2:
            text = f"family bearing evidence phrase about ai systems number {i}"
        elif i % 5 == 3:
            text = (
                f"family bearing evidence phrase about ai systems number {i} "
                f"with enough words for medium length prose"
            )
        else:
            text = (
                f"extended family bearing evidence phrase about ai systems number {i} "
                f"with enough words for longer definitional prose and ordinary cadence"
            )
        rows.append(_row(text, lineage="ai-native"))
    for i in range(320):
        rows.append(
            _row(
                f"legacy brainrot aura lexical residue {i} words here with extra filler prose",
                lineage="brainrot-aura",
            )
        )
    for i in range(320):
        rows.append(
            _row(
                f"near domain prose without family evidence number {i} continues online discussion threads",
                lineage="none",
            )
        )
    for i in range(220):
        rows.append(_row(f"gx{i}", lineage="none"))
    for i in range(220):
        rows.append(_row(f"ai{i}", lineage="ai-native", klass="INFERRED"))

    blocked = load_blocked_ids(
        ledger={
            "identities": [
                {
                    "normalized_text_sha256": normalized_text_sha256("reserve spent v4"),
                    "state": "EVAL_SPENT",
                    "evaluation_spent": True,
                }
            ]
        },
        spent_row_files=[[{"text": "reserve spent v4"}]],
    )
    built = build_surface(rows, blocked_ids=blocked, ontology=ONTOLOGY, augment=True)
    assert built["readiness"]["state"] == "READY"
    assert built["assembled"]["disjointness"]["spent_reserve_overlap_count"] == 0
    assert built["assembled"]["disjointness"]["pass"] is True
    counts = built["assembled"]["diagnostics"]["diagnostics"]["counts_by_subtype"]
    for subtype, floor in ACQUISITION_FLOORS.items():
        assert counts[subtype] >= floor, (subtype, counts.get(subtype), floor)
    val = built["assembled"]["diagnostics"]["diagnostics"]["validation_subtype_counts"]
    for subtype, floor in VALIDATION_FLOORS.items():
        assert val[subtype] >= floor, (subtype, val.get(subtype), floor)
    assert built["assembled"]["stage_a_train_contract"] is not None
    assert (
        built["assembled"]["stage_a_train_contract"][
            "false_evidence_entry_rate_on_none_max"
        ]
        == 0.05
    )
    assert built["assembled"]["diagnostics"]["diagnostics"]["paired_positive_negative_count"] >= 1
    ordinary = built["assembled"]["diagnostics"]["diagnostics"]["ordinary_domain_coverage"]
    assert ordinary["pass"] is True
    assert built["assembled"]["shortcut"]["pass"] is True
    assert built["assembled"]["shallow"]["pass"] is True


def test_spent_overlap_blocks_ready():
    text = "positive family bearing prose about systems unique spent"
    rows = [_row(text, lineage="ai-native")]
    for i in range(50):
        rows.append(_row(f"filler positive evidence words {i} more here", lineage="ai-native"))
    blocked = {normalized_text_sha256(text)}
    pools = collect_pools(rows, blocked_ids=blocked)
    assert all(item["identity"] != normalized_text_sha256(text) for item in pools["POSITIVE_EVIDENCE"])


def test_validate_row_and_select_caps_short_atom():
    example = build_example(
        _row("positive family bearing prose about systems", lineage="ai-native"),
        "POSITIVE_EVIDENCE",
    )
    assert validate_row(example, ONTOLOGY) == []
    example["required_evidence_present"] = "false"
    assert "required_evidence_present_mismatch" in validate_row(example, ONTOLOGY)

    pools = {
        "POSITIVE_EVIDENCE": [
            build_example(_row(f"pos evidence words {i} more words here", lineage="ai-native"), "POSITIVE_EVIDENCE")
            for i in range(20)
        ],
        "SHORT_ATOM_NONE": [
            build_example(_row(f"z{i}", lineage="none"), "SHORT_ATOM_NONE") for i in range(500)
        ],
        "ORDINARY_DOMAIN_NONE": [],
        "HARD_NONE": [],
        "NEAR_DOMAIN_NONE": [],
        "GENERIC_NONE": [],
        "LEXICAL_LOOKALIKE_NONE": [],
        "AMBIGUOUS_EVIDENCE": [],
    }
    balanced = select_balanced_pools(pools)
    assert len(balanced["SHORT_ATOM_NONE"]) <= 240


def test_assign_splits_keeps_pairs_together():
    pos = build_example(
        _row("pair positive evidence words shared alpha beta", lineage="ai-native"),
        "POSITIVE_EVIDENCE",
    )
    neg = build_example(
        _row("pair negative ordinary alpha beta without family", lineage="none", evidence_subtype="HARD_NONE"),
        "HARD_NONE",
    )
    group = "abcd1234"
    pos["pair_group_id"] = group
    neg["pair_group_id"] = group
    neg["paired_positive_identity"] = pos["identity"]
    result = assign_splits([pos, neg])
    by_id = {row["identity"]: row for row in result["rows"]}
    assert by_id[pos["identity"]]["split"] == by_id[neg["identity"]]["split"]
