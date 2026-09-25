"""Selection-surface audit: Wilson, sibling flag, strict copy, verdict. No GPU."""

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPARK = ROOT / "scripts" / "spark" / "soft_ceiling"
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))
sys.path.insert(0, str(SPARK))

from hyperlexical.selection_surface import (  # noqa: E402
    HoldoutSliceRefused,
    TrainIndex,
    annotate_rows,
    assemble_report,
    broad_clean_rows,
    copy_token_block,
    drop_test_rows,
    force_fair_rows,
    lenient_copy_hit,
    load_force_keys,
    metric_block,
    publish_verdict,
    stem_token,
    strict_slot_pair,
    surface_verdict,
    train_val_strict_rows,
    val_after_force,
    wilson_interval,
    write_report,
)
from hyperlexical.soft_ceiling import row_key  # noqa: E402
from hyperlexical.unbind_recipe import apply_unbind_force_train  # noqa: E402
from score_holdout import copy_baseline  # noqa: E402
import selection_surface_audit as audit_cli  # noqa: E402


def _rate_slice(k: int, n: int) -> dict:
    from hyperlexical.selection_surface import _rate

    return {"unbind_exact": _rate(k, n)}


def _models(**named):
    return {name: {"slices": slices} for name, slices in named.items()}


def test_wilson_known_intervals():
    assert wilson_interval(0, 0) is None
    lo, hi = wilson_interval(222, 306)
    assert round(lo, 3) == 0.673
    assert round(hi, 3) == 0.772
    lo, hi = wilson_interval(1, 10)
    assert round(lo, 3) == 0.018
    assert round(hi, 3) == 0.404
    assert wilson_interval(0, 10)[0] == 0.0
    assert wilson_interval(10, 10)[1] == 1.0
    with pytest.raises(ValueError):
        wilson_interval(3, 2)


def test_stem_and_sibling_flag():
    assert stem_token("quitting") == "quit"
    assert stem_token("quits") == "quit"
    assert stem_token("passing") == "pass"
    train = [
        {"split": "train", "text": "quiet quitting", "fillers": ["quiet", "quitting"]},
        {"split": "train", "text": "alpha beta gamma", "fillers": ["alpha", "beta", "gamma"]},
    ]
    index = TrainIndex(train)
    assert index.match({"text": "Quiet, quitting!"}) == (True, "norm_text")
    assert index.match({"text": "TOKEN:quiet SLOT:quitting"}) == (True, "norm_text")
    assert index.match({"text": "quiet quits", "fillers": ["zzz"]}) == (True, "lemma")
    assert index.match({"text": "other phrase", "fillers": ["alpha", "beta"]}) == (True, "filler_jaccard")
    assert index.match({"text": "unrelated words", "fillers": ["nope"]}) == (False, None)
    # 1/3 is below the 0.5 cutoff.
    assert index.match({"text": "unrelated words", "fillers": ["alpha"]}) == (False, None)
    with pytest.raises(HoldoutSliceRefused):
        TrainIndex([{"split": "test", "text": "quiet quitting", "fillers": ["quiet", "quitting"]}])


def test_strict_slot_copy_credits_placement_only():
    swapped = {"text": "no cap", "fillers": ["cap", "no"]}
    assert lenient_copy_hit(swapped)
    assert strict_slot_pair(swapped) == (["cap", "no"], ["no", "cap"])
    block = metric_block([strict_slot_pair(swapped)])
    assert block["unbind_exact"]["value"] == 0.0
    assert block["unbind_token_f1"]["value"] == 1.0
    assert block["unbind_slot_f1"]["value"] == 0.0
    assert block["unbind_exact"]["wilson95"][0] == 0.0

    placed = {"text": "TOKEN:rizz SLOT:up", "fillers": ["rizz", "up"]}
    gold, pred = strict_slot_pair(placed)
    assert gold == pred == ["rizz", "up"]
    assert lenient_copy_hit(placed)

    missing = {"text": "bet", "fillers": ["that"]}
    assert not lenient_copy_hit(missing)
    assert strict_slot_pair(missing) == (["that"], ["bet"])

    rows = [
        {"text": "no cap", "fillers": ["no", "cap"]},
        {"text": "TOKEN:rizz SLOT:up", "fillers": ["rizz", "up"]},
        {"text": "bet", "fillers": ["that"]},
    ]
    assert copy_token_block(rows)["value"] == copy_baseline(rows)


