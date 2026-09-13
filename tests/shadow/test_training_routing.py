"""Synthetic routing controls; no GPU execution.

Provenance: Notion Sprint 001 Hub NOT_COMPUTABLE + Loop 805 Slice N/A
+ Hash: b3eee725054c1ed1dae16fad3464af005edad0cc (base).
"""
import copy
from pathlib import Path

import pytest

from scripts.shadow.hyperlexical import loop
from scripts.shadow.hyperlexical.training_routing import route_rows


def row(task="classify+unbind", split="train", **extra):
    return {"task": task, "split": split, "text": "fixture", "lineage": "none",
            "fillers": ["fixture"], "roles": ["pos_0"], **extra}


def test_combined_accounted_once_assigned_twice():
    rows = [row(), row(split="val"), row(split="test")]
    before = copy.deepcopy(rows)
    selected, stats = route_rows(rows)
    assert rows == before
    assert selected["classify"]["train"] == [rows[0]]
    assert selected["unbind"]["val"] == [rows[1]]
    assert stats["row_outcomes"] == {"selected": 2, "reserved_test": 1}
    assert sum(stats["task_assignments"].values()) == 4
    assert stats["legacy_declared_rows"] == 3


@pytest.mark.parametrize("family,structure", [(False, False), (True, False), (False, True), (True, True)])
def test_independent_masks(family, structure):
    rows = [row(loss_masks={"family": family, "structure": structure})]
    selected, stats = route_rows(rows)
    assert len(selected["classify"]["train"]) == int(family)
    assert len(selected["unbind"]["train"]) == int(structure)
    assert stats["explicit_mask_rows"] == 1
    assert stats["input_rows"] == sum(stats["row_outcomes"].values())


@pytest.mark.parametrize("bad", [
    {"task": "typo"}, {"split": "dev"}, {"loss_masks": None},
    {"loss_masks": {}}, {"loss_masks": {"family": True}},
    {"loss_masks": {"family": 1, "structure": False}},
    {"loss_masks": {"family": True, "structure": False, "stage": True}},
    {"task": "classify", "loss_masks": {"family": True, "structure": True}},
])
def test_rejects_ambiguous_declarations(bad):
    with pytest.raises(ValueError):
        route_rows([row(**bad)])


def test_order_and_hash():
    rows = [row(text="a"), row(text="b")]
    assert route_rows(rows)[0]["classify"]["train"] == rows
    assert route_rows(rows)[1] == route_rows(copy.deepcopy(rows))[1]
    assert route_rows(rows)[1]["input_sha256"] != route_rows(rows[::-1])[1]["input_sha256"]


def test_recipe_receives_only_selected_unbind(monkeypatch):
    seen = []
    monkeypatch.setattr(loop, "shape_unbind_train", lambda rows: (seen.extend(rows) or rows, {}))
    rows = [row(), row(loss_masks={"family": True, "structure": False}), row(split="val")]
    train, val, _ = loop.prepare_unbind_splits(rows)
    assert seen == train == [rows[0]]
    assert val == [rows[2]]


def test_run_boundary_rejects_before_export_or_model(monkeypatch, tmp_path):
    monkeypatch.setattr(loop, "export_dataset", lambda *a, **k: {"rows": [row(task="unknown")]})
    def forbidden(*a, **k):
        pytest.fail("must not write or load model")
    monkeypatch.setattr(loop, "write_export", forbidden)
    monkeypatch.setattr(loop, "_require_local_model", forbidden)
    with pytest.raises(ValueError):
        loop.run_loop(Path("unused"), tmp_path)


def test_run_masked_classify_fails_minimum_before_model(monkeypatch, tmp_path):
    rows = [row(loss_masks={"family": False, "structure": True}) for _ in range(8)]
    monkeypatch.setattr(loop, "export_dataset", lambda *a, **k: {"rows": rows})
    monkeypatch.setattr(loop, "write_export", lambda *a, **k: None)
    monkeypatch.setattr(loop, "shape_unbind_train", lambda rows: (rows, {}))
    with pytest.raises(RuntimeError, match="not enough classify"):
        loop.run_loop(Path("unused"), tmp_path)


@pytest.mark.parametrize("extra", [
    {"fillers": ["general"]}, {"fillers": []}, {"fillers": None},
    {"roles": []}, {"roles": [""]}, {"fillers": [1]},
    {"text": "fixture fixture"}, {"fillers": ["fixture", "fixture"], "roles": ["a", "b"]},
])
@pytest.mark.parametrize("split", ["train", "val"])
def test_unsafe_combined_unbind_excluded_but_classify_retained(extra, split):
    r = row(split=split, **extra)
    selected, stats = route_rows([r])
    assert selected["unbind"][split] == []
    assert selected["classify"][split] == [r]
    assert stats["combined_unbind_suppressed"] == 1


def test_invalid_combined_with_classify_masked_has_explicit_exclusion():
    r = row(fillers=["general"], loss_masks={"family": False, "structure": True})
    selected, stats = route_rows([r])
    assert not selected["unbind"]["train"]
    assert not selected["classify"]["train"]
    assert stats["row_outcomes"] == {"invalid_combined_unbind_targets": 1}
