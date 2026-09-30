"""Classification v3 evidence-surface builder tests. No train / reserve / BEST."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v3_evidence_gate import (  # noqa: E402
    CURRENT_STATE,
    FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
    FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
)
from hyperlexical.classification_v3_evidence_surface import (  # noqa: E402
    ACQUISITION_FLOORS,
    SCHEMA_FILES,
    SURFACE_RULE,
    VALIDATION_FLOORS,
    assign_splits,
    build_example,
    build_surface,
    classify_subtype,
    collect_pools,
    load_spent_v2_reserve_ids,
    preregistration_contract,
    validate_row,
)
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402

SCHEMA_DIR = ROOT / "specs/007-hyperlexical-model/schemas/classification-v3"
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
) -> dict:
    return {
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


def test_preregistration_freezes_gates_and_schemas():
    assert CURRENT_STATE == "RUNNING"
    contract = preregistration_contract()
    assert contract["state"] == "PREREGISTERED"
    assert contract["false_evidence_entry_rate_on_none_max"] == 0.05
    assert contract["false_evidence_entry_rate_on_none_max"] == FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX
    assert contract["family_emission_precision_min"] == FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE == 0.80
    assert contract["decision_semantics"]["NO_EVIDENCE"] == "NONE"
    assert contract["decision_semantics"]["UNCERTAIN"] == "ABSTAIN"
    assert contract["decision_semantics"]["EVIDENCE_PRESENT"] == "Stage_B_retrieval"
    assert contract["train"] is False
    for key, digest in SCHEMA_FILES.items():
        filename = {
            "evidence_example.v1": "evidence_example.v1.schema.json",
            "evidence_decision.v1": "evidence_decision.v1.schema.json",
            "family_candidates.v1": "family_candidates.v1.schema.json",
            "decision.v1": "decision.v1.schema.json",
        }[key]
        path = SCHEMA_DIR / filename
        observed = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
        assert observed == digest


def test_subtype_mapping_and_spent_exclusion():
    assert classify_subtype(_row("alpha beta gamma delta epsilon zeta", lineage="ai-native")) == "POSITIVE_EVIDENCE"
    assert classify_subtype(_row("brainrot", lineage="brainrot-aura")) == "HARD_NONE"
    assert classify_subtype(_row("the ordinary explanation of weather patterns", lineage="none")) == "NEAR_DOMAIN_NONE"
    assert classify_subtype(_row("ok", lineage="none")) == "GENERIC_NONE"
    assert classify_subtype(_row("ai", lineage="ai-native", klass="INFERRED")) == "AMBIGUOUS_EVIDENCE"
    spent = {normalized_text_sha256("spent phrase here")}
    pools = collect_pools(
        [
            _row("spent phrase here", lineage="ai-native"),
            _row("fresh positive evidence phrase one two three", lineage="ai-native"),
        ],
        spent_reserve_ids=spent,
    )
    assert len(pools["POSITIVE_EVIDENCE"]) == 1
    assert pools["POSITIVE_EVIDENCE"][0]["text"] == "fresh positive evidence phrase one two three"


def test_build_surface_meets_floors_and_disjointness():
    rows = []
    # POSITIVE
    for i in range(520):
        rows.append(
            _row(
                f"family bearing evidence phrase about ai systems number {i} with enough words",
                lineage="ai-native",
            )
        )
    # HARD_NONE via legacy
    for i in range(260):
        rows.append(_row(f"legacy brainrot aura lexical atom {i}", lineage="brainrot-aura"))
    # NEAR_DOMAIN_NONE
    for i in range(260):
        rows.append(
            _row(
                f"near domain prose without family evidence number {i} continues",
                lineage="none",
            )
        )
    # GENERIC_NONE
    for i in range(260):
        rows.append(_row(f"ok{i}", lineage="none"))
    # AMBIGUOUS short inferred actives
    for i in range(160):
        rows.append(_row(f"ai{i}", lineage="ai-native", klass="INFERRED"))

    spent = load_spent_v2_reserve_ids(
        ledger={
            "identities": [
                {
                    "normalized_text_sha256": normalized_text_sha256("reserve spent"),
                    "state": "EVAL_RESERVE",
                    "labels": [{"task": "classify"}],
                }
            ]
        },
        reserve_rows=[{"normalized_text_sha256": normalized_text_sha256("reserve spent")}],
    )
    built = build_surface(rows, spent_reserve_ids=spent, ontology=ONTOLOGY)
    assert built["readiness"]["state"] == "READY"
    assert built["assembled"]["disjointness"]["spent_v2_reserve_overlap_count"] == 0
    assert built["assembled"]["disjointness"]["pass"] is True
    counts = built["assembled"]["diagnostics"]["diagnostics"]["counts_by_subtype"]
    for subtype, floor in ACQUISITION_FLOORS.items():
        assert counts[subtype] >= floor
    val = built["assembled"]["diagnostics"]["diagnostics"]["validation_subtype_counts"]
    for subtype, floor in VALIDATION_FLOORS.items():
        assert val[subtype] >= floor
    assert built["assembled"]["split_manifest"]["v3_reserve"] is None
    assert SURFACE_RULE == "HYPERLEX_V3_EVIDENCE_SURFACE_V1"


def test_collect_pools_enforces_global_identity_uniqueness():
    text = "same identity conflict phrase with enough words here"
    pools = collect_pools(
        [
            _row(text, lineage="none"),
            _row(text, lineage="ai-native"),
            _row(text, lineage="brainrot-aura"),
        ],
        spent_reserve_ids=set(),
    )
    total = sum(len(values) for values in pools.values())
    assert total == 1
    assert len(pools["POSITIVE_EVIDENCE"]) == 1
    assert pools["POSITIVE_EVIDENCE"][0]["evidence_subtype"] == "POSITIVE_EVIDENCE"


def test_validate_row_rejects_inconsistent_positive():
    example = build_example(
        _row("positive family bearing prose about systems", lineage="ai-native"),
        "POSITIVE_EVIDENCE",
    )
    example["positive_evidence_spans"] = []
    errors = validate_row(example, ONTOLOGY)
    assert "positive_missing_spans" in errors


def test_assign_splits_is_deterministic():
    pools = {
        "POSITIVE_EVIDENCE": [
            build_example(_row(f"pos evidence words {i} more words here", lineage="ai-native"), "POSITIVE_EVIDENCE")
            for i in range(120)
        ],
        "HARD_NONE": [
            build_example(_row(f"hard none legacy {i}", lineage="brainrot-aura"), "HARD_NONE")
            for i in range(60)
        ],
        "NEAR_DOMAIN_NONE": [
            build_example(_row(f"near domain none prose {i} words", lineage="none"), "NEAR_DOMAIN_NONE")
            for i in range(60)
        ],
        "GENERIC_NONE": [
            build_example(_row(f"g{i}", lineage="none"), "GENERIC_NONE") for i in range(60)
        ],
        "AMBIGUOUS_EVIDENCE": [
            build_example(_row(f"x{i}", lineage="ai-native", klass="INFERRED"), "AMBIGUOUS_EVIDENCE")
            for i in range(40)
        ],
    }
    a = assign_splits(pools)
    b = assign_splits(pools)
    assert [row["identity"] for row in a["rows"]] == [row["identity"] for row in b["rows"]]
    assert [row["split"] for row in a["rows"]] == [row["split"] for row in b["rows"]]
