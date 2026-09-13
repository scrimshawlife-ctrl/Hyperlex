"""Torch-free morph15 recipe preflight — resolve-only, fail-closed."""

from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.morph15_recipe import main, morph15_recipe_snapshot


def _clear_morph15_env(monkeypatch):
    for key in (
        "HYPERLEX_UNBIND_PRIMARY",
        "HYPERLEX_UNBIND_SLOT_CE",
        "HYPERLEX_UNBIND_OBSERVED_UPSAMPLE",
        "HYPERLEX_UNBIND_INFERRED_WEIGHT",
        "HYPERLEX_UNBIND_CURRICULUM",
        "HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS",
        "HYPERLEX_UNBIND_CURRICULUM_TYPE_EPOCHS",
        "HYPERLEX_UNBIND_HARD_ATOMS_PATH",
        "HYPERLEX_UNBIND_HARD_UPSAMPLE",
        "HYPERLEX_UNBIND_HEAD_SLOT_WEIGHT",
        "HYPERLEX_UNBIND_RESIDUAL_DUMP",
        "HYPERLEX_INCLUDE_LIVE",
        "HYPERLEX_TRAIN_EPOCHS",
        "HYPERLEX_TRAIN_OUT",
    ):
        monkeypatch.delenv(key, raising=False)


def test_morph15_recipe_defaults_identity(monkeypatch):
    _clear_morph15_env(monkeypatch)
    snap = morph15_recipe_snapshot()
    assert snap["schema"] == "hyperlex.hyperlexical.morph15_recipe.v0.1"
    assert snap["unbind_slot_ce_armed"] is False
    assert snap["unbind_observed_upsample"] == 1
    assert snap["unbind_inferred_weight"] == pytest.approx(1.0)
    assert snap["unbind_curriculum"] is False
    assert snap["unbind_hard_upsample"] == 1
    assert snap["unbind_head_slot_weight"] == pytest.approx(1.0)
    assert snap["unbind_residual_dump"] == ""
    assert snap["unbind_hard_atoms_exists"] is False
    assert snap["name_gate"] is False
    assert snap["pin_best"] == "seed-morph14"
    assert snap["ladder_unbind_exact"] == [0.45, 0.55, 0.65]


def test_morph15_recipe_card_env(monkeypatch, tmp_path):
    _clear_morph15_env(monkeypatch)
    hard = tmp_path / "hard_atoms_train.jsonl"
    hard.write_text('{"text":"x"}\n', encoding="utf-8")
    monkeypatch.setenv("HYPERLEX_UNBIND_PRIMARY", "slot_ce")
    monkeypatch.setenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", "2")
    monkeypatch.setenv("HYPERLEX_UNBIND_INFERRED_WEIGHT", "0.5")
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM", "1")
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS", "2")
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM_TYPE_EPOCHS", "1")
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", str(hard))
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", "3")
    monkeypatch.setenv("HYPERLEX_UNBIND_HEAD_SLOT_WEIGHT", "2")
    monkeypatch.setenv("HYPERLEX_UNBIND_RESIDUAL_DUMP", "/tmp/hlx-morph15-residual.jsonl")
    monkeypatch.setenv("HYPERLEX_INCLUDE_LIVE", "1")
    monkeypatch.setenv("HYPERLEX_TRAIN_EPOCHS", "6")
    snap = morph15_recipe_snapshot()
    assert snap["unbind_slot_ce_armed"] is True
    assert snap["unbind_slot_ce_aux_lambda"] == pytest.approx(0.25)
    assert snap["unbind_observed_upsample"] == 2
    assert snap["unbind_inferred_weight"] == pytest.approx(0.5)
    assert snap["unbind_curriculum"] is True
    assert snap["unbind_curriculum_pos_epochs"] == 2
    assert snap["unbind_curriculum_type_epochs"] == 1
    assert snap["unbind_hard_atoms_exists"] is True
    assert snap["unbind_hard_upsample"] == 3
    assert snap["unbind_head_slot_weight"] == pytest.approx(2.0)
    assert snap["unbind_residual_dump"].endswith("hlx-morph15-residual.jsonl")
    assert snap["include_live"] is True
    assert snap["train_epochs"] == 6
    assert snap["name_gate"] is False


def test_morph15_recipe_main_soft_warn_missing_hard(monkeypatch, capsys):
    _clear_morph15_env(monkeypatch)
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", "3")
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", "/no/such/hard_atoms.jsonl")
    code = main([])
    assert code == 3
    out = json.loads(capsys.readouterr().out)
    assert out["unbind_hard_atoms_exists"] is False
    assert out["name_gate"] is False


def test_morph15_recipe_main_fail_closed_bad_env(monkeypatch, capsys):
    _clear_morph15_env(monkeypatch)
    monkeypatch.setenv("HYPERLEX_UNBIND_HEAD_SLOT_WEIGHT", "0")
    code = main([])
    assert code == 2
    out = json.loads(capsys.readouterr().out)
    assert out["abort"] is True
    assert out["name_gate"] is False
