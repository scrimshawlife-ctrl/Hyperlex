"""Row flags for a manifest-v2 draw. No GPU. No test-slice reads."""

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPARK = ROOT / "scripts" / "spark" / "soft_ceiling"
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))
sys.path.insert(0, str(SPARK))

from hyperlexical.flag_rows import (  # noqa: E402
    FLAG_ORDER,
    JEV_PHRASES_PATH,
    UNDEFINED_TERMS_PATH,
    flag_dataset,
    load_term_file,
    write_flags,
)
from hyperlexical.heldout_census import normalize_group_text  # noqa: E402
from hyperlexical.selection_surface import row_id  # noqa: E402
import flag_rows as flag_cli  # noqa: E402

JEV_PHRASES = (
    "we're so back",
    "clutch up",
    "bet that up",
    "real talk",
    "highkey shawty",
    "have fun staying poor",
    "fr fr no cap",
)


def _row(
    text,
    fillers,
    *,
    task="unbind",
    split="val",
    scheme="positional",
    cls="OBSERVED",
    provenance="ingest:store",
    lineage="none",
):
    return {
        "task": task,
        "split": split,
        "class": cls,
        "lineage": lineage,
        "role_scheme": scheme,
        "text": text,
        "fillers": list(fillers),
        "provenance": provenance,
    }


def _by_text(rows, records, text):
    ident = row_id(next(row for row in rows if row["text"] == text))
    matched = [rec for rec in records if rec["row_id"] == ident]
    assert len(matched) == 1
    return matched[0]


def test_committed_lists_cite_kdr_and_jev_receipts():
    undefined = UNDEFINED_TERMS_PATH.read_text(encoding="utf-8")
    assert "never defines" in undefined
    assert "create_high_signal_subset.py" in undefined
    assert load_term_file(UNDEFINED_TERMS_PATH) == frozenset({"kdr"})

    jev = JEV_PHRASES_PATH.read_text(encoding="utf-8")
    for receipt in (
        "20260923-morph77-val-acquire-label-hold.md",
        "20260923-morph76-acquire-settle-cancelled-fair-ceiling.md",
        "20260924-authorize-name-phrases-morph78.md",
    ):
        assert receipt in jev
    assert "Jev did not write the fillers" in jev
    loaded = load_term_file(JEV_PHRASES_PATH)
    assert loaded == {normalize_group_text(phrase) for phrase in JEV_PHRASES}
    assert normalize_group_text("quiet quitting") not in loaded


