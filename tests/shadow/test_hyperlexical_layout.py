from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.layout import (
    FAMILIES,
    HIDDEN,
    LAST_TRAINABLE,
    LAST_TRAINABLE_MAX,
    LAYERS,
    describe,
    label_maps,
    resolve_last_trainable,
)
from hyperlexical.loop import freeze_encoder


class _P:
    def __init__(self):
        self.requires_grad = True

    def numel(self):
        return 1


class _Block:
    def __init__(self):
        self._ps = [_P(), _P()]

    def parameters(self):
        return self._ps


class _Enc:
    def __init__(self, n):
        self.layers = [_Block() for _ in range(n)]

    def parameters(self):
        for block in self.layers:
            yield from block.parameters()


def test_layout_shapes(monkeypatch):
    monkeypatch.delenv("HYPERLEX_LAST_TRAINABLE", raising=False)
    maps = label_maps(
        [
            {"roles": ["pos_0", "pos_1"], "fillers": ["a", "b"]},
            {"roles": ["TOKEN"], "fillers": ["c"]},
        ]
    )
    card = describe(maps)
    assert card["hidden"] == HIDDEN == 768
    assert card["layers"] == LAYERS == 22
    assert card["last_trainable"] == LAST_TRAINABLE == 2
    assert card["classify"]["out"] == len(FAMILIES) == 9
    assert card["unbind_role"]["reads"] == "last_hidden_state"
    assert card["unbind_filler"]["reads"] == "last_hidden_state"
    assert "refusal_head" in card["forbidden"]
    assert card["brier"] is None
    assert maps["role_vocab"][0] == "<unk>"
    assert "a" in maps["filler_vocab"]


def test_resolve_last_trainable_default_and_env(monkeypatch):
    monkeypatch.delenv("HYPERLEX_LAST_TRAINABLE", raising=False)
    assert LAST_TRAINABLE == 2
    assert resolve_last_trainable() == 2
    monkeypatch.setenv("HYPERLEX_LAST_TRAINABLE", "4")
    assert resolve_last_trainable() == 4
    monkeypatch.setenv("HYPERLEX_LAST_TRAINABLE", "99")
    assert resolve_last_trainable() == LAST_TRAINABLE_MAX == 8
    assert resolve_last_trainable(layer_count=3) == 3


def test_resolve_last_trainable_rejects_non_positive(monkeypatch):
    monkeypatch.setenv("HYPERLEX_LAST_TRAINABLE", "0")
    with pytest.raises(ValueError, match="positive int"):
        resolve_last_trainable()
    monkeypatch.setenv("HYPERLEX_LAST_TRAINABLE", "nope")
    with pytest.raises(ValueError, match="positive int"):
        resolve_last_trainable()


def test_freeze_encoder_records_effective_last_trainable(monkeypatch):
    monkeypatch.setenv("HYPERLEX_LAST_TRAINABLE", "3")
    enc = _Enc(5)
    n_unfrozen, used = freeze_encoder(enc)
    assert used == 3
    assert n_unfrozen == 6
    flags = [p.requires_grad for block in enc.layers for p in block.parameters()]
    assert flags == [False] * 4 + [True] * 6
