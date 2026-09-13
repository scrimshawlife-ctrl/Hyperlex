"""Synthetic adapter checks. Provenance: Hyperlex Spec 007; base 54db59e0cb1e5c800d49498c61cce179b72c4f7d."""
import copy

import pytest
from test_training_contracts import fixture

from scripts.shadow.hyperlexical import loop
from scripts.shadow.hyperlexical.training_adapter import adapt_reviewed


def dataset():
    b = fixture()
    d = {k: b[k] for k in ("sources", "annotations", "split")}
    ann = d["annotations"][0]
    ann["labels"]["family"].update(status="reviewed", values=["none"], loss_mask=True, reviewer="synthetic")
    ann["labels"]["structure"] = dict(ann["labels"]["family"], values=["pos_0", "pos_1"])
    return d


def adapt(d):
    return adapt_reviewed(d, expected_ontology="proposal-v1")


def test_combined_and_repeated_occurrences_preserved():
    d = dataset()
    before = copy.deepcopy(d)
    result = adapt(d)
    row = result["rows"][0]
    assert row["task"] == "classify+unbind"
    assert row["split"] == "val"
    assert [(s["start"], s["occurrence_id"]) for s in row["occurrence_spans"]] == [(0, "o1"), (5, "o2")]
    assert row["fillers"] == ["same", "same"]
    assert "class" not in row
    assert result["training_ready"] is False
    row["labels"]["family"]["values"].append("changed")
    assert d == before


def test_unknown_family_not_negative():
    d = dataset()
    d["annotations"][0]["labels"]["family"].update(status="unreviewed", values=[], loss_mask=False)
    row = adapt(d)["rows"][0]
    assert "lineage" not in row
    assert row["task"] == "unbind"
    assert row["loss_masks"]["family"] is False


def test_no_active_accounted():
    d = dataset()
    for label in d["annotations"][0]["labels"].values():
        label["loss_mask"] = False
    result = adapt(d)
    assert result["rows"] == []
    assert result["excluded"] == [{"example_id": "e1", "reason": "NO_ACTIVE_SUPERVISION"}]


@pytest.mark.parametrize("kind", ["weak", "typology", "ontology", "unknown_family", "multi_family", "rights"])
def test_rejects_unsupported(kind):
    d = dataset()
    ann = d["annotations"][0]
    if kind == "weak":
        ann["labels"]["family"]["status"] = "weak"
    elif kind == "typology":
        ann["labels"]["typology"] = copy.deepcopy(ann["labels"]["family"])
    elif kind == "ontology":
        ann["ontology_version"] = "other"
    elif kind == "unknown_family":
        ann["labels"]["family"]["values"] = ["invented"]
    elif kind == "multi_family":
        ann["labels"]["family"]["values"] = ["none", "ai-native"]
    else:
        d["sources"][0]["rights_status"] = "unreviewed"
    with pytest.raises(ValueError):
        adapt(d)


def test_test_partition_and_determinism():
    d = dataset()
    d["split"]["assignments"][0]["partition"] = "test"
    result = adapt(d)
    assert result == adapt(copy.deepcopy(d))
    assert result["routing"]["row_outcomes"] == {"reserved_test": 1}


def test_legacy_loop_refuses_before_write_or_model(monkeypatch, tmp_path):
    rows = adapt(dataset())["rows"]
    monkeypatch.setattr(loop, "export_dataset", lambda *a, **k: {"rows": rows})
    def forbidden(*a, **k):
        pytest.fail("adapter must not reach writes or model loading")
    monkeypatch.setattr(loop, "write_export", forbidden)
    monkeypatch.setattr(loop, "_require_local_model", forbidden)
    with pytest.raises(ValueError, match="occurrence-aware"):
        loop.run_loop(tmp_path, tmp_path)