def test_verdict_rule_and_hold():
    surface = _models(
        morph78={
            "all": _rate_slice(72, 100),
            "harvested": _rate_slice(3, 10),
            "templated": _rate_slice(9, 10),
            "sibling": _rate_slice(5, 10),
            "no_sibling": _rate_slice(5, 10),
        },
        morph65={"all": _rate_slice(70, 100)},
        rc1={"all": _rate_slice(68, 100)},
    )
    decided = surface_verdict(surface)
    assert decided["candidate"] == "SURFACE_SWAP_SUPPORTED"
    assert decided["checks"]["wilson_overlaps_test_clean"]
    assert decided["checks"]["harvested_below_templated"]
    held = publish_verdict(decided["candidate"], [{"row_id": "a"}], None)
    assert held["published"] == "HOLD" and held["reproduce"] == "pending"
    matched = publish_verdict(decided["candidate"], [{"row_id": "a"}], [{"row_id": "a"}])
    assert matched["published"] == "SURFACE_SWAP_SUPPORTED" and matched["hold"] is False
    mismatch = publish_verdict(decided["candidate"], [{"row_id": "a"}], [{"row_id": "b"}])
    assert mismatch["published"] == "HOLD" and mismatch["reproduce"] == "mismatch"

    leak = _models(
        morph78={
            "all": _rate_slice(97, 100),
            "no_sibling": _rate_slice(80, 100),
            "sibling": _rate_slice(100, 100),
            "harvested": _rate_slice(97, 100),
            "templated": _rate_slice(97, 100),
        }
    )
    assert surface_verdict(leak)["candidate"] == "LEAK_NOT_SURFACE"

    rejected = _models(
        morph78={
            "all": _rate_slice(96, 100),
            "sibling": _rate_slice(96, 100),
            "no_sibling": _rate_slice(96, 100),
            "harvested": _rate_slice(96, 100),
            "templated": _rate_slice(96, 100),
        }
    )
    assert surface_verdict(rejected)["candidate"] == "H1_REJECTED"

    no_overlap = _models(
        morph78={
            "all": _rate_slice(50, 100),
            "harvested": _rate_slice(1, 10),
            "templated": _rate_slice(9, 10),
            "sibling": _rate_slice(5, 10),
            "no_sibling": _rate_slice(5, 10),
        },
        morph65={"all": _rate_slice(40, 100)},
        rc1={"all": _rate_slice(30, 100)},
    )
    assert surface_verdict(no_overlap)["candidate"] == "NO_RULE_MATCH"

    rank_flip = _models(
        morph78={
            "all": _rate_slice(72, 100),
            "harvested": _rate_slice(3, 10),
            "templated": _rate_slice(9, 10),
        },
        morph65={"all": _rate_slice(80, 100)},
        rc1={"all": _rate_slice(60, 100)},
    )
    assert surface_verdict(rank_flip)["candidate"] == "NO_RULE_MATCH"


def _fixture_rows():
    templated = []
    for i in range(8):
        text = "trained phrase" if i == 0 else f"alpha phrase {i}"
        templated.append(
            {
                "task": "unbind",
                "split": "val",
                "class": "OBSERVED",
                "lineage": "none",
                "role_scheme": "positional",
                "text": text,
                "fillers": text.split(),
                "provenance": "civilian-pos:registry:demo",
            }
        )
    harvested = [
        {
            "task": "unbind",
            "split": "val",
            "class": "INFERRED",
            "lineage": "none",
            "role_scheme": "type_slot",
            "text": "secret test only",
            "fillers": ["nope", "nope"],
            "provenance": "ingest:store",
        },
        {
            "task": "classify+unbind",
            "split": "val",
            "class": "INFERRED",
            "lineage": "ai-native",
            "role_scheme": "type_slot",
            "text": "harvested phrase here",
            "fillers": ["general"],
            "provenance": {"source": "moltbook"},
        },
    ]
    train = [
        {
            "task": "unbind",
            "split": "train",
            "class": "OBSERVED",
            "lineage": "none",
            "role_scheme": "positional",
            "text": "trained phrase",
            "fillers": ["trained", "phrase"],
            "provenance": "civilian-pos:registry:demo",
        }
    ]
    test = [
        {
            "task": "unbind",
            "split": "test",
            "class": "OBSERVED",
            "lineage": "none",
            "role_scheme": "positional",
            "text": "secret test only",
            "fillers": ["secret", "test"],
            "provenance": "ingest:store",
        }
    ]
    return templated + harvested + train + test


