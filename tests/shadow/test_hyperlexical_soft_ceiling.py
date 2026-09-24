import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.soft_ceiling import (
    PIN_BROAD_EXACT,
    clean_surface,
    decide,
    load_jsonl_keys,
    oov_filler_surface,
    overlap,
)

BASE = dict(force_fair=1.0, force_fair_n=164, best_exact=1.0, val_n=164, e2_pass=True)


def _row(text, scheme="positional", fillers=None, split="val"):
    return {"text": text, "role_scheme": scheme, "fillers": fillers or text.split(), "split": split}


def test_force_fair_mode_unchanged():
    d = decide(force_fair=0.9, force_fair_n=164, best_exact=0.95, val_n=164, e2_pass=True)
    assert d["promote"] and d["mode"] == "force_fair"
    d = decide(force_fair=0.95, force_fair_n=164, best_exact=0.95, val_n=164, e2_pass=True)
    assert d["decision"] == "REJECT_VS_BEST"


def test_missing_broad_eval_rejects():
    assert decide(**BASE)["decision"] == "REJECT_NO_BROAD_EVAL"


def test_unmeasured_contamination_fails_closed():
    d = decide(**BASE, broad_exact=0.99, broad_n=256, prior_broad_exact=0.88, prior_broad_n=256)
    assert d["decision"] == "REJECT_UNKNOWN_CONTAMINATION" and not d["promote"]


def test_contaminated_surface_rejects_morph78_case():
    d = decide(**BASE, broad_exact=0.98828125, broad_n=256, prior_broad_exact=0.88671875, prior_broad_n=256, broad_overlap=193)
    assert d["decision"] == "REJECT_CONTAMINATED" and not d["promote"]


def test_clean_tie_rejects():
    d = decide(**BASE, broad_exact=1.0, broad_n=63, prior_broad_exact=1.0, prior_broad_n=63, broad_overlap=0)
    assert d["decision"] == "REJECT_VS_BROAD_BASELINE" and not d["promote"]


def test_clean_win_promotes():
    d = decide(**BASE, broad_exact=0.95, broad_n=63, prior_broad_exact=0.9, prior_broad_n=63, broad_overlap=0)
    assert d["promote"] and d["broad_baseline_src"] == "live_prior_broad"


def test_pin_fallback_and_surface_mismatch():
    d = decide(**BASE, broad_exact=PIN_BROAD_EXACT + 0.01, broad_n=254, broad_overlap=0)
    assert d["promote"] and d["broad_baseline_src"] == "authorize_pin"
    d = decide(**BASE, broad_exact=0.99, broad_n=250, prior_broad_exact=0.88, prior_broad_n=256, broad_overlap=0)
    assert d["decision"] == "REJECT_BROAD_SURFACE"


def test_e2_fail_blocks():
    d = decide(**{**BASE, "e2_pass": False}, broad_exact=0.99, broad_n=63, prior_broad_exact=0.8, prior_broad_n=63, broad_overlap=0)
    assert not d["promote"]


def test_clean_surface_accounting(tmp_path):
    force = tmp_path / "force.jsonl"
    force.write_text(json.dumps({"text": "Bet That Up", "role_scheme": "positional"}) + "\n")
    trained = load_jsonl_keys(force)
    eval_rows = [
        _row("bet that up"),
        _row("bet that up", scheme="type_slot"),
        _row("rizz"),
        _row("no cap"),
    ]
    train_rows = [_row("rizz", split="train")]
    kept, acct = clean_surface(eval_rows, train_rows=train_rows, trained_keys=trained)
    assert [r["text"] for r in kept] == ["no cap"]
    assert acct == {
        "n_input": 4,
        "n_kept": 1,
        "n_excluded_trained_key": 1,
        "n_excluded_trained_text": 1,
        "n_excluded_train_split_text": 1,
    }
    assert overlap(kept, trained) == 0
    assert overlap(eval_rows, trained) == 2


def test_oov_filler_surface():
    train_rows = [_row("no cap", split="train")]
    rows = [_row("no cap"), _row("touch grass"), _row("cap grass")]
    assert [r["text"] for r in oov_filler_surface(rows, train_rows)] == ["touch grass"]


def test_missing_force_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_jsonl_keys(tmp_path / "nope.jsonl")


def test_task_routing_switch(monkeypatch):
    from hyperlexical.loop import prepare_unbind_splits, task_routing

    monkeypatch.delenv("HYPERLEX_TASK_ROUTING", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_FORCE_TRAIN_PATH", raising=False)
    assert task_routing() == "route_rows"
    assert task_routing("legacy_split") == "legacy_split"
    with pytest.raises(ValueError):
        task_routing("bogus")
    rows = [
        {"task": "unbind", "split": "train", "text": "no cap", "fillers": ["no", "cap"], "roles": ["pos_0", "pos_1"], "role_scheme": "positional", "class": "OBSERVED"},
        {"task": "classify+unbind", "split": "train", "text": "rizz up", "fillers": ["rizz", "up"], "roles": ["pos_0", "pos_1"], "role_scheme": "positional", "class": "OBSERVED"},
    ]
    monkeypatch.setenv("HYPERLEX_TASK_ROUTING", "legacy_split")
    legacy_train, _, _ = prepare_unbind_splits(rows)
    monkeypatch.setenv("HYPERLEX_TASK_ROUTING", "route_rows")
    routed_train, _, _ = prepare_unbind_splits(rows)
    assert {r["text"] for r in legacy_train} == {"no cap"}
    assert {"no cap", "rizz up"} <= {r["text"] for r in routed_train}


def test_reject_reason_does_not_claim_win():
    d = decide(**BASE, broad_exact=1.0, broad_n=58, prior_broad_exact=1.0, prior_broad_n=58, broad_overlap=0)
    assert "not >" in d["reason"]
