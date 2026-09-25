"""Spec 007 eval/metrics: token/slot F1 beside unbind_exact.

Tiny fixtures only. Does not invent gold. name_gate stays false.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.eval_unbind import run_eval
from hyperlexical.unbind_metrics import (
    mapped_filler,
    mapped_pred,
    null_unbind_secondary,
    summarize_unbind_pairs,
)


def test_exact_match_is_all_ones():
    metrics = summarize_unbind_pairs([(["rizz", "aura"], ["rizz", "aura"])])
    assert metrics["unbind_exact"] == 1.0
    assert metrics["unbind_token_f1"] == 1.0
    assert metrics["unbind_slot_f1"] == 1.0
    assert metrics["unbind_token_precision"] == 1.0
    assert metrics["unbind_token_recall"] == 1.0
    assert metrics["n_unbind_eval"] == 1


def test_one_wrong_filler_of_two():
    metrics = summarize_unbind_pairs([(["rizz", "aura"], ["rizz", "mid"])])
    assert metrics["unbind_exact"] == 0.0
    assert metrics["unbind_slot_f1"] == 0.5
    assert 0.0 < metrics["unbind_token_f1"] < 1.0
    assert metrics["n_unbind_eval"] == 1


def test_permutation_token_f1_high_slot_f1_zero():
    metrics = summarize_unbind_pairs([(["rizz", "aura"], ["aura", "rizz"])])
    assert metrics["unbind_exact"] == 0.0
    assert metrics["unbind_slot_f1"] == 0.0
    assert metrics["unbind_token_f1"] == 1.0


def test_empty_gold_skipped_like_exact():
    metrics = summarize_unbind_pairs([([], ["rizz"]), (["aura"], ["aura"])])
    assert metrics["n_unbind_eval"] == 1
    assert metrics["unbind_exact"] == 1.0
    assert metrics["unbind_token_f1"] == 1.0
    assert metrics["unbind_slot_f1"] == 1.0


def test_empty_series_zeros():
    metrics = summarize_unbind_pairs([])
    assert metrics["n_unbind_eval"] == 0
    assert metrics["unbind_exact"] == 0.0
    assert metrics["unbind_token_f1"] == 0.0
    assert metrics["unbind_slot_f1"] == 0.0


def test_mapped_filler_uses_unk_like_exact():
    maps = {
        "filler_vocab": ["<unk>", "rizz"],
        "filler_of": {"<unk>": 0, "rizz": 1},
    }
    assert mapped_filler(maps, "rizz") == "rizz"
    assert mapped_filler(maps, "missing") == "<unk>"
    assert mapped_pred(maps, 1) == "rizz"
    assert mapped_pred(maps, 99) == "<unk>"
    mapped = summarize_unbind_pairs(
        [([mapped_filler(maps, "missing")], [mapped_pred(maps, 0)])]
    )
    assert mapped["unbind_exact"] == 1.0
    assert mapped["unbind_token_f1"] == 1.0
    assert mapped["unbind_slot_f1"] == 1.0
    # Same already-mapped pair: strict still refuses the <unk> prediction.
    assert mapped["unbind_exact_strict"] == 0.0
    assert mapped["unbind_token_f1_strict"] == 0.0
    assert mapped["unbind_slot_f1_strict"] == 0.0


def test_strict_oov_uses_raw_filler_and_unk_is_miss():
    """Legacy maps OOV gold to <unk> before scoring. Strict does not."""
    maps = {
        "filler_vocab": ["<unk>", "rizz", "missing"],
        "filler_of": {"<unk>": 0, "rizz": 1, "missing": 2},
    }
    raw = "not-in-vocab"
    pred = mapped_pred(maps, 0)
    legacy_gold = mapped_filler(maps, raw)
    metrics = summarize_unbind_pairs(
        [([legacy_gold], [pred])],
        strict_pairs=[([raw], [pred])],
    )
    assert legacy_gold == "<unk>"
    assert pred == "<unk>"
    assert metrics["unbind_exact"] == 1.0
    assert metrics["unbind_token_f1"] == 1.0
    assert metrics["unbind_slot_f1"] == 1.0
    assert metrics["unbind_token_precision"] == 1.0
    assert metrics["unbind_token_recall"] == 1.0
    assert metrics["unbind_exact_strict"] == 0.0
    assert metrics["unbind_token_f1_strict"] == 0.0
    assert metrics["unbind_slot_f1_strict"] == 0.0
    assert metrics["unbind_token_precision_strict"] == 0.0
    assert metrics["unbind_token_recall_strict"] == 0.0

    # In-vocab hit stays a hit on both series.
    hit = summarize_unbind_pairs(
        [(["rizz"], ["rizz"])],
        strict_pairs=[(["rizz"], ["rizz"])],
    )
    assert hit["unbind_exact"] == 1.0
    assert hit["unbind_exact_strict"] == 1.0
    assert hit["unbind_token_f1_strict"] == 1.0
    assert hit["unbind_slot_f1_strict"] == 1.0

    # Strict gold is the raw lowercased string, not the mapped vocab id.
    cased = summarize_unbind_pairs(
        [([mapped_filler(maps, "Missing")], [mapped_pred(maps, 2)])],
        strict_pairs=[(["Missing"], [mapped_pred(maps, 2)])],
    )
    assert mapped_filler(maps, "Missing") == "<unk>"
    assert cased["unbind_exact"] == 0.0
    assert cased["unbind_exact_strict"] == 1.0


def test_operator_card_keeps_legacy_exact_beside_strict():
    from hyperlexical.selection_surface import metric_block

    block = metric_block(
        [(["<unk>"], ["<unk>"])],
        strict_pairs=[(["missing"], ["<unk>"])],
    )
    assert block["unbind_exact"]["value"] == 1.0
    assert block["unbind_token_f1"]["value"] == 1.0
    assert block["unbind_slot_f1"]["value"] == 1.0
    assert block["unbind_exact_strict"]["value"] == 0.0
    assert block["unbind_token_f1_strict"]["value"] == 0.0
    assert block["unbind_slot_f1_strict"]["value"] == 0.0


def test_stub_eval_leaves_f1_null(tmp_path, monkeypatch):
    monkeypatch.delenv("HYPERLEX_E2_TRUNK_FORWARD", raising=False)
    monkeypatch.delenv("HYPERLEX_TRUNK_DIR", raising=False)
    monkeypatch.delenv("HLX_E2_DISJOINT", raising=False)
    monkeypatch.setenv("HYPERLEX_TRAIN_OUT", str(tmp_path / "no-heads"))
    report = run_eval()
    assert report["unbind_token_f1"] is None
    assert report["unbind_slot_f1"] is None
    assert report["unbind_token_precision"] is None
    assert report["unbind_token_recall"] is None
    assert report["unbind_exact_strict"] is None
    assert report["unbind_token_f1_strict"] is None
    assert report["unbind_slot_f1_strict"] is None
    assert report["e2_train_overlap_count"] > 0
    assert "unbind_exact" not in report or report.get("unbind_exact") is None
    assert report.get("name_gate", False) is False
    assert report["brier"] is None
    assert null_unbind_secondary()["unbind_token_f1"] is None