def _predictions(rows):
    kept, _n = drop_test_rows(rows)
    tagged = annotate_rows(
        [row for row in kept if row.get("split") == "val"],
        [row for row in kept if row.get("split") == "train"],
    )
    templated = [row for row in tagged if row["provenance_bucket"] == "templated"]
    preds = {name: {} for name in ("morph78", "morph65", "rc1")}
    miss65 = {templated[-1]["row_id"]}
    miss_rc1 = {row["row_id"] for row in templated[-2:]}
    for row in tagged:
        gold = [item.lower() for item in row["fillers"]]
        miss = ["zzz"] * len(gold)
        hit = row["provenance_bucket"] == "templated"
        preds["morph78"][row["row_id"]] = (gold, gold if hit else miss)
        preds["morph65"][row["row_id"]] = (gold, miss if (not hit or row["row_id"] in miss65) else gold)
        preds["rc1"][row["row_id"]] = (gold, miss if (not hit or row["row_id"] in miss_rc1) else gold)
    return preds


def test_assemble_drops_test_and_holds_until_reproduce(tmp_path):
    rows = _fixture_rows()
    preds = _predictions(rows)
    first = assemble_report(rows, preds)
    second = assemble_report(rows, preds)
    assert first["rows"] == second["rows"]
    assert first["test_slices_scored"] is False
    assert first["allow_train"] is False
    assert first["brier"] is None
    assert first["n_test_discarded"] == 1
    assert all(row["split"] != "test" for row in first["rows"])
    secret = [row for row in first["rows"] if row["text"] == "secret test only"]
    assert len(secret) == 1 and secret[0]["train_sibling"] is False
    sibling = [row for row in first["rows"] if row["text"] == "trained phrase"]
    assert sibling[0]["train_sibling"] is True and sibling[0]["sibling_reason"] == "norm_text"
    assert sibling[0]["provenance_bucket"] == "templated"
    assert secret[0]["provenance_bucket"] == "harvested"
    assert first["release_val"]["n_rows"] == 10
    assert first["verdict"]["candidate"] == "SURFACE_SWAP_SUPPORTED"
    assert first["verdict"]["published"] == "HOLD"
    # Lenient copy is saturated on whitespace templates; strict placement is not,
    # because the harvested "general" filler is not the surface token.
    assert first["controls"]["unbind_copy_token"]["templated"]["value"] == 1.0
    harvested_strict = first["controls"]["strict_slot_copy"]["harvested"]["unbind_exact"]["value"]
    assert harvested_strict == 0.0

    reproduced = assemble_report(rows, preds, reproduce_rows=first["rows"])
    assert reproduced["verdict"]["published"] == "SURFACE_SWAP_SUPPORTED"
    drifted = assemble_report(rows, preds, reproduce_rows=[{"row_id": "nope"}])
    assert drifted["verdict"]["published"] == "HOLD"

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    json_path, md_path = write_report(first, tmp_path)
    reloaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert reloaded["rows"] == first["rows"]
    summary = md_path.read_text(encoding="utf-8")
    assert "HOLD" in summary and "SURFACE_SWAP_SUPPORTED" in summary
    assert "secret test only" not in summary or "discarded" in summary


