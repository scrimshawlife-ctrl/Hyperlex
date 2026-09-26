"""Default-off rc4 flags: HLX_SEED and HLX_CLASSIFY_SPLIT_FILE.

Synthetic rows only. No dataset text, ids, or private paths.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classify_split import (  # noqa: E402
    apply_classify_split_file,
    trainval_base_sha256,
)
from hyperlexical.holdout_guard import HoldoutSpec, filter_holdout_rows  # noqa: E402
from hyperlexical.seed_control import apply_training_seed, resolve_training_seed  # noqa: E402
from hyperlexical.selection_surface import row_id  # noqa: E402


def _row(text: str, split: str, *, task: str = "classify", lineage: str = "none") -> dict:
    return {
        "task": task,
        "split": split,
        "role_scheme": "positional",
        "class": "OBSERVED",
        "lineage": lineage,
        "text": text,
    }


def _write_split(path: Path, train: list, val: list, mapping: dict[str, str], *, base: bool = True, schema: str | None = "hyperlex.classify_split_override.v0.1") -> None:
    payload: dict = {"split_by_row_id": mapping}
    if schema is not None:
        payload["schema"] = schema
    if base:
        payload["base_trainval_sha256"] = trainval_base_sha256(train, val)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_split_unset_returns_same_lists(monkeypatch):
    monkeypatch.delenv("HLX_CLASSIFY_SPLIT_FILE", raising=False)
    train = [_row("synthetic row 1", "train"), _row("synthetic row 2", "train")]
    val = [_row("synthetic row 3", "val")]
    before = json.dumps([train, val], sort_keys=True)
    got_tr, got_va, receipt = apply_classify_split_file(train, val)
    assert got_tr is train
    assert got_va is val
    assert receipt is None
    assert json.dumps([train, val], sort_keys=True) == before


def test_split_moves_drops_and_keeps_row_objects(monkeypatch, tmp_path):
    train = [_row("synthetic row 1", "train"), _row("synthetic row 2", "train")]
    val = [_row("synthetic row 3", "val"), _row("synthetic row 4", "val")]
    mapping = {
        row_id(train[0]): "val",
        row_id(train[1]): "drop",
        row_id(val[0]): "train",
        row_id(val[1]): "val",
    }
    path = tmp_path / "split.json"
    _write_split(path, train, val, mapping)
    monkeypatch.setenv("HLX_CLASSIFY_SPLIT_FILE", str(path))
    got_tr, got_va, receipt = apply_classify_split_file(train, val)
    assert got_tr == [val[0]]
    assert got_va == [train[0], val[1]]
    assert got_tr[0] is val[0]
    assert train[0]["split"] == "train"
    assert receipt["n_train_to_val"] == 1
    assert receipt["n_val_to_train"] == 1
    assert receipt["n_dropped_train"] == 1
    assert receipt["n_dropped_val"] == 0
    assert receipt["n_train"] == 1
    assert receipt["n_val"] == 2
    assert len(receipt["file_sha256"]) == 64
    blob = json.dumps(receipt)
    assert "synthetic" not in blob
    for row in train + val:
        assert row_id(row) not in blob


def test_holdout_guard_still_drops_a_row_the_file_puts_in_train(monkeypatch, tmp_path):
    train = [_row("synthetic row 1", "train")]
    held = _row("synthetic row 2", "val")
    mapping = {row_id(train[0]): "train", row_id(held): "train"}
    path = tmp_path / "split.json"
    _write_split(path, train, [held], mapping, base=False)
    monkeypatch.setenv("HLX_CLASSIFY_SPLIT_FILE", str(path))
    got_tr, got_va, _ = apply_classify_split_file(train, [held])
    assert got_va == []
    assert held in got_tr
    spec = HoldoutSpec(frozenset({row_id(held)}), frozenset(), ())
    kept, removed = filter_holdout_rows(got_tr, spec)
    assert removed == 1
    assert kept == [train[0]]


def test_split_fail_closed(monkeypatch, tmp_path):
    train = [_row("synthetic row 1", "train")]
    val = [_row("synthetic row 2", "val")]
    path = tmp_path / "split.json"
    mapping = {row_id(train[0]): "train", row_id(val[0]): "sideways"}
    _write_split(path, train, val, mapping, base=False)
    monkeypatch.setenv("HLX_CLASSIFY_SPLIT_FILE", str(path))
    with pytest.raises(SystemExit, match="REFUSE"):
        apply_classify_split_file(train, val)

    mapping = {row_id(train[0]): "train"}
    _write_split(path, train, val, mapping, base=False)
    with pytest.raises(SystemExit, match="REFUSE"):
        apply_classify_split_file(train, val)

    mapping = {row_id(train[0]): "train", row_id(val[0]): "val", "not-a-row": "drop"}
    _write_split(path, train, val, mapping, base=False)
    with pytest.raises(SystemExit, match="REFUSE"):
        apply_classify_split_file(train, val)

    mapping = {row_id(train[0]): "train", row_id(val[0]): "val"}
    _write_split(path, train, val, mapping, base=True)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["base_trainval_sha256"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SystemExit, match="REFUSE"):
        apply_classify_split_file(train, val)

    path.write_text("{", encoding="utf-8")
    with pytest.raises(SystemExit, match="REFUSE"):
        apply_classify_split_file(train, val)

    monkeypatch.setenv("HLX_CLASSIFY_SPLIT_FILE", str(tmp_path / "missing.json"))
    with pytest.raises(SystemExit, match="REFUSE"):
        apply_classify_split_file(train, val)


def test_split_does_not_touch_unbind_lists(monkeypatch, tmp_path):
    classify_train = [_row("synthetic row 1", "train")]
    unbind = [_row("synthetic unbind row", "train", task="unbind")]
    path = tmp_path / "split.json"
    _write_split(path, classify_train, [], {row_id(classify_train[0]): "drop"}, base=False)
    monkeypatch.setenv("HLX_CLASSIFY_SPLIT_FILE", str(path))
    apply_classify_split_file(classify_train, [])
    assert unbind[0]["task"] == "unbind"
    assert unbind[0]["text"] == "synthetic unbind row"


def test_each_flag_leaves_the_other_unset(monkeypatch, tmp_path):
    train = [_row("synthetic row 1", "train")]
    val = [_row("synthetic row 2", "val")]
    monkeypatch.delenv("HLX_CLASSIFY_SPLIT_FILE", raising=False)
    monkeypatch.setenv("HLX_SEED", "7")
    got_tr, got_va, receipt = apply_classify_split_file(train, val)
    assert got_tr is train
    assert got_va is val
    assert receipt is None
    assert resolve_training_seed() == 7

    monkeypatch.delenv("HLX_SEED", raising=False)
    path = tmp_path / "split.json"
    _write_split(
        path,
        train,
        val,
        {row_id(train[0]): "val", row_id(val[0]): "train"},
        base=False,
    )
    monkeypatch.setenv("HLX_CLASSIFY_SPLIT_FILE", str(path))
    got_tr, got_va, receipt = apply_classify_split_file(train, val)
    assert got_tr == [val[0]]
    assert got_va == [train[0]]
    assert receipt is not None
    assert resolve_training_seed() is None


def test_seed_unset_does_not_touch_rng(monkeypatch):
    torch = pytest.importorskip("torch")
    monkeypatch.delenv("HLX_SEED", raising=False)
    monkeypatch.delenv("HLX_CLASSIFY_SPLIT_FILE", raising=False)

    random.seed(11)
    torch.manual_seed(11)
    py_before = random.getstate()
    torch_before = torch.get_rng_state().clone()
    assert resolve_training_seed() is None
    assert apply_training_seed(torch) is None
    assert random.getstate() == py_before
    assert torch.equal(torch.get_rng_state(), torch_before)


def test_seed_reproducible_and_distinct(monkeypatch):
    torch = pytest.importorskip("torch")
    from torch import nn

    monkeypatch.delenv("HLX_CLASSIFY_SPLIT_FILE", raising=False)

    def first_weight(seed: str):
        monkeypatch.setenv("HLX_SEED", seed)
        try:
            receipt = apply_training_seed(torch)
            layer = nn.Linear(4, 2)
            return receipt, layer.weight.detach().clone()
        finally:
            torch.use_deterministic_algorithms(False)

    receipt_a, weight_a = first_weight("7")
    _, weight_b = first_weight("7")
    receipt_c, weight_c = first_weight("8")
    assert receipt_a["seed"] == 7
    assert receipt_a["deterministic_algorithms"] is True
    assert torch.equal(weight_a, weight_b)
    assert not torch.equal(weight_a, weight_c)
    blob = json.dumps(receipt_a)
    assert "synthetic" not in blob


def test_seed_rejects_non_integers(monkeypatch):
    monkeypatch.setenv("HLX_SEED", "nope")
    with pytest.raises(SystemExit, match="REFUSE"):
        resolve_training_seed()
    monkeypatch.setenv("HLX_SEED", "1.5")
    with pytest.raises(SystemExit, match="REFUSE"):
        resolve_training_seed()
