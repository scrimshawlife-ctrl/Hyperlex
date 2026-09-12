import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.eval_forward import (
    apply_encoder_trainable,
    encoder_forward_note,
    _load_maps,
)
from hyperlexical.save_pretrained import (
    collect_encoder_trainable,
    flatten_weight_tensors,
    split_weight_tensors,
)


class _FakeEncoder:
    def __init__(self):
        self._sd = {
            "layers.20.weight": [1.0],
            "layers.21.weight": [2.0],
            "layers.0.weight": [0.0],
        }

    def state_dict(self):
        return dict(self._sd)

    def load_state_dict(self, state, strict=True):
        unexpected = [k for k in state if k not in self._sd]
        for key, value in state.items():
            if key in self._sd:
                self._sd[key] = value
        return type("Result", (), {"missing_keys": [], "unexpected_keys": unexpected})()


def test_flatten_includes_encoder_keys_from_fake_state():
    state = {
        "classify": {"weight": 1, "bias": 2},
        "role_head": {"weight": 3},
        "filler_head": {"weight": 4, "bias": 5},
        "encoder": {"layers.20.attn.Wqkv.weight": 9},
    }
    flat = flatten_weight_tensors(state)
    encoder_keys = [k for k in flat if k.startswith("encoder.")]
    assert encoder_keys
    assert "encoder.layers.20.attn.Wqkv.weight" in flat
    assert flat["filler_head.weight"] == 4
    assert flat["classify.weight"] == 1
    split = split_weight_tensors(flat)
    assert "encoder.layers.20.attn.Wqkv.weight" in split["encoder"]
    assert split["filler_head"]["weight"] == 4


def test_flatten_prefixes_bare_encoder_keys():
    flat = flatten_weight_tensors({"encoder": {"layers.21.weight": 7}, "filler_head": {}})
    assert flat["encoder.layers.21.weight"] == 7


def test_collect_encoder_trainable_requires_grad_only():
    class _Param:
        def __init__(self, value, requires_grad):
            self.requires_grad = requires_grad
            self._value = value

        def detach(self):
            return self

        def cpu(self):
            return self

        def contiguous(self):
            return self._value

    class _Enc:
        def named_parameters(self):
            return [
                ("layers.20.weight", _Param(9, True)),
                ("layers.0.weight", _Param(1, False)),
            ]

    out = collect_encoder_trainable(_Enc())
    assert out == {"encoder.layers.20.weight": 9}


def test_apply_encoder_trainable_updates_matching_keys():
    encoder = _FakeEncoder()
    info = apply_encoder_trainable(
        encoder,
        {
            "encoder.layers.20.weight": [9.0],
            "encoder.nope.weight": [8.0],
        },
    )
    sd = encoder.state_dict()
    assert sd["layers.20.weight"] == [9.0]
    assert sd["layers.21.weight"] == [2.0]
    assert sd["layers.0.weight"] == [0.0]
    assert info["loaded"] == 1
    assert "encoder.nope.weight" in info["unexpected"]


def test_apply_encoder_trainable_empty_is_noop():
    encoder = _FakeEncoder()
    info = apply_encoder_trainable(encoder, {})
    assert info["loaded"] == 0
    assert encoder.state_dict()["layers.20.weight"] == [1.0]


def test_missing_encoder_keys_still_split_heads_and_note_divergence():
    split = split_weight_tensors(
        {
            "classify.weight": 1,
            "role_head.weight": 2,
            "filler_head.weight": 3,
            "filler_head.bias": 4,
        }
    )
    assert split["encoder"] == {}
    assert split["filler_head"]["weight"] == 3
    note = encoder_forward_note(loaded=0, present=0)
    assert "may diverge" in note


def test_load_maps_from_config_filler_vocab(tmp_path):
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "role_vocab": ["<unk>", "pos_0"],
                "filler_vocab": ["<unk>", "rizz"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    maps = _load_maps(tmp_path, None)
    assert maps["filler_vocab"] == ["<unk>", "rizz"]
    assert maps["filler_of"]["rizz"] == 1
    assert maps["role_of"]["pos_0"] == 1
