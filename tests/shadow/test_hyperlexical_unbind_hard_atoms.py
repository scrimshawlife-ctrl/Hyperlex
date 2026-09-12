"""Spec 007 data/recipe PR #5: targeted OBSERVED hard-atom upsample.

Default 1 / unset path is identity. Extra copies are already-OBSERVED
train unbind rows only. INFERRED is never promoted. Missing path fails
closed. Operator JSONL is env-path only — not SoT gold.
"""

from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.export import export_dataset
from hyperlexical.loop import prepare_unbind_splits
from hyperlexical.unbind_recipe import (
    UNBIND_HARD_UPSAMPLE_DEFAULT,
    hard_atoms_receipt_path,
    load_hard_atom_texts,
    resolve_unbind_hard_atoms_path,
    resolve_unbind_hard_upsample,
    shape_unbind_train,
    unbind_row_matches_hard_atoms,
)


def _unbind_row(
    text,
    fillers,
    *,
    cls="OBSERVED",
    split="train",
    role_scheme="positional",
    roles=None,
):
    fills = list(fillers)
    if role_scheme == "type_slot":
        display = " ".join(f"TOKEN:{tok}" for tok in fills)
        role_list = ["TOKEN"] * len(fills)
    else:
        display = text
        role_list = list(roles) if roles is not None else [f"pos_{i}" for i in range(len(fills))]
    return {
        "text": display,
        "split": split,
        "lineage": "brainrot-aura",
        "typology": ["compression"],
        "stage": "circulating",
        "roles": role_list,
        "fillers": fills,
        "role_scheme": role_scheme,
        "task": "unbind",
        "provenance": "test:unbind",
        "class": cls,
        "license": "MIT-examples",
    }


def _write_atoms(path: Path, texts: list[str]) -> Path:
    path.write_text("".join(json.dumps({"text": t}) + "\n" for t in texts), encoding="utf-8")
    return path


