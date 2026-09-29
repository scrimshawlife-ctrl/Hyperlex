"""SELECT-006 zero-row expansion. No optimizer and no training step."""

from __future__ import annotations

import ast
from pathlib import Path
import sys

import pytest

torch = pytest.importorskip("torch")
from torch import nn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.loop import run_loop
from hyperlexical.zero_init_loader import (
    DIMENSION_MISMATCH,
    DUPLICATE_NAME,
    SOURCE_MISMATCH,
    ZeroInitLoaderError,
    expand_named_linear,
    expanded_loader_hashes,
)


def _linear(rows: int, hidden: int = 4) -> nn.Linear:
    module = nn.Linear(hidden, rows)
    with torch.no_grad():
        module.weight.fill_(3.0)
        module.bias.fill_(4.0)
    return module


def _state(rows: int, hidden: int = 4):
    weight = torch.empty(rows, hidden)
    bias = torch.empty(rows)
    for index in range(rows):
        weight[index].fill_(10.0 + index)
        bias[index].fill_(100.0 + index)
    return {"weight": weight, "bias": bias}


def test_new_rows_are_exact_zero_and_removed_rows_are_omitted():
    source = ["<unk>", "alpha", "beta"]
    target = ["<unk>", "beta", "gamma"]
    module = _linear(len(target))
    receipt = expand_named_linear(module, _state(len(source)), source, target, "filler_head")
    assert receipt["mapped"] == 2
    assert receipt["new_current_rows"] == 1
    assert receipt["skipped_init_only"] == 1
    assert receipt["new_names"] == ["gamma"]
    assert torch.equal(module.weight[0], torch.full((4,), 10.0))
    assert torch.equal(module.bias[1], torch.full((), 102.0))
    assert torch.equal(module.weight[2], torch.zeros(4))
    assert torch.equal(module.bias[2], torch.zeros(()))


def test_duplicate_name_fails_closed():
    module = _linear(2)
    with pytest.raises(ZeroInitLoaderError, match=DUPLICATE_NAME):
        expand_named_linear(module, _state(3), ["<unk>", "a", "a"], ["<unk>", "a"], "role_head")


def test_dimension_and_source_count_fail_closed():
    module = _linear(2)
    state = _state(2)
    state["weight"] = torch.zeros(2, 5)
    with pytest.raises(ZeroInitLoaderError, match=DIMENSION_MISMATCH):
        expand_named_linear(module, state, ["<unk>", "a"], ["<unk>", "a"], "role_head")
    short = _state(1)
    with pytest.raises(ZeroInitLoaderError, match=SOURCE_MISMATCH):
        expand_named_linear(module, short, ["<unk>", "a"], ["<unk>", "b"], "role_head")


def test_repeated_expansion_is_identical():
    source = ["<unk>", "pos_0"]
    target = ["<unk>", "pos_0", "pos_6"]
    hashes = []
    for seed in (1, 99):
        torch.manual_seed(seed)
        module = nn.Linear(4, len(target))
        expand_named_linear(module, _state(len(source)), source, target, "role_head")
        hashes.append(expanded_loader_hashes(module, module, {"role_vocab": target, "filler_vocab": target}))
    assert hashes[0] == hashes[1]
    assert torch.equal(module.weight[2], torch.zeros(4))


def test_training_loop_reaches_loader_before_optimizer():
    src = Path(run_loop.__code__.co_filename).read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_loop")
    warm_line = stop_line = adam_line = None
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if name == "warm_load_checkpoint":
            warm_line = node.lineno
        if name == "pre_optimizer_stop_requested":
            stop_line = node.lineno
        if name == "AdamW":
            adam_line = node.lineno
    assert warm_line is not None and stop_line is not None and adam_line is not None
    assert warm_line < stop_line < adam_line
    assert "select006_training_init_guard" in src
