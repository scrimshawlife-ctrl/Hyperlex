import json
import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.eval_unbind import main as eval_main
from hyperlexical.eval_unbind import (
    _probe_report,
    e2_test_spans,
    e2_train_overlap_count,
    filler_tuple,
    run_eval,
    spans_to_unbind_rows,
    want_trunk_forward,
)
from hyperlexical import train as train_mod
from hyperlexical.export import LiveStoreMissing, export_dataset, harvest_unbind, harvest_unbind_spans
from hyperlexical.loop import run_loop


def test_eval_stub_loses_to_004(tmp_path, monkeypatch):
    monkeypatch.delenv("HYPERLEX_TRAIN_OUT", raising=False)
    monkeypatch.delenv("HYPERLEX_E2_TRUNK_FORWARD", raising=False)
    monkeypatch.delenv("HYPERLEX_TRUNK_DIR", raising=False)
    monkeypatch.delenv("HLX_E2_DISJOINT", raising=False)
    monkeypatch.setenv("HYPERLEX_TRAIN_OUT", str(tmp_path / "no-heads"))
    report = run_eval()
    assert report["brier"] is None
    assert report["forecast_eligible"] is False
    assert report["trunk_loaded"] is False
    assert report["heads_loaded"] is False
    assert report["weight_file"] is None
    assert report["model_swap"] is None
    assert report["model_id"] == "stub"
    assert report["e2_pass"] is False
    assert report["probe_swap_min"] >= report["stub_swap"]
    assert report["unbind_token_f1"] is None
    assert report["unbind_slot_f1"] is None
    assert report["unbind_token_precision"] is None
    assert report["unbind_token_recall"] is None
    assert report["unbind_exact_strict"] is None
    assert report["e2_train_overlap_count"] > 0


def test_e2_train_overlap_legacy_and_disjoint(monkeypatch):
    """Leak check: harvest n=24 vs the 12 E2 test spans (n=48, seed=7).

    Index identity overlaps test indices 0, 6, 12, 16, 18. Filler-tuple
    comparison also counts test index 44, whose fillers match training
    index 10 with different type tags. ``e2_train_overlap_count`` uses
    filler tuples, so the legacy count is 6 and the disjoint flag makes it 0.
    """
    monkeypatch.delenv("HLX_E2_DISJOINT", raising=False)
    sys.path.insert(0, str(ROOT / "scripts" / "shadow"))
    from recoverable_structure.fit import _split
    from recoverable_structure.fixtures import make_spans

    spans = make_spans(n=48, length=4, seed=7)
    _train_idx, test_idx, _split_hash = _split(48, seed=7)
    train = make_spans(n=24, length=4, seed=7)
    assert test_idx == [0, 6, 12, 16, 18, 36, 41, 43, 44, 45, 46, 47]
    same_span = [
        i
        for i in test_idx
        if i < 24 and spans[i]["item_ids"] == train[i]["item_ids"] and spans[i]["type_tags"] == train[i]["type_tags"]
    ]
    assert same_span == [0, 6, 12, 16, 18]
    train_tuples = {tuple(sp["item_ids"]) for sp in train}
    tuple_overlap = [i for i in test_idx if tuple(spans[i]["item_ids"]) in train_tuples]
    assert tuple_overlap == [0, 6, 12, 16, 18, 44]
    assert filler_tuple(spans[44]) == filler_tuple(train[10])
    assert spans[44]["type_tags"] != train[10]["type_tags"]

    probe_spans = _probe_report()[1]
    assert [filler_tuple(sp) for sp in e2_test_spans()] == [filler_tuple(sp) for sp in probe_spans]
    assert e2_train_overlap_count() == len(tuple_overlap) == 6
    assert e2_train_overlap_count() > 0

    legacy_rows = harvest_unbind()
    assert len(legacy_rows) == 48
    legacy_by_prov = {row["provenance"]: row for row in legacy_rows}

    monkeypatch.setenv("HLX_E2_DISJOINT", "1")
    assert e2_train_overlap_count() == 0
    dropped = harvest_unbind_spans()
    assert len(dropped) == 18
    disjoint_rows = harvest_unbind()
    assert len(disjoint_rows) == 36
    assert {row["provenance"] for row in disjoint_rows} < set(legacy_by_prov)
    for row in disjoint_rows:
        assert row == legacy_by_prov[row["provenance"]]
    monkeypatch.delenv("HYPERLEX_E2_TRUNK_FORWARD", raising=False)
    monkeypatch.setenv("HYPERLEX_TRAIN_OUT", str(ROOT / "no-such-train-out"))
    report = run_eval()
    assert report["e2_train_overlap_count"] == 0
    assert report.get("unbind_exact") is None
    assert report["unbind_exact_strict"] is None
    assert report["e2_pass"] is False


