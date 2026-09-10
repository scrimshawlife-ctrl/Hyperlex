import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.eval_unbind import run_eval
from hyperlexical import train as train_mod


def test_eval_stub_loses_to_004():
    report = run_eval()
    assert report["brier"] is None
    assert report["forecast_eligible"] is False
    assert report["trunk_loaded"] is False
    assert report["e2_pass"] is False
    assert report["probe_swap_min"] >= report["stub_swap"]


def test_train_gated_without_flag():
    os.environ.pop("HYPERLEX_ALLOW_TRAIN", None)
    os.environ.pop("HYPERLEX_TRUNK_DIR", None)
    assert train_mod.main(["--offline"]) == 2
