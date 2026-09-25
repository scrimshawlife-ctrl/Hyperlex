"""Classify harness: train-only vocab, force-train overlap, McNemar, macro-F1."""

from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hyperlexical.classify_metrics import (
    SELECT_METRIC_CLASSIFY,
    SELECT_METRIC_UNBIND,
    checkpoint_score,
    macro_f1_nonnone,
    mcnemar_exact_p,
    mcnemar_paired,
    none_rates,
    resolve_select_metric,
)
from hyperlexical.eval_classify import (
    SLICES_WARNING,
    _spec004_preds,
    main as classify_main,
    run_eval_classify,
)
from hyperlexical.force_train_overlap import (
    enforce_force_train_disjoint,
    overlap_counts,
    resolve_force_train_disjoint,
)
from hyperlexical.layout import label_maps, label_maps_for_splits, resolve_vocab_train_only


def _row(text, fillers, *, split="train", roles=None):
    return {
        "text": text,
        "fillers": fillers,
        "roles": roles if roles is not None else ["pos_0"],
        "role_scheme": "positional",
        "class": "OBSERVED",
        "split": split,
        "task": "unbind",
        "lineage": "none",
    }


def test_vocab_train_only_excludes_val_fillers(monkeypatch):
    monkeypatch.delenv("HLX_VOCAB_TRAIN_ONLY", raising=False)
    assert resolve_vocab_train_only() is False
    train = [_row("train surface aa", ["aa"], roles=["pos_0"])]
    val = [_row("val surface bb", ["bb"], split="val", roles=["pos_9"])]
    historical = label_maps(train + val)
    assert label_maps_for_splits(train, val) == historical
    assert "bb" in historical["filler_vocab"]
    assert "pos_9" in historical["role_vocab"]
    monkeypatch.setenv("HLX_VOCAB_TRAIN_ONLY", "1")
    limited = label_maps_for_splits(train, val)
    assert "bb" not in limited["filler_vocab"]
    assert "aa" in limited["filler_vocab"]
    assert limited["filler_vocab"][0] == "<unk>"
    assert "pos_9" in limited["role_vocab"]
    assert limited["role_vocab"] == historical["role_vocab"]


def test_force_train_overlap_counted_and_dropped(capsys):
    val_hit = _row("Blue Quartz Lantern!", ["quartz"], split="val")
    val_keep = _row("north cobble path", ["cobble"], split="val")
    force = [{"text": "blue quartz lantern", "role_scheme": "positional", "id": "force-1"}]
    counts = overlap_counts(force, [val_hit, val_keep], [val_hit])
    assert counts["n_overlap"] == 1
    assert counts["n_in_val"] == 1
    assert counts["n_in_selection"] == 1
    kept_c, kept_u, report = enforce_force_train_disjoint(
        [],
        [val_hit, val_keep],
        [val_hit],
        force_rows=force,
        disjoint=False,
    )
    assert kept_u == [val_hit, val_keep]
    assert report["n_dropped_unbind_val"] == 0
    assert "n=1" in capsys.readouterr().out
    _c, dropped, report = enforce_force_train_disjoint(
        [],
        [val_hit, val_keep],
        [val_hit],
        force_rows=force,
        disjoint=True,
    )
    assert [row["text"] for row in dropped] == ["north cobble path"]
    assert report["n_dropped_unbind_val"] == 1
    assert report["n_classify_val"] == 0


def test_force_train_overlap_by_id_and_selection_only():
    val = [_row("north cobble path", ["cobble"], split="val")]
    val[0]["id"] = "row-keep"
    selection = [_row("other selection phrase", ["other"], split="val")]
    selection[0]["id"] = "row-sel"
    force = [{"text": "unrelated force phrase", "role_scheme": "positional", "id": "row-sel"}]
    counts = overlap_counts(force, val, selection)
    assert counts["n_in_val"] == 0
    assert counts["n_in_selection"] == 1
    assert counts["n_overlap"] == 1
    _c, kept, report = enforce_force_train_disjoint(
        [],
        val,
        selection,
        force_rows=force,
        disjoint=True,
    )
    assert kept == val
    assert report["n_dropped_unbind_val"] == 0