def test_eval_loads_fixture_heads_without_hyperlex(tmp_path, monkeypatch):
    monkeypatch.delenv("HYPERLEX_E2_TRUNK_FORWARD", raising=False)
    heads = tmp_path / "heads.json"
    heads.write_text(
        json.dumps(
            {
                "model_id": "hyperlex-encoder-modernbert-base-seed",
                "weight_digest": "fixture-heads-v0",
                "filler_vocab": ["<unk>", "alpha"],
                "role_vocab": ["<unk>", "slot0"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HYPERLEX_TRAIN_OUT", str(tmp_path))
    before = set(sys.modules)
    report = run_eval()
    added = set(sys.modules) - before
    assert not any(
        m == "hyperlex" or m.startswith("hyperlex.") or m == "abraxas" or m.startswith("abraxas.")
        for m in added
    )
    assert report["heads_loaded"] is True
    assert report["weight_file"] == "heads.json"
    assert report["model_id"] == "hyperlex-encoder-modernbert-base-seed"
    assert report["model_swap"] is not None
    assert report["trunk_loaded"] is False
    assert report["brier"] is None
    # Fixture seed is not the stub hash, so the report can differ from stub-only.
    stub = run_eval(model_dir=tmp_path / "empty")
    assert stub["heads_loaded"] is False
    assert stub["model_id"] == "stub"
    assert report != stub


def test_eval_cli_model_dir_fixture(tmp_path, monkeypatch):
    monkeypatch.delenv("HYPERLEX_E2_TRUNK_FORWARD", raising=False)
    (tmp_path / "heads.json").write_text(
        '{"model_id": "fixture-cli", "weight_digest": "cli"}\n',
        encoding="utf-8",
    )
    out = tmp_path / "e2.json"
    rc = eval_main(["--model-dir", str(tmp_path), "--out", str(out)])
    assert rc == 3
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["heads_loaded"] is True
    assert report["model_id"] == "fixture-cli"
    assert report["e2_pass"] is False


def test_train_gated_without_flag():
    os.environ.pop("HYPERLEX_ALLOW_TRAIN", None)
    os.environ.pop("HYPERLEX_TRUNK_DIR", None)
    os.environ.pop("HYPERLEX_INCLUDE_LIVE", None)
    assert train_mod.main(["--offline"]) == 2


def test_train_include_live_missing_store_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(tmp_path))
    (tmp_path / "config.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("HYPERLEX_INCLUDE_LIVE", "1")
    monkeypatch.setenv("HYPERLEX_LIVE_STORE", str(tmp_path / "missing.jsonl"))
    rc = train_mod.main(["--offline"])
    captured = capsys.readouterr()
    assert rc == 2
    payload = json.loads(captured.err)
    assert payload["abort"] is True
    assert "live store missing" in payload["error"]
    assert payload["include_live"] is True


def test_train_include_live_cli_missing_store_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(tmp_path))
    monkeypatch.delenv("HYPERLEX_INCLUDE_LIVE", raising=False)
    (tmp_path / "config.json").write_text("{}\n", encoding="utf-8")
    rc = train_mod.main(["--offline", "--include-live", "--live-store", str(tmp_path / "nope.jsonl")])
    captured = capsys.readouterr()
    assert rc == 2
    payload = json.loads(captured.err)
    assert "live store missing" in payload["error"]


def test_export_include_live_missing_store_fails(tmp_path):
    with pytest.raises(LiveStoreMissing, match="live store missing"):
        export_dataset(ROOT, include_live=True, live_store=tmp_path / "absent.jsonl")


def test_run_loop_passes_include_live(monkeypatch, tmp_path):
    captured = {}

    def fake_export(root, include_live=False, live_store=None):
        captured["include_live"] = include_live
        captured["live_store"] = live_store
        raise RuntimeError("stop-before-torch")

    monkeypatch.setattr("hyperlexical.loop.export_dataset", fake_export)
    with pytest.raises(RuntimeError, match="stop-before-torch"):
        run_loop(tmp_path, tmp_path / "out", include_live=True, live_store=tmp_path / "store.jsonl")
    assert captured["include_live"] is True
    assert captured["live_store"] == tmp_path / "store.jsonl"


def test_stub_path_unchanged_when_trunk_forward_flag_off(tmp_path, monkeypatch):
    trunk = tmp_path / "trunk"
    trunk.mkdir()
    (trunk / "config.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(trunk))
    monkeypatch.setenv("HYPERLEX_TRAIN_OUT", str(tmp_path / "no-heads"))
    monkeypatch.delenv("HYPERLEX_E2_TRUNK_FORWARD", raising=False)
    report = run_eval()
    assert report["trunk_loaded"] is False
    assert report["heads_loaded"] is False
    assert report["model_id"] == "stub"
    assert report["e2_pass"] is False
    assert report["model_swap"] is None
    assert report.get("trunk_forward") in (None, False)
    assert report["brier"] is None
    assert "name_gate" not in report or report["name_gate"] is False
    assert report["unbind_token_f1"] is None
    assert report["unbind_slot_f1"] is None


def test_trunk_forward_without_trunk_fails_closed(tmp_path, monkeypatch, capsys):
    weights = tmp_path / "weights"
    weights.mkdir()
    (weights / "heads.pt").write_bytes(b"not-a-real-checkpoint")
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(tmp_path / "no-such-trunk"))
    monkeypatch.setenv("HYPERLEX_TRAIN_OUT", str(weights))
    monkeypatch.delenv("HYPERLEX_E2_TRUNK_FORWARD", raising=False)
    rc = eval_main(["--trunk-forward", "--model-dir", str(weights)])
    captured = capsys.readouterr()
    assert rc == 2
    payload = json.loads(captured.err)
    assert payload["abort"] is True
    assert payload["e2_pass"] is False
    assert payload["trunk_loaded"] is False
    assert payload["brier"] is None
    assert payload["name_gate"] is False
    assert "trunk-forward" in payload["error"]


def test_env_trunk_forward_without_trunk_fails_closed(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HYPERLEX_E2_TRUNK_FORWARD", "1")
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(tmp_path / "missing-trunk"))
    monkeypatch.setenv("HYPERLEX_TRAIN_OUT", str(tmp_path / "no-weights"))
    rc = eval_main([])
    captured = capsys.readouterr()
    assert rc == 2
    payload = json.loads(captured.err)
    assert payload["abort"] is True
    assert "trunk-forward" in payload["error"]


def test_trunk_forward_heads_json_only_fails_closed(tmp_path, monkeypatch, capsys):
    trunk = tmp_path / "trunk"
    trunk.mkdir()
    (trunk / "config.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "heads.json").write_text(
        '{"model_id": "fixture", "weight_digest": "x"}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(trunk))
    monkeypatch.setenv("HYPERLEX_TRAIN_OUT", str(tmp_path))
    monkeypatch.setattr("hyperlexical.eval_unbind.torch_importable", lambda: True)
    rc = eval_main(["--trunk-forward"])
    captured = capsys.readouterr()
    assert rc == 2
    payload = json.loads(captured.err)
    assert payload["abort"] is True
    assert "model.safetensors" in payload["error"] or "heads.pt" in payload["error"]


def test_want_trunk_forward_and_004_export_rows(monkeypatch):
    monkeypatch.delenv("HYPERLEX_E2_TRUNK_FORWARD", raising=False)
    assert want_trunk_forward(False) is False
    monkeypatch.setenv("HYPERLEX_E2_TRUNK_FORWARD", "1")
    assert want_trunk_forward(False) is True
    rows = spans_to_unbind_rows(
        [{"item_ids": ["a", "b"], "type_tags": ["TOKEN", "SLOT"]}]
    )
    assert [r["role_scheme"] for r in rows] == ["positional", "type_slot"]
    assert rows[0]["fillers"] == ["a", "b"]
    assert rows[1]["text"] == "TOKEN:a SLOT:b"
