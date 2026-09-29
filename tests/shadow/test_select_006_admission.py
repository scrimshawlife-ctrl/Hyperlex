"""SELECT-006 admission evidence. No optimizer and no training."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.admission import _decision_authorization
from hyperlexical.loop import run_loop
from hyperlexical.select_006_admission import (
    EXPERIMENT_ID,
    LOADER_NOT_VERIFIED,
    WITNESS_MISMATCH,
    Select006AdmissionError,
    select006_threshold_is_sealed,
    verify_zero_init_witness,
)
from hyperlexical.select_006_efficiency_preservation import vocabulary_expansion_pin


def _witness() -> dict:
    return {
        "execution_loader_status": "ZERO_INIT_LOADER_VERIFIED",
        "expanded_filler_bias_sha256": "cce2ff11650d8b9734f84f1d05acd65003b68e31adb5e0c9e035beaa7f5a03bf",
        "expanded_filler_weight_sha256": "b3d11a8eb1fcfb4f616c36b9f5b32be84aab9c91d642e54294dccfea36a385a3",
        "expanded_loader_witness_sha256": "58a3e733087c33c5ffea5909b46098e666337e1b99fb83d87c3744db4aef91b2",
        "expanded_role_bias_sha256": "ce7b6ecb2b276d4d5b46ae23f38a749d1939cadc336e82b76548e01065151b93",
        "expanded_role_weight_sha256": "94aa92d4c6f17f56a6d7a68a5951ad98bb38764d029ed93916fb9b870c54c20d",
        "optimizer_constructed": False,
        "training_started": False,
    }


def test_historical_vocabulary_pin_stays_unimplemented():
    assert vocabulary_expansion_pin()["execution_loader_status"] == "NOT_YET_IMPLEMENTED"


def test_verified_witness_is_the_live_loader_state():
    verify_zero_init_witness(_witness())
    bad = _witness()
    bad["execution_loader_status"] = "NOT_YET_IMPLEMENTED"
    with pytest.raises(Select006AdmissionError, match=LOADER_NOT_VERIFIED):
        verify_zero_init_witness(bad)
    drifted = _witness()
    drifted["expanded_loader_witness_sha256"] = "0" * 64
    with pytest.raises(Select006AdmissionError, match=WITNESS_MISMATCH):
        verify_zero_init_witness(drifted)


def test_select006_threshold_schema_seals_without_numeric_floors():
    payload = {
        "authorization_state": "SEALED",
        "decision_rule": {"compensation": False, "primary_equality": "PASS"},
        "epsilon": 0,
        "experiment_id": EXPERIMENT_ID,
        "schema": "hyperlex.select_006_threshold_authorization.v1",
        "sealed": True,
        "training_launch_authorized": False,
    }
    assert select006_threshold_is_sealed(payload, EXPERIMENT_ID) is True


def test_numeric_threshold_gate_still_rejects_an_empty_v1_file(tmp_path, monkeypatch):
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "schema": "hyperlex.threshold_authorization.v1",
        "sealed": True,
    }
    path = tmp_path / "threshold.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("HLX_THRESHOLD_AUTHORIZATION", str(path))

    class Ctx:
        experiment_id = EXPERIMENT_ID

        def fail(self, gate, message, **fields):
            raise SystemExit(message)

    with pytest.raises(SystemExit, match="numeric decision thresholds"):
        _decision_authorization(Ctx())


def test_admission_only_returns_before_optimizer():
    src = Path(run_loop.__code__.co_filename).read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_loop")
    admit_line = adam_line = None
    for node in ast.walk(fn):
        if isinstance(node, ast.Compare):
            text = ast.get_source_segment(src, node) or ""
            if "HLX_ADMISSION_ONLY" in text:
                admit_line = node.lineno
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "AdamW":
            adam_line = node.lineno
    assert admit_line is not None and adam_line is not None
    assert admit_line < adam_line