def test_each_flag_and_holdout_ineligible_is_the_union():
    rows = [
        _row("a general statement", ["General"]),
        _row("alpha beta", ["nope"]),
        _row("quiet desk", [], task="classify", cls="INFERRED", scheme=None),
        _row("see KDR next", ["KDR"]),
        _row("We're so back", ["back"]),
        _row("clutch up later", ["clutch up"], task="classify"),
        _row("shared phrase", ["shared", "phrase"], split="train"),
        _row("Shared Phrase", ["shared", "phrase"], split="val"),
        _row("spent twin phrase", ["phrase"], task="classify", cls="INFERRED"),
        _row("clean zebra token", ["clean", "zebra", "token"]),
        _row("other source", ["other", "source"], split="train", provenance="seed:dialect-e6"),
    ]
    rows[2]["gold_demote_reason"] = "no_gold"
    rows[2]["fillers"] = []
    spent = _row("Spent twin phrase", ["spent", "twin", "phrase"], task="unbind", split="train")
    records, summary = flag_dataset(
        rows,
        trained_rows=[spent],
        holdout_ids={"deadbeef"},
        code_commit="abc",
        code_tree_sha256="def",
    )
    assert _by_text(rows, records, "a general statement")["flags"] == [
        "fallback_label",
        "holdout_ineligible",
    ]
    assert _by_text(rows, records, "alpha beta")["flags"] == [
        "gold_not_in_text",
        "holdout_ineligible",
    ]
    assert _by_text(rows, records, "quiet desk")["flags"] == ["demoted", "holdout_ineligible"]
    assert _by_text(rows, records, "see KDR next")["flags"] == [
        "undefined_term",
        "holdout_ineligible",
    ]
    assert _by_text(rows, records, "We're so back")["flags"] == [
        "jev_selected",
        "holdout_ineligible",
    ]
    # The filler is the phrase. The row text is longer, so this is not a text hit.
    # "clutch up" is one filler and not one surface token, so gold_not_in_text
    # fires too. The two flags are independent.
    clutch = _by_text(rows, records, "clutch up later")
    assert normalize_group_text("clutch up later") not in load_term_file(JEV_PHRASES_PATH)
    assert clutch["flags"] == ["gold_not_in_text", "jev_selected", "holdout_ineligible"]
    for text in ("shared phrase", "Shared Phrase"):
        assert _by_text(rows, records, text)["flags"] == [
            "cross_split_text",
            "holdout_ineligible",
        ]
    assert _by_text(rows, records, "spent twin phrase")["flags"] == [
        "spent_or_trained_text",
        "holdout_ineligible",
    ]
    assert _by_text(rows, records, "clean zebra token")["flags"] == []
    assert _by_text(rows, records, "other source")["flags"] == []

    blob = json.dumps(records) + json.dumps(summary)
    assert "We're so back" not in blob
    assert "clean zebra token" not in blob
    assert "general statement" not in blob
    for rec in records:
        assert set(rec) == {"row_id", "normalized_text_sha256", "source", "split", "flags"}
        assert len(rec["row_id"]) == 16
        assert len(rec["normalized_text_sha256"]) == 64
    assert summary["brier"] is None
    assert summary["holdout"]["n_unresolved"] == 1
    assert any("did not match" in item for item in summary["not_computed"])
    assert summary["counts"]["ingest"]["fallback_label"] == {"train": 0, "val": 1}
    assert summary["counts"]["ingest"]["cross_split_text"] == {"train": 1, "val": 1}
    assert summary["counts"]["seed"]["holdout_ineligible"] == {"train": 0, "val": 0}
    assert summary["n_holdout_ineligible"] == 9


def test_flag_order_when_every_barring_flag_fires():
    norm = normalize_group_text("We're so back")
    row = _row("We're so back", ["General", "KDR"], split="train")
    row["gold_demote_reason"] = "fallback_label"
    from hyperlexical.flag_rows import row_flags

    flags = row_flags(
        row,
        cross_texts={norm},
        spent_texts={norm},
        undefined_terms=load_term_file(UNDEFINED_TERMS_PATH),
        jev_phrases=load_term_file(JEV_PHRASES_PATH),
    )
    assert flags == list(FLAG_ORDER)


def test_holdout_id_text_matches_across_task():
    spent = _row("same surface here", ["same", "surface", "here"], task="unbind", split="val")
    twin = _row("Same surface here", ["here"], task="classify+unbind", split="val", scheme="type_slot")
    clean = _row("clean zebra token", ["clean", "zebra", "token"])
    records, summary = flag_dataset([spent, twin, clean], holdout_ids={row_id(spent)}, holdout_supplied=True)
    assert _by_text([spent, twin, clean], records, "same surface here")["flags"] == [
        "spent_or_trained_text",
        "holdout_ineligible",
    ]
    assert _by_text([spent, twin, clean], records, "Same surface here")["flags"] == [
        "spent_or_trained_text",
        "holdout_ineligible",
    ]
    assert row_id(spent) != row_id(twin)
    assert _by_text([spent, twin, clean], records, "clean zebra token")["flags"] == []
    assert summary["holdout"]["n_resolved"] == 1
    assert summary["holdout"]["n_unresolved"] == 0
    assert "trained-row text" in " ".join(summary["not_computed"])


