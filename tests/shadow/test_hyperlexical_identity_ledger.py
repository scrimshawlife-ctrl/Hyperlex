"""Text identity owns contamination. Admission never consults a model score."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402
from hyperlexical.identity_ledger import (  # noqa: E402
    PLANNING_TARGETS,
    IdentityLedger,
    acquisition_gap,
    assert_training_disjoint_from_reserve,
    derived_state,
)
from hyperlexical.selection_surface import row_id  # noqa: E402

TINY = {
    "classify": 1,
    "classify_observed": 1,
    "classify_non_none": 1,
    "unbind_clean": 1,
}


def _row(text, *, split="train", task="classify", cls="OBSERVED", lineage="brainrot", declared=None):
    row = {
        "text": text,
        "fillers": ["atom"],
        "roles": ["pos_0"],
        "role_scheme": "positional",
        "class": cls,
        "split": split,
        "task": task,
        "lineage": lineage,
    }
    if declared is not None:
        row["row_id"] = declared
    return row


def test_identity_function_is_the_holdout_guard():
    assert normalized_text_sha256("Hello, WORLD") == normalized_text_sha256("hello world")
    digest = normalized_text_sha256("Hello, WORLD")
    ledger = IdentityLedger()
    ledger.observe_row(_row("Hello, WORLD"), source_artifact="unit", provenance="unit", catalogued=True)
    assert digest in ledger.identities
    blob = json.dumps(ledger.project())
    assert "Hello" not in blob
    assert "WORLD" not in blob


def test_historical_blocks_are_monotonic():
    ledger = IdentityLedger()
    row = _row("consumed phrase alpha")
    digest = ledger.observe_row(row, source_artifact="pin", provenance="pin", catalogued=True)
    ledger.mark_historical(digest, "training_consumed", source_artifact="pin", provenance="trained")
    assert derived_state(ledger.identity(digest)) == "TRAIN_CONSUMED"
    with pytest.raises(SystemExit, match="monotonic"):
        ledger.transition(digest, "EVAL_RESERVE", source_artifact="nope", provenance="nope")
    spent = ledger.observe_row(_row("spent phrase beta"), source_artifact="v2", provenance="v2", catalogued=True)
    ledger.mark_historical(spent, "evaluation_spent", source_artifact="v2", provenance="spent")
    with pytest.raises(SystemExit, match="monotonic"):
        ledger.transition(spent, "EVAL_RESERVE", source_artifact="nope", provenance="nope")
    abandoned = ledger.observe_row(
        _row("abandoned phrase gamma"), source_artifact="select", provenance="select", catalogued=True
    )
    ledger.mark_historical(
        abandoned, "evaluation_abandoned", source_artifact="select", provenance="abandoned"
    )
    with pytest.raises(SystemExit, match="monotonic"):
        ledger.transition(abandoned, "EVAL_RESERVE", source_artifact="nope", provenance="nope")


def test_generation_reset_does_not_clear_flags():
    ledger = IdentityLedger()
    digest = ledger.observe_row(_row("keep this trained"), source_artifact="pin", provenance="pin", catalogued=True)
    ledger.mark_historical(digest, "training_consumed", source_artifact="pin", provenance="trained")
    with pytest.raises(SystemExit, match="generation reset"):
        ledger.request_generation_reset(governed_receipt="", confirm=False)
    result = ledger.request_generation_reset(governed_receipt="receipts/governed.json", confirm=True)
    assert result["applied"] is False
    assert result["flags_cleared"] == 0
    assert ledger.identity(digest)["training_consumed"] is True
    assert derived_state(ledger.identity(digest)) == "TRAIN_CONSUMED"


def test_admit_reserves_by_slice_not_by_score():
    ledger = IdentityLedger()
    rows = [
        _row("observed classify one", cls="OBSERVED", lineage="brainrot"),
        _row("inferred classify two", cls="INFERRED", lineage="brainrot"),
        _row("clean unbind", task="unbind", cls="INFERRED", lineage="brainrot"),
        _row("second clean unbind", task="unbind", cls="INFERRED", lineage="brainrot"),
    ]
    clean = {normalized_text_sha256(rows[2]["text"]), normalized_text_sha256(rows[3]["text"])}
    report = ledger.admit(
        rows,
        batch_id="batch-a",
        source_artifact="acquire",
        targets=TINY,
        unbind_clean_hashes=clean,
    )
    assert report["raw_rows"] == 4
    assert report["unique_canonical_text_identities"] == 4
    assert report["unique_admitted_to_eval_reserve"] + report["unique_routed_to_train_candidate"] == 4
    assert report["unique_routed_to_train_candidate"] >= 1
    assert report["model_outcomes_consulted"] is False
    counts = ledger.reserve_counts()
    assert counts["classify_observed"] == 1
    assert counts["classify_non_none"] >= 1
    assert counts["unbind_clean"] == 1


def test_duplicate_text_does_not_increase_reserve_and_new_text_with_old_id_is_separate():
    ledger = IdentityLedger()
    first = _row("same surface", cls="OBSERVED", lineage="brainrot")
    report = ledger.admit(
        [first],
        batch_id="batch-b",
        source_artifact="acquire",
        targets=TINY,
    )
    assert report["unique_admitted_to_eval_reserve"] == 1
    twin = _row("same surface", split="val", cls="OBSERVED", lineage="brainrot")
    assert row_id(twin) != row_id(first)
    again = ledger.admit([twin], batch_id="batch-c", source_artifact="acquire", targets=TINY)
    assert again["unique_admitted_to_eval_reserve"] == 0
    assert again["rejected_existing_identities"]["EVAL_RESERVE"] == 1
    assert ledger.reserve_counts()["classify"] == 1
    fresh = _row("different surface", cls="INFERRED", lineage="brainrot", declared=row_id(first))
    collided = ledger.admit([fresh], batch_id="batch-d", source_artifact="acquire", targets=TINY)
    assert collided["row_id_collisions_with_new_text"] == 1
    assert collided["unique_admitted_to_eval_reserve"] == 0
    assert collided["unique_routed_to_train_candidate"] == 1
    assert normalized_text_sha256(fresh["text"]) != normalized_text_sha256(first["text"])


def test_blocked_hashes_are_rejected_and_scores_are_refused():
    ledger = IdentityLedger()
    consumed = _row("already trained")
    digest = ledger.observe_row(consumed, source_artifact="pin", provenance="pin", catalogued=True)
    ledger.mark_historical(digest, "training_consumed", source_artifact="pin", provenance="trained")
    report = ledger.admit([consumed], batch_id="batch-e", source_artifact="acquire", targets=TINY)
    assert report["unique_admitted_to_eval_reserve"] == 0
    assert report["rejected_existing_identities"]["TRAIN_CONSUMED"] == 1
    scored = _row("brand new phrase")
    scored["model_score"] = 0.9
    with pytest.raises(SystemExit, match="model outcome"):
        ledger.admit([scored], batch_id="batch-f", source_artifact="acquire", targets=TINY)


def test_training_guard_blocks_reserve_and_ignores_historical_overlap():
    ledger = IdentityLedger()
    reserved = _row("held for eval", cls="OBSERVED", lineage="brainrot")
    ledger.admit([reserved], batch_id="batch-g", source_artifact="acquire", targets=TINY)
    with pytest.raises(SystemExit, match="ADMISSION FAIL"):
        assert_training_disjoint_from_reserve([reserved], ledger)
    historical = _row("old train and old holdout")
    digest = ledger.observe_row(historical, source_artifact="pin", provenance="pin", catalogued=True)
    ledger.mark_historical(digest, "training_consumed", source_artifact="pin", provenance="trained")
    ledger.mark_historical(digest, "evaluation_abandoned", source_artifact="select", provenance="abandoned")
    report = assert_training_disjoint_from_reserve([historical], ledger)
    assert report["eval_reserve_training_disjoint"] is True


def test_roundtrip_and_gap_labels(tmp_path):
    ledger = IdentityLedger()
    ledger.admit(
        [_row("only one", cls="OBSERVED", lineage="brainrot")],
        batch_id="batch-h",
        source_artifact="acquire",
        targets=TINY,
    )
    ledger.save(tmp_path)
    loaded = IdentityLedger.load(tmp_path)
    assert loaded.reserve_counts()["classify_observed"] == 1
    blob = (tmp_path / "ledger.json").read_text(encoding="utf-8")
    assert '"text":' not in blob
    gap = acquisition_gap({})
    assert [row["minimum_required"] for row in gap] == ["NOT_COMPUTABLE"] * 4
    assert {row["slice"]: row["planning_target"] for row in gap} == PLANNING_TARGETS
    gate = loaded.select_003_gate(train_hashes=set())
    assert gate["select_003"] == "NOT_DRAFTED"
    assert gate["eligible"] is False


def test_same_batch_duplicate_text_counts_once():
    ledger = IdentityLedger()
    row = _row("batch twin", cls="OBSERVED", lineage="brainrot")
    twin = _row("batch twin", split="val", cls="OBSERVED", lineage="brainrot")
    report = ledger.admit([row, twin], batch_id="batch-i", source_artifact="acquire", targets=TINY)
    assert report["raw_rows"] == 2
    assert report["unique_canonical_text_identities"] == 1
    assert report["unique_admitted_to_eval_reserve"] == 1
    assert report["duplicate_text_rows_not_counted"] == 1
