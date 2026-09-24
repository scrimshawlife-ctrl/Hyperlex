"""Force-train authorized OBSERVED val exacts → train (accept-style)."""

from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.loop import prepare_unbind_splits
from hyperlexical.unbind_recipe import (
    apply_unbind_force_train,
    load_force_train_keys,
    resolve_unbind_force_train_path,
)


def _unbind_row(text, fillers, *, cls="OBSERVED", split="train", scheme="positional"):
    roles = (
        [f"pos_{i}" for i in range(len(fillers))]
        if scheme == "positional"
        else ["TOKEN", "SLOT", "MARKER"][: len(fillers)]
    )
    return {
        "text": text,
        "fillers": fillers,
        "roles": roles,
        "role_scheme": scheme,
        "class": cls,
        "split": split,
        "task": "unbind",
        "lineage": "brainrot-aura",
    }


def test_force_train_default_identity(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_FORCE_TRAIN_PATH", raising=False)
    assert resolve_unbind_force_train_path() == ""
    assert load_force_train_keys() == frozenset()
    train = [_unbind_row("train a", ["a", "b"], split="train")]
    val = [_unbind_row("val a", ["c", "d"], split="val")]
    t2, v2, stats = apply_unbind_force_train(train, val)
    assert t2 == train
    assert v2 == val
    assert stats["n_unbind_force_train"] == 0


def test_force_train_moves_observed_val_only(monkeypatch, tmp_path):
    path = tmp_path / "force_train.jsonl"
    path.write_text(
        json.dumps({"text": "val obs", "role_scheme": "positional"}) + "\n"
        + json.dumps({"text": "val inf", "role_scheme": "positional"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HYPERLEX_UNBIND_FORCE_TRAIN_PATH", str(path))
    monkeypatch.delenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", raising=False)
    rows = [
        _unbind_row("train obs", ["aped", "in"], split="train"),
        _unbind_row("val obs", ["quiet", "quitter"], split="val"),
        _unbind_row("val inf", ["aura", "farm"], cls="INFERRED", split="val"),
        _unbind_row("val other", ["dark", "flow"], split="val"),
    ]
    train, val, stats = prepare_unbind_splits(rows)
    assert [r["text"] for r in val] == ["val inf", "val other"]
    assert any(r["text"] == "val obs" and r["split"] == "train" for r in train)
    assert stats["n_unbind_force_train"] == 1
    assert stats["n_unbind_force_train_keys"] == 2
    assert stats["unbind_force_train_path"] == "force_train.jsonl"


def test_force_train_fail_closed_missing(monkeypatch):
    monkeypatch.setenv("HYPERLEX_UNBIND_FORCE_TRAIN_PATH", "/no/such/force_train.jsonl")
    with pytest.raises(ValueError, match="not a file"):
        load_force_train_keys()