def _clear_hard_env(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_INFERRED_CAP", raising=False)


def test_resolve_hard_upsample_default_identity(monkeypatch):
    _clear_hard_env(monkeypatch)
    assert UNBIND_HARD_UPSAMPLE_DEFAULT == 1
    assert resolve_unbind_hard_upsample() == 1
    assert resolve_unbind_hard_upsample("") == 1
    assert resolve_unbind_hard_upsample("  ") == 1
    assert resolve_unbind_hard_atoms_path() == ""
    assert resolve_unbind_hard_atoms_path("  ") == ""
    assert hard_atoms_receipt_path("") == ""
    assert hard_atoms_receipt_path("/home/morpheus/hlx/hard_atoms_train.jsonl") == (
        "hard_atoms_train.jsonl"
    )
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", "4")
    assert resolve_unbind_hard_upsample() == 4
    assert resolve_unbind_hard_upsample(3) == 3


def test_resolve_hard_upsample_reject_invalid(monkeypatch):
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", "0")
    with pytest.raises(ValueError, match="int >= 1"):
        resolve_unbind_hard_upsample()
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", "nope")
    with pytest.raises(ValueError, match="int >= 1"):
        resolve_unbind_hard_upsample()
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", "-2")
    with pytest.raises(ValueError, match="int >= 1"):
        resolve_unbind_hard_upsample()


def test_shape_defaults_no_path_no_extra(monkeypatch):
    _clear_hard_env(monkeypatch)
    rows = [
        _unbind_row("obs a", ["aped"], cls="OBSERVED"),
        _unbind_row("inf a", ["aura"], cls="INFERRED"),
    ]
    shaped, stats = shape_unbind_train(rows)
    assert stats["unbind_hard_upsample"] == 1
    assert stats["unbind_hard_atoms_path"] == ""
    assert stats["n_unbind_hard_atoms_matched"] == 0
    assert stats["n_unbind_hard_extra_copies"] == 0
    assert [r["text"] for r in shaped] == [r["text"] for r in rows]
    assert stats["n_train_unbind"] == 2


def test_shape_upsample_1_with_path_is_identity(monkeypatch, tmp_path):
    _clear_hard_env(monkeypatch)
    atoms = _write_atoms(tmp_path / "hard_atoms_train.jsonl", ["obs a", "missing phrase"])
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", str(atoms))
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", "1")
    rows = [
        _unbind_row("obs a", ["aped"], cls="OBSERVED"),
        _unbind_row("inf a", ["aura"], cls="INFERRED"),
    ]
    shaped, stats = shape_unbind_train(rows)
    assert stats["unbind_hard_upsample"] == 1
    assert stats["unbind_hard_atoms_path"] == "hard_atoms_train.jsonl"
    assert stats["n_unbind_hard_atoms_matched"] == 1
    assert stats["n_unbind_hard_extra_copies"] == 0
    assert [r["text"] for r in shaped] == [r["text"] for r in rows]


def test_shape_extra_copies_matched_observed_only(monkeypatch, tmp_path):
    _clear_hard_env(monkeypatch)
    atoms = _write_atoms(
        tmp_path / "hard_atoms_train.jsonl",
        ["obs hard", "unmatched phrase", "INF ONLY"],
    )
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", str(atoms))
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", "3")
    rows = [
        _unbind_row("obs hard", ["aped"], cls="OBSERVED"),
        _unbind_row("obs other", ["rizz"], cls="OBSERVED"),
        _unbind_row("INF ONLY", ["aura"], cls="INFERRED"),
    ]
    shaped, stats = shape_unbind_train(rows)
    texts = [r["text"] for r in shaped]
    assert texts.count("obs hard") == 1 + (3 - 1)
    assert texts.count("obs other") == 1
    assert texts.count("INF ONLY") == 1
    assert stats["n_unbind_observed"] == 2
    assert stats["n_unbind_inferred"] == 1
    assert stats["n_unbind_hard_atoms_matched"] == 1
    assert stats["n_unbind_hard_extra_copies"] == 2
    assert stats["n_train_unbind"] == 5
    inferred = [r for r in shaped if r["text"] == "INF ONLY"]
    assert inferred and all(r["class"] == "INFERRED" for r in inferred)
    assert all(r["class"] == "OBSERVED" for r in shaped if r["text"] == "obs hard")


def test_shape_unmatched_and_type_slot_atom_text(monkeypatch, tmp_path):
    _clear_hard_env(monkeypatch)
    atoms = _write_atoms(tmp_path / "hard.jsonl", ["quiet quitter"])
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", str(atoms))
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", "2")
    rows = [
        _unbind_row("quiet quitter", ["quiet", "quitter"], cls="OBSERVED"),
        _unbind_row(
            "quiet quitter",
            ["quiet", "quitter"],
            cls="OBSERVED",
            role_scheme="type_slot",
        ),
        _unbind_row("no match", ["rizz"], cls="OBSERVED"),
    ]
    assert unbind_row_matches_hard_atoms(rows[0], {"quiet quitter"})
    assert unbind_row_matches_hard_atoms(rows[1], {"quiet quitter"})
    assert not unbind_row_matches_hard_atoms(rows[2], {"quiet quitter"})
    shaped, stats = shape_unbind_train(rows)
    assert stats["n_unbind_hard_atoms_matched"] == 1
    assert stats["n_unbind_hard_extra_copies"] == 2
    type_slot = [r for r in shaped if r["role_scheme"] == "type_slot"]
    assert len(type_slot) == 2
    assert all(r["class"] == "OBSERVED" for r in type_slot)
    assert [r["text"] for r in shaped].count("no match") == 1


def test_shape_does_not_invent_missing_hard_atoms(monkeypatch, tmp_path):
    _clear_hard_env(monkeypatch)
    atoms = _write_atoms(tmp_path / "hard.jsonl", ["brand new settled atom xyz"])
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", str(atoms))
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", "4")
    rows = [_unbind_row("obs a", ["aped"], cls="OBSERVED")]
    shaped, stats = shape_unbind_train(rows)
    assert stats["n_unbind_hard_atoms_matched"] == 0
    assert stats["n_unbind_hard_extra_copies"] == 0
    assert [r["text"] for r in shaped] == ["obs a"]


def test_shape_composes_after_observed_upsample(monkeypatch, tmp_path):
    _clear_hard_env(monkeypatch)
    atoms = _write_atoms(tmp_path / "hard.jsonl", ["obs hard"])
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", str(atoms))
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", "3")
    monkeypatch.setenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", "2")
    rows = [
        _unbind_row("obs hard", ["aped"], cls="OBSERVED"),
        _unbind_row("inf a", ["aura"], cls="INFERRED"),
    ]
    shaped, stats = shape_unbind_train(rows)
    texts = [r["text"] for r in shaped]
    assert texts.count("obs hard") == 2 + (3 - 1)
    assert texts.count("inf a") == 1
    assert stats["unbind_observed_upsample"] == 2
    assert stats["n_unbind_hard_extra_copies"] == 2


def test_prepare_unbind_splits_hard_atoms_leave_val(monkeypatch, tmp_path):
    _clear_hard_env(monkeypatch)
    atoms = _write_atoms(tmp_path / "hard.jsonl", ["train obs", "val obs"])
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", str(atoms))
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", "3")
    rows = [
        _unbind_row("train obs", ["aped"], cls="OBSERVED", split="train"),
        _unbind_row("train inf", ["rizz"], cls="INFERRED", split="train"),
        _unbind_row("val obs", ["aping"], cls="OBSERVED", split="val"),
    ]
    train, val, stats = prepare_unbind_splits(rows)
    assert [r["text"] for r in val] == ["val obs"]
    assert [r["text"] for r in train].count("train obs") == 3
    assert [r["text"] for r in train].count("val obs") == 0
    assert stats["n_unbind_hard_atoms_matched"] == 1
    assert stats["n_unbind_hard_extra_copies"] == 2


def test_load_hard_atoms_fail_closed(monkeypatch, tmp_path):
    _clear_hard_env(monkeypatch)
    missing = tmp_path / "missing.jsonl"
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", str(missing))
    with pytest.raises(ValueError, match="is not a file"):
        load_hard_atom_texts()
    with pytest.raises(ValueError, match="is not a file"):
        shape_unbind_train([_unbind_row("obs a", ["aped"])])

    bad_json = tmp_path / "bad.jsonl"
    bad_json.write_text("{not json\n", encoding="utf-8")
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", str(bad_json))
    with pytest.raises(ValueError, match="not valid JSON"):
        load_hard_atom_texts()

    no_text = tmp_path / "notext.jsonl"
    no_text.write_text(json.dumps({"phrase": "obs a"}) + "\n", encoding="utf-8")
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", str(no_text))
    with pytest.raises(ValueError, match="missing required field 'text'"):
        load_hard_atom_texts()

    empty_text = tmp_path / "empty.jsonl"
    empty_text.write_text(json.dumps({"text": "   "}) + "\n", encoding="utf-8")
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", str(empty_text))
    with pytest.raises(ValueError, match="empty text field"):
        load_hard_atom_texts()

    not_obj = tmp_path / "list.jsonl"
    not_obj.write_text(json.dumps(["obs a"]) + "\n", encoding="utf-8")
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", str(not_obj))
    with pytest.raises(ValueError, match="JSON object"):
        load_hard_atom_texts()

    not_str = tmp_path / "num.jsonl"
    not_str.write_text(json.dumps({"text": 12}) + "\n", encoding="utf-8")
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", str(not_str))
    with pytest.raises(ValueError, match="must be a string"):
        load_hard_atom_texts()


def test_export_sot_unchanged_when_hard_env_set(monkeypatch, tmp_path):
    _clear_hard_env(monkeypatch)
    baseline = export_dataset(ROOT)
    atoms = _write_atoms(tmp_path / "hard_atoms_train.jsonl", ["rizz", "does not exist xyz"])
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", str(atoms))
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", "4")
    bumped = export_dataset(ROOT)
    assert baseline["counts"]["unbind_hard_upsample"] == 1
    assert baseline["counts"]["unbind_hard_atoms_path"] == ""
    assert baseline["counts"]["n_unbind_hard_extra_copies"] == 0
    assert bumped["counts"]["unbind_hard_upsample"] == 4
    assert bumped["counts"]["unbind_hard_atoms_path"] == "hard_atoms_train.jsonl"
    assert [r["text"] for r in bumped["rows"]] == [r["text"] for r in baseline["rows"]]
    assert [r.get("class") for r in bumped["rows"]] == [r.get("class") for r in baseline["rows"]]
    unbind = [r for r in bumped["rows"] if r["task"] == "unbind"]
    assert all("hard_neg_fillers" not in r for r in unbind)
    assert bumped["counts"]["n_unbind_observed"] == baseline["counts"]["n_unbind_observed"]
    assert bumped["counts"]["name_gate"] is False