def test_force_train_disjoint_refuses_over_half():
    rows = [_row(f"synthetic phrase {i}", [f"tok{i}"], split="val") for i in range(3)]
    force = [{"text": row["text"], "role_scheme": "positional"} for row in rows]
    with pytest.raises(SystemExit, match=r"over 50%: classify_val=0/0 unbind_val=3/3"):
        enforce_force_train_disjoint([], rows, rows, force_rows=force, disjoint=True)


def test_force_train_disjoint_allows_exact_half(monkeypatch):
    monkeypatch.delenv("HLX_FORCE_TRAIN_DISJOINT", raising=False)
    assert resolve_force_train_disjoint() is False
    hit = _row("synthetic alpha phrase", ["alpha"], split="val")
    keep = _row("synthetic beta phrase", ["beta"], split="val")
    force = [{"text": "synthetic alpha phrase", "role_scheme": "positional"}]
    _c, kept, report = enforce_force_train_disjoint(
        [],
        [hit, keep],
        [hit, keep],
        force_rows=force,
        disjoint=True,
    )
    assert [row["text"] for row in kept] == ["synthetic beta phrase"]
    assert report["n_dropped_unbind_val"] == 1


def test_mcnemar_exact_on_toy_table():
    # b=6, c=1, n=7. 2 * (C(7,0)+C(7,1)) / 128 = 0.125
    assert mcnemar_exact_p(6, 1) == pytest.approx(0.125)
    assert mcnemar_exact_p(1, 6) == pytest.approx(0.125)
    assert mcnemar_exact_p(0, 0) == 1.0
    gold = ["a", "a", "b", "b"]
    model = ["a", "b", "b", "a"]
    baseline = ["b", "a", "b", "b"]
    # model only: row0. baseline only: row1 and row3. row2 both correct.
    paired = mcnemar_paired(gold, model, baseline)
    assert paired["n_model_only_correct"] == 1
    assert paired["n_baseline_only_correct"] == 2
    assert paired["n_discordant"] == 3
    assert paired["p_two_sided"] == pytest.approx(mcnemar_exact_p(1, 2))


def test_macro_f1_excludes_none():
    gold = ["none", "none", "alpha", "beta"]
    pred = ["none", "alpha", "alpha", "none"]
    # alpha F1 = 2/3, beta F1 = 0, none excluded → 1/3
    assert macro_f1_nonnone(gold, pred) == pytest.approx(1.0 / 3.0)
    rates = none_rates(gold, pred)
    assert rates["none_fpr"] == pytest.approx(0.5)
    assert rates["none_fnr"] == pytest.approx(0.5)
    assert macro_f1_nonnone(["none", "none"], ["none", "alpha"]) is None


