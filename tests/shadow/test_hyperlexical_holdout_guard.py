"""Holdout manifests stay out of unbind train, val, vocab, and injection."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical import train as train_mod  # noqa: E402
from hyperlexical.heldout_census import normalize_group_text  # noqa: E402
from hyperlexical.holdout_guard import (  # noqa: E402
    assert_no_holdout,
    holdout_receipt,
    load_holdout_spec,
    normalized_text_sha256,
    require_holdout_for_training,
)
from hyperlexical.layout import label_maps  # noqa: E402
from hyperlexical.loop import prepare_unbind_splits, run_loop  # noqa: E402
from hyperlexical.selection_surface import row_id  # noqa: E402
from hyperlexical.unbind_recipe import (  # noqa: E402
    apply_unbind_force_train,
    load_hard_atom_texts,
    unbind_row_matches_hard_atoms,
)


@pytest.fixture(autouse=True)
def _clear_holdout_env(monkeypatch):
    for key in (
        "HLX_HOLDOUT_MANIFESTS",
        "HLX_ALLOW_NO_HOLDOUT",
        "HLX_EXPERIMENT_ID",
        "HLX_TRAIN_EXPORT_PATH",
        "HLX_TRAIN_EXPORT_SHA256",
        "HLX_TRAIN_EXPORT_ROWS",
        "HYPERLEX_ALLOW_TRAIN",
        "HYPERLEX_RELEASE_SET",
        "HYPERLEX_TASK_ROUTING",
        "HYPERLEX_FILLER_FILTER",
        "HYPERLEX_UNBIND_FORCE_TRAIN_PATH",
        "HYPERLEX_UNBIND_HARD_ATOMS_PATH",
        "HYPERLEX_UNBIND_HARD_UPSAMPLE",
        "HYPERLEX_UNBIND_OBSERVED_UPSAMPLE",
        "HYPERLEX_UNBIND_INFERRED_CAP",
        "HYPERLEX_EXPORT_DIR",
    ):
        monkeypatch.delenv(key, raising=False)


def _row(text, fillers, *, split="val", cls="OBSERVED", task="unbind"):
    return {
        "text": text,
        "fillers": list(fillers),
        "roles": [f"pos_{i}" for i in range(len(fillers))],
        "role_scheme": "positional",
        "class": cls,
        "split": split,
        "task": task,
        "lineage": "none",
    }


def _write_manifest(
    path: Path,
    *,
    row_ids=(),
    text_hashes=(),
    status=None,
    experiment_id=None,
) -> Path:
    body = {
        "schema": "hyperlex.holdout_manifest.v2",
        "row_ids": list(row_ids),
        "normalized_text_sha256": list(text_hashes),
    }
    if status is not None:
        body["status"] = status
    if experiment_id is not None:
        body["experiment_id"] = experiment_id
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def _arm(monkeypatch, path: Path) -> None:
    monkeypatch.setenv("HLX_HOLDOUT_MANIFESTS", str(path))


def test_id_match_removed_from_val(monkeypatch, tmp_path):
    secret = _row("blue quartz lantern", ["quartz"], split="val")
    keep = _row("north cobble path", ["cobble"], split="val")
    manifest = _write_manifest(
        tmp_path / "ids.json",
        row_ids=[row_id(secret)],
        text_hashes=[normalized_text_sha256("unrelated copper kettle")],
    )
    _arm(monkeypatch, manifest)
    _train, val, stats = prepare_unbind_splits([secret, keep])
    assert [r["text"] for r in val] == ["north cobble path"]
    assert stats["n_holdout_removed_val"] == 1
    assert stats["n_holdout_removed_train"] == 0
    assert stats["holdout_manifests"][0]["sha256"] == hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert stats["holdout_manifests"][0]["n_row_ids"] == 1


def test_text_hash_removed_from_train_val_and_vocab(monkeypatch, tmp_path):
    surface = "Blue Quartz Lantern!"
    assert normalize_group_text(surface) == "blue quartz lantern"
    digest = hashlib.sha256(normalize_group_text(surface).encode("utf-8")).hexdigest()
    assert digest == normalized_text_sha256(surface)
    val_row = _row(surface, ["quartz"], split="val")
    train_row = _row("blue quartz lantern", ["quartz"], split="train")
    keep = _row("north cobble path", ["cobble"], split="train")
    assert row_id(val_row) != row_id(train_row)
    assert row_id(val_row) != "0123456789abcdef"
    assert row_id(train_row) != "0123456789abcdef"
    manifest = _write_manifest(
        tmp_path / "hashes.json",
        row_ids=["0123456789abcdef"],
        text_hashes=[digest],
    )
    _arm(monkeypatch, manifest)
    train, val, stats = prepare_unbind_splits([train_row, val_row, keep])
    assert [r["text"] for r in val] == []
    assert [r["text"] for r in train] == ["north cobble path"]
    assert stats["n_holdout_removed_val"] == 1
    assert stats["n_holdout_removed_train"] == 1
    vocab = label_maps(train + val)["filler_vocab"]
    assert "quartz" not in vocab
    assert "cobble" in vocab


def test_force_train_cannot_reinject(monkeypatch, tmp_path):
    holdout = _row("blue quartz lantern", ["quartz"], split="val")
    keep = _row("north cobble path", ["cobble"], split="train")
    force = tmp_path / "force.jsonl"
    force.write_text(
        json.dumps({"text": "blue quartz lantern", "role_scheme": "positional"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HYPERLEX_UNBIND_FORCE_TRAIN_PATH", str(force))
    moved, _val, moved_stats = apply_unbind_force_train([keep], [holdout])
    assert moved_stats["n_unbind_force_train"] == 1
    assert any(r["text"] == "blue quartz lantern" for r in moved)
    manifest = _write_manifest(
        tmp_path / "force-holdout.json",
        text_hashes=[normalized_text_sha256(holdout["text"])],
    )
    _arm(monkeypatch, manifest)
    train, val, stats = prepare_unbind_splits([keep, holdout])
    assert all(r["text"] != "blue quartz lantern" for r in train + val)
    assert stats["n_unbind_force_train"] == 0
    assert stats["n_holdout_removed_val"] == 1


def test_hard_atoms_cannot_copy(monkeypatch, tmp_path):
    holdout = _row("blue quartz lantern", ["quartz"], split="train")
    keep = _row("north cobble path", ["cobble"], split="train")
    atoms = tmp_path / "atoms.jsonl"
    atoms.write_text(json.dumps({"text": "blue quartz lantern"}) + "\n", encoding="utf-8")
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", str(atoms))
    monkeypatch.setenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", "4")
    assert unbind_row_matches_hard_atoms(holdout, load_hard_atom_texts(atoms))
    manifest = _write_manifest(tmp_path / "atoms-holdout.json", row_ids=[row_id(holdout)])
    _arm(monkeypatch, manifest)
    train, val, stats = prepare_unbind_splits([holdout, keep])
    assert [r["text"] for r in train] == ["north cobble path"]
    assert val == []
    assert stats["n_unbind_hard_extra_copies"] == 0
    assert stats["n_holdout_removed_train"] == 1
    assert "quartz" not in label_maps(train + val)["filler_vocab"]


def test_two_manifests_union(monkeypatch, tmp_path):
    by_id = _row("north cobble path", ["cobble"], split="val")
    by_text = _row("blue quartz lantern", ["quartz"], split="train")
    first = _write_manifest(tmp_path / "a.json", row_ids=[row_id(by_id)])
    second = _write_manifest(
        tmp_path / "b.json",
        text_hashes=[normalized_text_sha256(by_text["text"])],
    )
    monkeypatch.setenv("HLX_HOLDOUT_MANIFESTS", f"{first}, {second}")
    train, val, stats = prepare_unbind_splits([by_id, by_text])
    assert train == [] and val == []
    assert stats["n_holdout_removed_val"] == 1
    assert stats["n_holdout_removed_train"] == 1
    receipt = holdout_receipt(
        load_holdout_spec(),
        {"classify_train": 0, "classify_val": 0, "unbind_train": 1, "unbind_val": 1},
    )
    assert receipt["manifest_sha256"] == [
        hashlib.sha256(first.read_bytes()).hexdigest(),
        hashlib.sha256(second.read_bytes()).hexdigest(),
    ]
    assert receipt["removed"]["unbind_val"] == 1
    assert receipt["allow_no_holdout"] is False


def test_overlap_assertion_names_the_split_and_hides_text(tmp_path):
    row = _row("blue quartz lantern", ["quartz"], split="val")
    manifest = _write_manifest(tmp_path / "overlap.json", row_ids=[row_id(row)])
    spec = load_holdout_spec(str(manifest))
    assert_no_holdout([], spec, "unbind val")
    with pytest.raises(SystemExit, match="unbind val") as raised:
        assert_no_holdout([row], spec, "unbind val")
    message = str(raised.value)
    assert "row_id" in message
    assert "blue quartz lantern" not in message


def test_prepare_asserts_when_filter_is_bypassed(monkeypatch, tmp_path):
    row = _row("blue quartz lantern", ["quartz"], split="val")
    manifest = _write_manifest(tmp_path / "bypass.json", row_ids=[row_id(row)])
    _arm(monkeypatch, manifest)
    monkeypatch.setattr(
        "hyperlexical.loop.filter_holdout_rows",
        lambda rows, spec: (list(rows), 0),
    )
    with pytest.raises(SystemExit, match="holdout overlap remains in unbind val"):
        prepare_unbind_splits([row])


def test_manifest_refuses_embedded_rows_bad_hash_and_missing(tmp_path):
    embedded = tmp_path / "embedded.json"
    embedded.write_text(
        json.dumps({"text": "plain synthetic sentence", "fillers": ["plain"], "task": "unbind"}),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit, match="row content"):
        load_holdout_spec(str(embedded))
    bad = _write_manifest(tmp_path / "bad.json", text_hashes=["abcd"])
    with pytest.raises(SystemExit, match="64-char hex"):
        load_holdout_spec(str(bad))
    with pytest.raises(SystemExit, match="not a file"):
        load_holdout_spec(str(tmp_path / "missing.json"))


def test_run_loop_fails_closed_without_manifest(monkeypatch, tmp_path):
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")

    def _export(*_args, **_kwargs):
        raise AssertionError("export ran")

    monkeypatch.setattr("hyperlexical.loop.export_dataset", _export)
    with pytest.raises(SystemExit, match="HLX_HOLDOUT_MANIFESTS"):
        run_loop(tmp_path, tmp_path / "out")


def test_gate_without_run_does_not_require_manifest(monkeypatch, tmp_path):
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(tmp_path))
    (tmp_path / "config.json").write_text("{}\n", encoding="utf-8")
    assert train_mod.main(["--offline"]) == 0


def test_train_run_fails_closed_without_manifest(monkeypatch, tmp_path):
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(tmp_path))
    (tmp_path / "config.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="no holdout manifest"):
        train_mod.main(["--offline", "--run"])


def test_allow_no_holdout_reaches_training(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HLX_ALLOW_NO_HOLDOUT", "1")
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(tmp_path))
    (tmp_path / "config.json").write_text("{}\n", encoding="utf-8")

    def _export(*_args, **_kwargs):
        raise RuntimeError("past-holdout")

    monkeypatch.setattr("hyperlexical.loop.export_dataset", _export)
    assert train_mod.main(["--offline", "--run"]) == 4
    assert "past-holdout" in capsys.readouterr().err


def test_cli_manifest_and_run_loop_log(monkeypatch, tmp_path, capsys):
    surface = "Blue Quartz Lantern!"
    classify = _row(surface, ["quartz"], split="val", task="classify")
    unbind = _row("north cobble path", ["cobble"], split="val")
    manifest = _write_manifest(
        tmp_path / "cli.json",
        row_ids=[row_id(unbind)],
        text_hashes=[normalized_text_sha256(surface)],
        status="UNSCORED_SEALED",
        experiment_id="HLX-EXP-TEST",
    )
    monkeypatch.setenv("HLX_EXPERIMENT_ID", "HLX-EXP-TEST")
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(tmp_path))
    monkeypatch.setenv("HYPERLEX_EXPORT_DIR", str(tmp_path / "export"))
    (tmp_path / "config.json").write_text("{}\n", encoding="utf-8")
    pinned = tmp_path / "pinned.jsonl"
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in (classify, unbind))
    pinned.write_text(payload, encoding="utf-8")
    monkeypatch.setenv("HLX_TRAIN_EXPORT_PATH", str(pinned))
    monkeypatch.setenv("HLX_TRAIN_EXPORT_SHA256", hashlib.sha256(pinned.read_bytes()).hexdigest())

    def _export(*_args, **_kwargs):
        raise AssertionError("export_dataset must not run for a pinned experiment")

    written = {"n": 0}

    def _write(*_args, **_kwargs):
        written["n"] += 1

    monkeypatch.setattr("hyperlexical.loop.export_dataset", _export)
    monkeypatch.setattr("hyperlexical.loop.write_export", _write)
    with pytest.raises(SystemExit, match="ADMISSION FAIL"):
        train_mod.main(["--offline", "--run", "--holdout-manifest", str(manifest)])
    assert written["n"] == 0
    captured = capsys.readouterr()
    assert "blue quartz" not in captured.out
    assert surface not in captured.out
    assert surface not in captured.err


def _admit(monkeypatch, path: Path, experiment_id: str = "HLX-EXP-TEST") -> None:
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HLX_EXPERIMENT_ID", experiment_id)
    monkeypatch.setenv("HLX_HOLDOUT_MANIFESTS", str(path))


def test_unscored_sealed_with_matching_binding_is_admissible(monkeypatch, tmp_path):
    manifest = _write_manifest(
        tmp_path / "fresh.json",
        row_ids=["abc123"],
        status="UNSCORED_SEALED",
        experiment_id="HLX-EXP-TEST",
    )
    _admit(monkeypatch, manifest)
    spec = require_holdout_for_training()
    assert spec.row_ids == frozenset({"abc123"})
    assert spec.manifests[0]["status"] == "UNSCORED_SEALED"
    assert spec.manifests[0]["experiment_id"] == "HLX-EXP-TEST"


@pytest.mark.parametrize("status", ["SCORED_SPENT", "SCORED", "FROZEN_NOT_SCORED"])
def test_spent_scored_and_unknown_status_are_rejected(monkeypatch, tmp_path, status):
    manifest = _write_manifest(
        tmp_path / "closed.json",
        row_ids=["abc123"],
        status=status,
        experiment_id="HLX-EXP-TEST",
    )
    _admit(monkeypatch, manifest)
    with pytest.raises(SystemExit, match="not admissible"):
        require_holdout_for_training()


def test_missing_status_is_rejected(monkeypatch, tmp_path):
    manifest = _write_manifest(tmp_path / "bare.json", row_ids=["abc123"])
    _admit(monkeypatch, manifest)
    with pytest.raises(SystemExit, match="status is missing"):
        require_holdout_for_training()


def test_wrong_experiment_binding_is_rejected(monkeypatch, tmp_path):
    manifest = _write_manifest(
        tmp_path / "wrong.json",
        row_ids=["abc123"],
        status="UNSCORED_SEALED",
        experiment_id="HLX-EXP-OTHER",
    )
    _admit(monkeypatch, manifest, "HLX-EXP-TEST")
    with pytest.raises(SystemExit, match="experiment binding"):
        require_holdout_for_training()


def test_unbound_experiment_is_rejected(monkeypatch, tmp_path):
    manifest = _write_manifest(
        tmp_path / "unbound.json",
        row_ids=["abc123"],
        status="UNSCORED_SEALED",
    )
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HLX_HOLDOUT_MANIFESTS", str(manifest))
    with pytest.raises(SystemExit, match="experiment binding"):
        require_holdout_for_training()


def test_no_holdout_is_rejected_when_override_is_unset(monkeypatch):
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    with pytest.raises(SystemExit, match="no holdout manifest"):
        require_holdout_for_training()


def test_spent_companion_does_not_admit(monkeypatch, tmp_path):
    fresh = _write_manifest(
        tmp_path / "fresh.json",
        row_ids=["abc123"],
        status="UNSCORED_SEALED",
        experiment_id="HLX-EXP-TEST",
    )
    spent = _write_manifest(
        tmp_path / "spent.json",
        row_ids=["def456"],
        status="SCORED_SPENT",
        experiment_id="HLX-EXP-TEST",
    )
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HLX_EXPERIMENT_ID", "HLX-EXP-TEST")
    monkeypatch.setenv("HLX_HOLDOUT_MANIFESTS", f"{fresh},{spent}")
    with pytest.raises(SystemExit, match="SCORED_SPENT"):
        require_holdout_for_training()


def test_spent_manifest_still_excludes_rows(monkeypatch, tmp_path):
    secret = _row("blue quartz lantern", ["quartz"], split="val")
    keep = _row("north cobble path", ["cobble"], split="val")
    manifest = _write_manifest(
        tmp_path / "spent.json",
        row_ids=[row_id(secret)],
        status="SCORED_SPENT",
        experiment_id="HLX-EXP-TEST",
    )
    _arm(monkeypatch, manifest)
    _train, val, stats = prepare_unbind_splits([secret, keep])
    assert [r["text"] for r in val] == ["north cobble path"]
    assert stats["n_holdout_removed_val"] == 1
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HLX_EXPERIMENT_ID", "HLX-EXP-TEST")
    with pytest.raises(SystemExit, match="SCORED_SPENT"):
        require_holdout_for_training()