def test_known_surfaces_and_force_move(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPERLEX_FILLER_FILTER", "off")
    rows = [
        {
            "task": "unbind",
            "split": "val",
            "class": "OBSERVED",
            "text": "keep me",
            "role_scheme": "positional",
            "fillers": ["keep", "me"],
            "provenance": "civilian-pos:registry:x",
        },
        {
            "task": "unbind",
            "split": "val",
            "class": "OBSERVED",
            "text": "trained key",
            "role_scheme": "positional",
            "fillers": ["trained", "key"],
            "provenance": "civilian-pos:registry:x",
        },
        {
            "task": "unbind",
            "split": "val",
            "class": "OBSERVED",
            "text": "in train",
            "role_scheme": "positional",
            "fillers": ["in", "train"],
            "provenance": "ingest:store:live",
        },
        {
            "task": "unbind",
            "split": "train",
            "class": "OBSERVED",
            "text": "in train",
            "role_scheme": "positional",
            "fillers": ["in", "train"],
            "provenance": "civilian-pos:registry:x",
        },
        {
            "task": "unbind",
            "split": "val",
            "class": "INFERRED",
            "text": "a b",
            "role_scheme": "positional",
            "fillers": ["a", "b"],
            "provenance": "ingest:store",
        },
        {
            "task": "unbind",
            "split": "val",
            "class": "OBSERVED",
            "text": "a b",
            "role_scheme": "positional",
            "fillers": ["a", "b"],
            "provenance": "civilian-pos:morph78-val-settle",
        },
        {
            "task": "unbind",
            "split": "val",
            "class": "OBSERVED",
            "text": "bad tok",
            "role_scheme": "positional",
            "fillers": ["@bad"],
            "provenance": "ingest:store",
        },
    ]
    with pytest.raises(HoldoutSliceRefused):
        broad_clean_rows(rows + [{"task": "unbind", "split": "test", "text": "x", "class": "OBSERVED"}], set())
    keys = {row_key({"text": "trained key", "role_scheme": "positional"})}
    clean, accounting = broad_clean_rows(rows, keys)
    assert sorted(row["text"] for row in clean) == ["a b", "bad tok", "keep me"]
    assert accounting["n_excluded_trained_key"] == 1
    assert accounting["n_excluded_train_split_text"] == 1

    force_path = tmp_path / "force.jsonl"
    force_path.write_text(json.dumps({"text": "a b", "role_scheme": "positional"}) + "\n", encoding="utf-8")
    force_keys = load_force_keys(force_path)
    val = [row for row in rows if row.get("split") == "val"]
    _train, recipe_val, _stats = apply_unbind_force_train([], val, path=force_path)
    assert [row["text"] + row["class"] for row in val_after_force(val, force_keys)] == [
        row["text"] + row["class"] for row in recipe_val
    ]
    fair = force_fair_rows(rows, force_keys)
    assert "a b" in {row["text"] for row in fair if row["class"] == "INFERRED"}
    assert not any(row["text"] == "a b" and row["class"] == "OBSERVED" for row in fair)
    assert any(row["fillers"] == ["@bad"] for row in fair)
    strict = train_val_strict_rows(rows, force_keys)
    assert not any(row["fillers"] == ["@bad"] for row in strict)

    report = assemble_report(rows, trained_keys=keys, force_keys=force_keys, n_test_discarded=0)
    assert report["known_surfaces"]["broad_clean"]["status"] == "OK"
    assert report["known_surfaces"]["broad_clean"]["provenance_bucket"]["templated"] >= 1
    bare = assemble_report(rows, n_test_discarded=0)
    assert bare["known_surfaces"]["broad_clean"]["status"] == "NOT_COMPUTABLE"
    assert bare["known_surfaces"]["force_fair"]["status"] == "NOT_COMPUTABLE"
    assert bare["known_surfaces"]["train_val_strict"]["expected_n"] == 140


def test_run_command_is_inference_only(monkeypatch):
    command = audit_cli.RUN_COMMAND
    assert "lmsysorg/sglang:dev-qwen38-27b-dflash2" in command
    assert "guard.py 0.3 selection_surface_audit" in command
    assert "HYPERLEX_ALLOW_TRAIN" not in command
    assert "morph78" in command and "morph65" in command and "rc1" in command
    monkeypatch.delenv("HYPERLEX_RELEASE_SET", raising=False)
    monkeypatch.delenv("HYPERLEX_INCLUDE_LIVE", raising=False)
    with pytest.raises(SystemExit):
        audit_cli.require_eval_env()
    monkeypatch.setenv("HYPERLEX_RELEASE_SET", "1")
    monkeypatch.setenv("HYPERLEX_INCLUDE_LIVE", "1")
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    note = audit_cli.require_eval_env()
    assert note["allow_train_stripped"] is True
    assert "HYPERLEX_ALLOW_TRAIN" not in __import__("os").environ
    with pytest.raises(SystemExit):
        audit_cli.main([
            "--model",
            "morph78=/tmp/holdout-manifest-rc1.json",
            "--out-dir",
            "/tmp/surface-audit-should-not-write",
        ])
