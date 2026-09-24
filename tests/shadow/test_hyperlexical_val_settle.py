import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.val_settle import main as settle_main
from hyperlexical.val_settle import settle_rows

RECEIPT = ROOT / "specs" / "007-hyperlexical-model" / "receipts" / "morph78-val-settle-20260924" / "ACQUIRE_SETTLE_SUMMARY.json"
PHRASES = {"have fun staying poor": "crypto-degen", "fr fr no cap": "kinship-address"}


def _run(policy="force_val", store=None, force=None):
    store = store if store is not None else [{"text": "fr fr no cap", "class": "INFERRED", "split": "train"}]
    force = force if force is not None else [{"text": "rizz", "role_scheme": "positional"}]
    harvest, hard = [], [{"text": "rizz", "role_scheme": "positional"}]
    s = settle_rows(phrases=dict(PHRASES), tag="morph78", auth="test", store=store, harvest=harvest, force=force, hard=hard, split_policy=policy)
    return s, store, harvest, force, hard


def test_reproduces_morph78_added_texts():
    receipt = json.loads(RECEIPT.read_text())
    s, store, harvest, force, hard = _run()
    assert s["added_force_texts"] == receipt["added_force_texts"]
    assert s["force_added"] == receipt["force_added"] == 4
    assert s["hard_added"] == receipt["hard_added"] == 4
    assert sorted(s["settled_inferred_to_observed"]) == sorted(receipt["settled_inferred_to_observed"])


def test_store_rows_observed_with_split_val_and_lineage():
    _, store, harvest, _, _ = _run()
    by = {r["text"]: r for r in store}
    assert by["fr fr no cap"]["class"] == "OBSERVED" and by["fr fr no cap"]["split"] == "val"
    assert by["have fun staying poor"]["lineage"] == "crypto-degen"
    assert {r["role_scheme"] for r in harvest} == {"positional", "type_slot"}
    assert all(r["class"] == "OBSERVED" for r in harvest)


def test_train_policy_leaves_val_untouched():
    s, store, harvest, force, _ = _run(policy="train")
    assert all(r["split"] == "train" for r in store)
    assert all(r["split"] == "train" for r in harvest)
    assert all(r.get("split_hint") in (None, "train") for r in force)


def test_rerun_is_idempotent():
    s1, store, harvest, force, hard = _run()
    s2 = settle_rows(phrases=dict(PHRASES), tag="morph78", auth="t", store=store, harvest=harvest, force=force, hard=hard)
    assert s2["force_added"] == 0
    assert sorted(s2["already_observed"]) == sorted(PHRASES)


def test_requires_named_phrases_and_known_policy():
    with pytest.raises(ValueError):
        settle_rows(phrases={}, tag="x", auth="a", store=[], harvest=[], force=[], hard=[])
    with pytest.raises(ValueError):
        settle_rows(phrases=dict(PHRASES), tag="x", auth="a", store=[], harvest=[], force=[], hard=[], split_policy="val")


def test_cli_dry_run_writes_only_summary(tmp_path):
    files = {n: tmp_path / f"{n}.jsonl" for n in ("store", "harvest", "force", "hard")}
    for f in files.values():
        f.write_text("")
    summary = tmp_path / "summary.json"
    rc = settle_main([
        "--tag", "morph99", "--auth", "dry", "--phrase", "touch grass=gaming-meta",
        "--store", str(files["store"]), "--harvest", str(files["harvest"]),
        "--force-base", str(files["force"]), "--hard-base", str(files["hard"]),
        "--force-out", str(tmp_path / "f_out.jsonl"), "--hard-out", str(tmp_path / "h_out.jsonl"),
        "--summary", str(summary), "--dry-run",
    ])
    assert rc == 0
    assert json.loads(summary.read_text())["force_added"] == 2
    assert files["store"].read_text() == ""
    assert not (tmp_path / "f_out.jsonl").exists()
