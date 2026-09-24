import json
import pathlib
import sys

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.infer import main as infer_main
from hyperlexical.infer_model import InferModelError, infer, model_identity, model_packet
from hyperlexical.layout import FAMILIES, MODEL_ID_SEED

SCHEMA = json.loads(
    (ROOT / "specs" / "007-hyperlexical-model" / "schemas" / "hyperlexical_inference.v0.1.schema.json").read_text()
)


def _packet(**over):
    kw = dict(
        model_id="hyperlex-structure-149m",
        model_version="seed-morph78",
        vector=[0.1, -0.2, 0.3],
        param_count=149_000_000,
        families=list(FAMILIES),
        family_probs=[0.05] * (len(FAMILIES) - 1) + [0.6],
        atoms=[{"role": "pos_0", "role_pred": "pos_0", "filler": "rizz", "filler_pred": "rizz"}],
    )
    kw.update(over)
    return model_packet("rizz", **kw)


def test_model_packet_matches_schema():
    pkt = _packet()
    jsonschema.validate(pkt, SCHEMA)
    assert pkt["embed_mode"] == "MODEL_EMBEDDING"
    assert pkt["brier"] is None
    assert pkt["forecast_eligible"] is False
    assert pkt["lineage_family"] == FAMILIES[-1]
    assert pkt["lineage_confidence"] == 0.6
    assert pkt["unbind_ok"] is True
    assert pkt["class"] == "INFERRED"
    assert len(pkt["vector_hash"]) == 64


def test_unbind_ok_false_on_filler_miss():
    pkt = _packet(atoms=[{"role": "pos_0", "role_pred": "pos_0", "filler": "rizz", "filler_pred": "<unk>"}])
    assert pkt["unbind_ok"] is False
    jsonschema.validate(pkt, SCHEMA)


def test_family_mismatch_fails_closed():
    with pytest.raises(InferModelError):
        _packet(family_probs=[1.0])


def test_identity_names_only_the_pin(tmp_path):
    assert model_identity(tmp_path / f"{MODEL_ID_SEED}-morph78") == ("hyperlex-structure-149m", "seed-morph78")
    assert model_identity(tmp_path / f"{MODEL_ID_SEED}-morph65") == (f"{MODEL_ID_SEED}-morph65", "seed-morph65")


def test_restricted_never_loads_model(tmp_path):
    pkt = infer("__RESTRICTED_FIXTURE__ x", model_dir=tmp_path / "missing")
    assert pkt["surface"] is None
    assert pkt["restricted_intent_suspected"] is True


def test_missing_weights_fail_closed(tmp_path):
    with pytest.raises(InferModelError):
        infer("rizz", model_dir=tmp_path)


def test_cli_model_dir_fails_closed_exit_2(tmp_path, capsys):
    rc = infer_main(["--text", "rizz", "--model-dir", str(tmp_path)])
    err = json.loads(capsys.readouterr().err)
    assert rc == 2
    assert err["abort"] is True
    assert err["brier"] is None


def test_cli_rejects_type_slot_for_model(tmp_path):
    assert infer_main(["--text", "rizz", "--model-dir", str(tmp_path), "--role-scheme", "type_slot"]) == 2


def test_cli_default_is_still_stub(tmp_path):
    out = tmp_path / "p.json"
    assert infer_main(["--text", "rizz", "--out", str(out)]) == 0
    assert json.loads(out.read_text())["model_id"] == "stub"