def test_test_rows_dropped_before_text_is_read(monkeypatch):
    import hyperlexical.flag_rows as flag_mod
    import hyperlexical.heldout_census as census_mod

    order = []
    real_drop = flag_mod.drop_test_rows
    real_norm = flag_mod.normalize_group_text
    real_hit = flag_mod.lenient_copy_hit
    real_id = flag_mod.row_id
    real_census_norm = census_mod.normalize_group_text
    real_census_id = census_mod.row_id

    def spy_drop(rows):
        order.append("drop")
        return real_drop(rows)

    def spy_norm(text):
        order.append("text")
        assert order[0] == "drop"
        assert "UNREAD_TEST_FILLER" not in str(text)
        assert "HELD_OUT_ONLY" not in str(text)
        return real_norm(text)

    def spy_census_norm(text):
        order.append("text")
        assert order[0] == "drop"
        assert "UNREAD_TEST_FILLER" not in str(text)
        assert "HELD_OUT_ONLY" not in str(text)
        return real_census_norm(text)

    def spy_hit(row):
        order.append("text")
        assert order[0] == "drop"
        blob = json.dumps(row)
        assert "UNREAD_TEST_FILLER" not in blob
        assert "HELD_OUT_ONLY" not in blob
        return real_hit(row)

    def spy_id(row):
        order.append("text")
        assert order[0] == "drop"
        blob = json.dumps(row)
        assert "UNREAD_TEST_FILLER" not in blob
        assert "HELD_OUT_ONLY" not in blob
        return real_id(row)

    def spy_census_id(row):
        order.append("text")
        assert order[0] == "drop"
        blob = json.dumps(row)
        assert "UNREAD_TEST_FILLER" not in blob
        assert "HELD_OUT_ONLY" not in blob
        return real_census_id(row)

    monkeypatch.setattr(flag_mod, "drop_test_rows", spy_drop)
    monkeypatch.setattr(flag_mod, "normalize_group_text", spy_norm)
    monkeypatch.setattr(flag_mod, "lenient_copy_hit", spy_hit)
    monkeypatch.setattr(flag_mod, "row_id", spy_id)
    monkeypatch.setattr(census_mod, "normalize_group_text", spy_census_norm)
    monkeypatch.setattr(census_mod, "row_id", spy_census_id)

    val = _row("sentinel phrase", ["sentinel", "phrase"])
    secret = _row("HELD_OUT_ONLY phrase", ["UNREAD_TEST_FILLER"], split="test")
    plain, plain_summary = flag_mod.flag_dataset([val], code_commit="abc", code_tree_sha256="def")
    tainted, tainted_summary = flag_mod.flag_dataset(
        [val, secret],
        code_commit="abc",
        code_tree_sha256="def",
    )
    assert order[0] == "drop"
    assert "text" in order
    assert tainted_summary["n_test_discarded"] == 1
    assert plain_summary["n_test_discarded"] == 0
    assert plain == tainted
    assert plain_summary["counts"] == tainted_summary["counts"]
    assert plain_summary["n_holdout_ineligible"] == tainted_summary["n_holdout_ineligible"]
    body = json.dumps(tainted) + json.dumps(tainted_summary)
    assert "UNREAD_TEST_FILLER" not in body
    assert "HELD_OUT_ONLY" not in body
    assert "sentinel phrase" not in body


def test_two_runs_are_byte_identical(tmp_path):
    rows = [
        _row("a general statement", ["general"]),
        _row("clean zebra token", ["clean", "zebra", "token"], split="train"),
        _row("HELD_OUT_ONLY phrase", ["UNREAD_TEST_FILLER"], split="test"),
    ]
    trained = [_row("other trained", ["other", "trained"], split="train")]
    kwargs = {
        "code_commit": "abc",
        "code_tree_sha256": "def",
        "input_sha256": {"export": "11", "trained": ["22"], "holdout_ids": None},
        "trained_supplied": True,
    }
    first_records, first_summary = flag_dataset(rows, trained, **kwargs)
    second_records, second_summary = flag_dataset(list(reversed(rows)), trained, **kwargs)
    left = write_flags(first_records, first_summary, tmp_path / "a")
    right = write_flags(second_records, second_summary, tmp_path / "b")
    assert left[0].read_bytes() == right[0].read_bytes()
    assert left[1].read_bytes() == right[1].read_bytes()
    assert b"HELD_OUT_ONLY" not in left[0].read_bytes()
    assert b"general statement" not in left[1].read_bytes()
    assert sorted(path.name for path in (tmp_path / "a").iterdir()) == ["flags.jsonl", "flags_summary.json"]


