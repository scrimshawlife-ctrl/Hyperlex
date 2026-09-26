import json
import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.eval_unbind import run_eval
from hyperlexical.layout import MODEL_ID_SEED
from hyperlexical.name_gate import APPROVED_PINS, PUBLIC_CARD_NAME, name_gate_for, pin_of

SCHEMA = ROOT / "specs" / "007-hyperlexical-model" / "schemas" / "eval_unbind.v0.1.schema.json"
CARD_CONFIG = ROOT / "specs" / "007-hyperlexical-model" / "hf-package" / "config.json"


def test_only_morph78_is_approved():
    assert set(APPROVED_PINS) == {"seed-morph78"}


def test_pin_of_train_out_dirs(tmp_path):
    assert pin_of(tmp_path / f"{MODEL_ID_SEED}-morph78") == "seed-morph78"
    assert pin_of(tmp_path / f"{MODEL_ID_SEED}-morph65") == "seed-morph65"
    assert pin_of(tmp_path / "some-other-model") is None
    assert pin_of(None) is None
    assert pin_of("") is None


def test_name_gate_true_only_for_approved_pin(tmp_path):
    assert name_gate_for(tmp_path / f"{MODEL_ID_SEED}-morph78") is True
    for morph in ("morph65", "morph79", "live", "morph78-copy"):
        assert name_gate_for(tmp_path / f"{MODEL_ID_SEED}-{morph}") is False
    assert name_gate_for(None) is False


def test_best_symlink_resolves_to_target(tmp_path):
    named = tmp_path / f"{MODEL_ID_SEED}-morph78"
    other = tmp_path / f"{MODEL_ID_SEED}-morph79"
    named.mkdir()
    other.mkdir()
    best = tmp_path / "BEST"
    best.symlink_to(named)
    assert name_gate_for(best) is True
    best.unlink()
    best.symlink_to(other)
    assert name_gate_for(best) is False


def test_digest_eval_of_pin_dir_is_not_named(tmp_path, monkeypatch):
    monkeypatch.delenv("HYPERLEX_E2_TRUNK_FORWARD", raising=False)
    pin = tmp_path / f"{MODEL_ID_SEED}-morph78"
    pin.mkdir()
    (pin / "heads.json").write_text(
        json.dumps({"model_id": MODEL_ID_SEED, "weight_digest": "fixture"}) + "\n",
        encoding="utf-8",
    )
    report = run_eval(model_dir=pin)
    assert report.get("trunk_forward") in (None, False)
    assert report.get("name_gate", False) is False


def test_eval_schema_allows_boolean_name_gate():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["name_gate"] == {"type": "boolean"}
    assert schema["properties"]["brier"] == {"type": "null"}
    assert schema["properties"]["forecast_eligible"] == {"const": False}


def test_card_config_matches_pin():
    cfg = json.loads(CARD_CONFIG.read_text(encoding="utf-8"))
    assert cfg["model_id"] == PUBLIC_CARD_NAME
    assert cfg["name_gate"] is True
    assert cfg["e2_pass"] is True
    assert cfg["brier"] is None
    assert cfg["last_trainable"] == 8


def test_name_gate_module_is_torch_free():
    src = (ROOT / "scripts" / "shadow" / "hyperlexical" / "name_gate.py").read_text(encoding="utf-8")
    assert "import torch" not in src
    assert "transformers" not in src