def test_select_metric_default_is_unbind(monkeypatch):
    monkeypatch.delenv("HLX_SELECT_METRIC", raising=False)
    assert resolve_select_metric() == SELECT_METRIC_UNBIND
    assert checkpoint_score({"unbind_exact": 0.25}, SELECT_METRIC_UNBIND) == pytest.approx(0.25)
    monkeypatch.setenv("HLX_SELECT_METRIC", SELECT_METRIC_CLASSIFY)
    assert resolve_select_metric() == SELECT_METRIC_CLASSIFY
    assert checkpoint_score({"classify_macro_f1_nonnone": None}, SELECT_METRIC_CLASSIFY) == float("-inf")
    monkeypatch.setenv("HLX_SELECT_METRIC", "accuracy")
    with pytest.raises(ValueError, match="HLX_SELECT_METRIC"):
        resolve_select_metric()


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_eval_classify_end_to_end_synthetic(tmp_path, capsys):
    train = [
        {"id": "t1", "text": "qxredtoken one", "lineage": "alpha"},
        {"id": "t2", "text": "qxredtoken two", "lineage": "alpha"},
        {"id": "t3", "text": "qxbluetoken one", "lineage": "beta"},
        {"id": "t4", "text": "qxbluetoken two", "lineage": "beta"},
        {"id": "t5", "text": "qxplaintoken one", "lineage": "none"},
        {"id": "t6", "text": "qxplaintoken two", "lineage": "none"},
    ]
    eval_rows = [
        {"id": "e1", "text": "qxredtoken three", "lineage": "alpha", "tags": ["rule-agree"]},
        {"id": "e2", "text": "qxbluetoken three", "lineage": "beta", "tags": ["rule-disagree"]},
        {"id": "e3", "text": "qxplaintoken three", "lineage": "none", "tags": ["rule-agree"]},
    ]
    preds = [
        {"id": "e1", "pred": "alpha"},
        {"id": "e2", "pred": "beta"},
        {"id": "e3", "pred": "alpha"},
    ]
    train_path = tmp_path / "train.jsonl"
    eval_path = tmp_path / "eval.jsonl"
    pred_path = tmp_path / "preds.jsonl"
    _write_jsonl(train_path, train)
    _write_jsonl(eval_path, eval_rows)
    _write_jsonl(pred_path, preds)
    out = tmp_path / "report.json"
    rc = classify_main(
        [
            "--preds",
            str(pred_path),
            "--eval",
            str(eval_path),
            "--train",
            str(train_path),
            "--slices",
            "rule-agree,rule-disagree",
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    assert SLICES_WARNING in capsys.readouterr().out
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["brier"] is None
    assert report["n"] == 3
    assert report["accuracy"] == pytest.approx(2.0 / 3.0)
    assert report["macro_f1_nonnone"] == pytest.approx(5.0 / 6.0)
    assert report["none_fpr"] == pytest.approx(0.0)
    assert report["none_fnr"] == pytest.approx(1.0)
    assert report["per_class"]["alpha"]["n"] == 1
    assert report["per_class"]["none"]["n"] == 1
    assert "other than none" in report["macro_f1_nonnone_definition"]
    bag = report["baselines"]["bag_of_terms_logreg"]
    assert bag["status"] == "OK"
    assert bag["accuracy"] == pytest.approx(1.0)
    mcnemar = bag["mcnemar"]
    assert mcnemar["n_discordant"] == 1
    assert mcnemar["n_baseline_only_correct"] == 1
    assert mcnemar["n_model_only_correct"] == 0
    assert mcnemar["p_two_sided"] == pytest.approx(mcnemar_exact_p(0, 1))
    rule = report["baselines"]["match_lineage"]
    assert rule["status"] == "OK"
    assert "p_two_sided" in rule["mcnemar"]
    probe = report["baselines"]["spec004_linear_probe"]
    assert probe["status"] == "NOT_COMPUTABLE"
    assert "fit_scheme" in probe["reason"]
    assert probe["mcnemar"] is None
    assert report["slices_warning"] == SLICES_WARNING
    assert report["slices"]["rule-agree"]["n"] == 2
    assert report["slices"]["rule-agree"]["reporting_only"] is True
    assert report["slices"]["rule-disagree"]["n"] == 1
    direct = run_eval_classify(preds_path=pred_path, eval_path=eval_path, train_path=train_path)
    assert "slices" not in direct


def test_spec004_probe_refits_when_spans_exist():
    def row(label, items, encoding):
        return {
            "lineage": label,
            "text": " ".join(items),
            "item_ids": items,
            "encoding": encoding,
        }

    train = [
        row("alpha", ["aa", "bb"], [1.0, 0.0, 0.0, 0.0]),
        row("alpha", ["aa", "bb"], [0.9, 0.1, 0.0, 0.0]),
        row("beta", ["cc", "dd"], [0.0, 1.0, 0.0, 0.0]),
        row("beta", ["cc", "dd"], [0.1, 0.9, 0.0, 0.0]),
    ]
    eval_rows = [
        row("alpha", ["aa", "bb"], [1.0, 0.0, 0.1, 0.0]),
        row("beta", ["cc", "dd"], [0.0, 1.0, 0.0, 0.1]),
    ]
    preds, meta = _spec004_preds(train, eval_rows)
    assert meta["status"] == "OK"
    assert meta["refit"] == "fit_scheme+swap_accuracy"
    assert preds == ["alpha", "beta"]
