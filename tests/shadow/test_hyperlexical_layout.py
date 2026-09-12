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
from hyperlexical.loop import (
    UNBIND_EVERY_N_DEFAULT,
    UNBIND_LOSS_WEIGHT_DEFAULT,
    freeze_encoder,
    resolve_unbind_every_n,
    resolve_unbind_loss_weight,
    should_interleave_unbind,
)


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


def test_resolve_unbind_loss_weight_default_and_env(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_LOSS_WEIGHT", raising=False)
    assert UNBIND_LOSS_WEIGHT_DEFAULT == 1.0
    assert resolve_unbind_loss_weight() == 1.0
    assert resolve_unbind_loss_weight("") == 1.0
    assert resolve_unbind_loss_weight("  ") == 1.0
    monkeypatch.setenv("HYPERLEX_UNBIND_LOSS_WEIGHT", "2.5")
    assert resolve_unbind_loss_weight() == 2.5
    assert resolve_unbind_loss_weight("0") == 0.0
    assert resolve_unbind_loss_weight(3) == 3.0


def test_resolve_unbind_loss_weight_rejects_invalid(monkeypatch):
    monkeypatch.setenv("HYPERLEX_UNBIND_LOSS_WEIGHT", "-1")
    with pytest.raises(ValueError, match="finite number >= 0"):
        resolve_unbind_loss_weight()
    monkeypatch.setenv("HYPERLEX_UNBIND_LOSS_WEIGHT", "nope")
    with pytest.raises(ValueError, match="finite number >= 0"):
        resolve_unbind_loss_weight()
    monkeypatch.setenv("HYPERLEX_UNBIND_LOSS_WEIGHT", "nan")
    with pytest.raises(ValueError, match="finite number >= 0"):
        resolve_unbind_loss_weight()
    monkeypatch.setenv("HYPERLEX_UNBIND_LOSS_WEIGHT", "inf")
    with pytest.raises(ValueError, match="finite number >= 0"):
        resolve_unbind_loss_weight()


def test_resolve_unbind_every_n_default_and_env(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_EVERY_N", raising=False)
    assert UNBIND_EVERY_N_DEFAULT == 1
    assert resolve_unbind_every_n() == 1
    assert resolve_unbind_every_n("") == 1
    monkeypatch.setenv("HYPERLEX_UNBIND_EVERY_N", "4")
    assert resolve_unbind_every_n() == 4
    assert resolve_unbind_every_n(2) == 2


def test_resolve_unbind_every_n_rejects_non_positive(monkeypatch):
    monkeypatch.setenv("HYPERLEX_UNBIND_EVERY_N", "0")
    with pytest.raises(ValueError, match="positive int"):
        resolve_unbind_every_n()
    monkeypatch.setenv("HYPERLEX_UNBIND_EVERY_N", "nope")
    with pytest.raises(ValueError, match="positive int"):
        resolve_unbind_every_n()


def test_should_interleave_unbind_preserves_default_schedule():
    assert should_interleave_unbind(0, 1) is False
    assert should_interleave_unbind(7, 1) is False
    assert [i for i in range(8) if should_interleave_unbind(i, 4)] == [3, 7]