def test_run_command_is_cpu_only_and_refuses_allow_train(monkeypatch, tmp_path):
    command = flag_cli.RUN_COMMAND
    assert "--gpus" not in command
    assert "HYPERLEX_ALLOW_TRAIN" not in command
    assert "guard.py" not in command
    assert "HYPERLEX_OFFLINE=1" in command
    assert "flag_rows.py" in command
    assert "civilian.v0.1.jsonl" in command
    assert "/tmp/hlx-row-flags" in command
    assert "export_dataset" not in command
    assert flag_cli.main(["--print-command"]) == 0

    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    with pytest.raises(SystemExit, match="HYPERLEX_ALLOW_TRAIN"):
        flag_cli.main(["--export", str(tmp_path / "in.jsonl"), "--out-dir", str(tmp_path / "out")])
    assert not (tmp_path / "out").exists()

    monkeypatch.delenv("HYPERLEX_ALLOW_TRAIN", raising=False)
    monkeypatch.delenv("HYPERLEX_OFFLINE", raising=False)
    with pytest.raises(SystemExit, match="HYPERLEX_OFFLINE"):
        flag_cli.main(["--export", str(tmp_path / "in.jsonl"), "--out-dir", str(tmp_path / "out2")])


def test_cli_writes_only_flag_files_and_is_deterministic(monkeypatch, tmp_path):
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    monkeypatch.delenv("HYPERLEX_ALLOW_TRAIN", raising=False)
    export = tmp_path / "export.jsonl"
    rows = [
        _row("a general statement", ["general"]),
        _row("clean zebra token", ["clean", "zebra", "token"], split="train"),
        _row("HELD_OUT_ONLY phrase", ["UNREAD_TEST_FILLER"], split="test"),
    ]
    export.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    trained = tmp_path / "trained.jsonl"
    trained.write_text(
        json.dumps({"text": "other trained", "fillers": ["other", "trained"], "split": "train"}) + "\n",
        encoding="utf-8",
    )
    holdout = tmp_path / "ids.json"
    holdout.write_text(json.dumps({"row_ids": ["deadbeef"]}), encoding="utf-8")

    def run(name):
        out = tmp_path / name
        assert flag_cli.main([
            "--export", str(export),
            "--trained", str(trained),
            "--holdout-ids", str(holdout),
            "--out-dir", str(out),
        ]) == 0
        assert sorted(path.name for path in out.iterdir()) == ["flags.jsonl", "flags_summary.json"]
        return (out / "flags.jsonl").read_bytes(), (out / "flags_summary.json").read_bytes()

    first = run("one")
    second = run("two")
    assert first == second
    summary = json.loads(first[1])
    assert summary["schema"] == "hyperlex.row_flags.v0.1"
    assert summary["n_test_discarded"] == 1
    assert summary["n_rows"] == 2
    assert summary["code_commit"]
    assert len(summary["code_tree_sha256"]) == 64
    assert summary["input_sha256"]["export"]
    assert "UNREAD_TEST_FILLER" not in first[0].decode()
    assert "HELD_OUT_ONLY" not in first[1].decode()
    assert "a general statement" not in first[0].decode()
    package = (ROOT / "scripts/shadow/hyperlexical/flag_rows.py").read_text(encoding="utf-8")
    cli = (SPARK / "flag_rows.py").read_text(encoding="utf-8")
    for text in (package, cli):
        assert "import torch" not in text
        assert "score_holdout" not in text
        assert "export_dataset" not in text
