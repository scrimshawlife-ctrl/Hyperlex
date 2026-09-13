"""Synthetic recovery tests; no real training evidence.

Provenance: Notion Sprint 001 Hub NOT_COMPUTABLE + Loop 805 Slice N/A
+ Hash: b3eee725054c1ed1dae16fad3464af005edad0cc (base).
"""
import copy
import hashlib
import json

import pytest
from test_training_contracts import fixture, seal

from scripts.shadow.hyperlexical.training_recovery import assess, main


def dataset():
    base = fixture()
    d = {k: copy.deepcopy(base[k]) for k in ("sources", "annotations", "split")}
    for part in ("train", "test"):
        src = copy.deepcopy(d["sources"][0])
        src.update(source_id=part, raw_text=part, text_sha256=hashlib.sha256(part.encode()).hexdigest())
        ann = copy.deepcopy(d["annotations"][0])
        ann.update(example_id=part, source_id=part, group_ids=[part], spans=[])
        d["sources"].append(src)
        d["annotations"].append(ann)
        d["split"]["assignments"].append({"example_id": part, "partition": part})
    for ann in d["annotations"]:
        ann["labels"]["family"].update(status="reviewed", values=["none"], reviewer="fixture", loss_mask=True)
    return d


def test_clean_no_mutation_or_authority():
    d = dataset()
    before = copy.deepcopy(d)
    r = assess(d)
    assert d == before
    assert r["status"] == "DATA_CONTRACT_CHECKS_PASSED"
    assert r["mode"] == "CLEAN_BASELINE_PROPOSED"
    assert r["training_ready"] is False
    assert r["active_labels_by_partition_head"]["train"] == {"family": 1}


def test_missing_train_signal():
    d = dataset()
    d["annotations"][1]["labels"]["family"]["loss_mask"] = False
    assert "NO_TRAIN_SUPERVISION" in assess(d)["blockers"]


def test_missing_dev_signal():
    d = dataset()
    d["annotations"][0]["labels"]["family"]["loss_mask"] = False
    assert "NO_DEV_SUPERVISION:family" in assess(d)["blockers"]


def test_missing_test():
    d = dataset()
    d["split"]["assignments"][2]["partition"] = "train"
    assert "NO_RESERVED_TEST" in assess(d)["blockers"]


def test_historical_bytes_and_negative_controls(tmp_path):
    d = dataset()
    h = fixture()
    h.update(copy.deepcopy(d))
    cp = tmp_path / "checkpoint"
    cp.write_bytes(b"synthetic checkpoint")
    h["run"]["checkpoint_sha256"] = hashlib.sha256(cp.read_bytes()).hexdigest()
    seal(h)
    assert assess(d, historical=h, checkpoint=cp)["mode"] == "HISTORICAL_BYTES_MATCHED"
    with pytest.raises(ValueError):
        assess(d, historical=h)
    with pytest.raises(ValueError):
        assess(d, checkpoint=cp)
    changed = copy.deepcopy(d)
    changed["split"]["split_id"] = "new"
    with pytest.raises(ValueError, match="differs"):
        assess(changed, historical=h, checkpoint=cp)
    cp.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        assess(d, historical=h, checkpoint=cp)


def test_contract_rejection():
    d = dataset()
    d["sources"][0]["rights_status"] = "unreviewed"
    with pytest.raises(ValueError):
        assess(d)


def test_cli(tmp_path, capsys):
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(dataset()))
    before = path.read_bytes()
    assert main(["--dataset", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["training_ready"] is False
    assert path.read_bytes() == before
    d = dataset()
    d["annotations"][1]["labels"]["family"]["loss_mask"] = False
    path.write_text(json.dumps(d))
    assert main(["--dataset", str(path)]) == 3
    path.write_text('{"sources": [], "sources": []}')
    assert main(["--dataset", str(path)]) == 2
    path.unlink()
    assert main(["--dataset", str(path)]) == 2
