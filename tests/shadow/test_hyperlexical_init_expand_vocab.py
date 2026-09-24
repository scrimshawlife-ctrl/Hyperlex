"""HYPERLEX_INIT_EXPAND_VOCAB warm-load remap."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

torch = pytest.importorskip("torch")
from torch import nn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.loop import warm_load_checkpoint


class _Enc:
    """Minimal encoder stand-in for apply_encoder_trainable."""

    def __init__(self):
        self._sd = {"layers.20.weight": torch.zeros(2)}

    def state_dict(self):
        return dict(self._sd)

    def load_state_dict(self, state, strict=True):
        for k, v in state.items():
            if k in self._sd:
                self._sd[k] = v
        return type("R", (), {"missing_keys": [], "unexpected_keys": []})()

    def named_parameters(self):
        return []


def _write_heads_seed(tmp: Path, roles: list[str], fillers: list[str]):
    hidden = 4
    classify = nn.Linear(hidden, 3)
    role_head = nn.Linear(hidden, len(roles))
    filler_head = nn.Linear(hidden, len(fillers))
    with torch.no_grad():
        for i in range(len(roles)):
            role_head.weight[i].fill_(10.0 + i)
            role_head.bias[i].fill_(100.0 + i)
        for i in range(len(fillers)):
            filler_head.weight[i].fill_(20.0 + i)
            filler_head.bias[i].fill_(200.0 + i)
    blob = {
        "classify": {k: v.detach().clone() for k, v in classify.state_dict().items()},
        "role_head": {k: v.detach().clone() for k, v in role_head.state_dict().items()},
        "filler_head": {k: v.detach().clone() for k, v in filler_head.state_dict().items()},
        "encoder": {},
    }
    torch.save(blob, tmp / "heads.pt")
    (tmp / "config.json").write_text(
        json.dumps({"role_vocab": roles, "filler_vocab": fillers}) + "\n"
    )
    return classify, role_head, filler_head


def test_warm_load_fail_closed_on_vocab_mismatch(tmp_path):
    init_roles = ["<unk>", "pos_0", "pos_1"]
    init_fillers = ["<unk>", "a", "b"]
    _write_heads_seed(tmp_path, init_roles, init_fillers)
    maps = {
        "role_vocab": ["<unk>", "pos_0", "pos_1", "pos_2"],
        "filler_vocab": ["<unk>", "a", "b", "c"],
    }
    classify = nn.Linear(4, 3)
    role_head = nn.Linear(4, 4)
    filler_head = nn.Linear(4, 4)
    with pytest.raises(ValueError, match="role_vocab mismatch"):
        warm_load_checkpoint(
            _Enc(), classify, role_head, filler_head, maps, tmp_path, expand_vocab=False
        )


def test_warm_load_expand_remaps_shared_rows_keeps_new_init(tmp_path):
    init_roles = ["<unk>", "TOKEN", "pos_0", "pos_1"]
    init_fillers = ["<unk>", "alpha", "beta"]
    _, init_role, init_filler = _write_heads_seed(tmp_path, init_roles, init_fillers)
    cur_roles = ["<unk>", "TOKEN", "pos_0", "pos_1", "pos_2"]
    # filler order differs + new label (name-remap, not index-pad)
    cur_fillers = ["<unk>", "beta", "alpha", "gamma"]
    maps = {"role_vocab": cur_roles, "filler_vocab": cur_fillers}
    classify = nn.Linear(4, 3)
    role_head = nn.Linear(4, len(cur_roles))
    filler_head = nn.Linear(4, len(cur_fillers))
    with torch.no_grad():
        role_head.weight.fill_(-1.0)
        role_head.bias.fill_(-1.0)
        filler_head.weight.fill_(-1.0)
        filler_head.bias.fill_(-1.0)
        new_role_row = role_head.weight[-1].clone()
        new_fill_row = filler_head.weight[cur_fillers.index("gamma")].clone()

    receipt = warm_load_checkpoint(
        _Enc(), classify, role_head, filler_head, maps, tmp_path, expand_vocab=True
    )
    assert receipt["expand_vocab"] is True
    assert receipt["role"]["mapped"] == 4
    assert receipt["filler"]["mapped"] == 3
    assert receipt["filler"]["new_current_rows"] == 1

    for lab in init_roles:
        ii = init_roles.index(lab)
        ci = cur_roles.index(lab)
        assert torch.allclose(role_head.weight[ci], init_role.weight[ii])
        assert torch.allclose(role_head.bias[ci], init_role.bias[ii])
    assert torch.allclose(role_head.weight[-1], new_role_row)

    for lab in init_fillers:
        ii = init_fillers.index(lab)
        ci = cur_fillers.index(lab)
        assert torch.allclose(filler_head.weight[ci], init_filler.weight[ii])
        assert torch.allclose(filler_head.bias[ci], init_filler.bias[ii])
    gi = cur_fillers.index("gamma")
    assert torch.allclose(filler_head.weight[gi], new_fill_row)


def test_warm_load_expand_exact_match_still_strict(tmp_path):
    roles = ["<unk>", "pos_0"]
    fillers = ["<unk>", "x"]
    _write_heads_seed(tmp_path, roles, fillers)
    maps = {"role_vocab": roles, "filler_vocab": fillers}
    classify = nn.Linear(4, 3)
    role_head = nn.Linear(4, 2)
    filler_head = nn.Linear(4, 2)
    receipt = warm_load_checkpoint(
        _Enc(), classify, role_head, filler_head, maps, tmp_path, expand_vocab=True
    )
    assert receipt["vocab_match"] is True
    assert receipt["expand_vocab"] is False
