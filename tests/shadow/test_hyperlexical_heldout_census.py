"""Held-out census: admission rules, Jaccard, source cap, reproduce. No GPU."""

import hashlib
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPARK = ROOT / "scripts" / "spark" / "soft_ceiling"
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))
sys.path.insert(0, str(SPARK))

from hyperlexical.heldout_census import (  # noqa: E402
    DRAW_READY_MIN,
    TOPUP_MIN,
    admitted_ids_sha256,
    census_rows,
    group_key,
    load_holdout_ids,
    load_trained_files,
    normalize_group_text,
    pinned_verdict,
    publish_census,
    source_over_cap,
    write_census,
)
from hyperlexical.selection_surface import row_id  # noqa: E402
from hyperlexical.soft_ceiling import row_key  # noqa: E402
import heldout_census as census_cli  # noqa: E402


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


def _census(rows, trained=(), holdout=(), **kwargs):
    return census_rows(rows, trained, holdout, code_commit="abc", code_tree_sha256="def", **kwargs)


def test_group_key_nfkc_casefold_url_punct_and_fillers():
    assert normalize_group_text("  Hello,\tWorld! ") == "hello world"
    assert normalize_group_text("ﬁle") == "file"
    assert normalize_group_text("ATE THAT https://t.co/abc UP") == "ate that up"
    assert normalize_group_text("www.example.com/x") == ""
    left = group_key(_row("Hello, World!", ["World", "Hello"]))
    right = group_key(_row("hello   world", ["hello", "world"]))
    assert left == right == ("hello world", ("hello", "world"))
    url = group_key(_row("ate that https://t.co/abc up", ["up", "ate", "that"]))
    plain = group_key(_row("ate that up", ["ate", "that", "up"]))
    assert url == plain


def test_each_rule_first_fail_and_all_failing():
    rows = [
        _row("plain classify", ["plain", "classify"], task="classify"),
        _row("something else", ["general"]),
        _row("placeholder row", ["general"], task="classify+unbind"),
        _row("see @handle", ["@handle"]),
        _row("secret phrase", ["secret", "phrase"]),
        _row("clean zebra", ["clean", "zebra"]),
    ]
    secret = rows[4]
    report = _census(rows, holdout={row_id(secret)})
    assert report["rejected"]["first_failing"] == {"1": 2, "2": 1, "3": 0, "4": 1, "5": 1}
    assert report["rejected"]["all_failing"]["1"] == 2
    assert report["rejected"]["all_failing"]["2"] == 2
    assert report["rejected"]["all_failing"]["4"] == 1
    assert report["rejected"]["all_failing"]["5"] == 1
    assert report["n_admitted"] == 1
    assert report["admitted"]["by_source"] == {"ingest": 1}
    assert report["admitted"]["by_scheme"] == {"positional": 1}
    assert report["admitted"]["by_class"] == {"OBSERVED": 1}
    blob = json.dumps(report)
    assert "something else" not in blob
    assert "secret phrase" not in blob
    assert "clean zebra" not in blob

    stacked = _row("nope", ["@handle"], task="classify")
    stacked_id = row_id(stacked)
    train = _row("nope train", ["@handle"], split="train")
    both = _census([stacked], trained=[train], holdout={stacked_id})
    assert both["rejected"]["first_failing"]["1"] == 1
    assert both["rejected"]["all_failing"] == {"1": 1, "2": 1, "3": 1, "4": 1, "5": 1}


def test_classify_unbind_recovers_only_when_gold_is_in_the_text():
    kept = _row("token rizz", ["token", "rizz"], task="classify+unbind", provenance={"source": "moltbook"})
    report = _census([kept])
    assert report["n_admitted"] == 1
    assert report["admitted"]["by_source"] == {"dict:moltbook": 1}
    missed = _row("unrelated words", ["general"], task="classify+unbind")
    missed_report = _census([missed])
    assert missed_report["rejected"]["first_failing"]["1"] == 1
    assert missed_report["rejected"]["all_failing"]["2"] == 1


def test_jaccard_sibling_and_exact_twin_not_lemma():
    train_j = _row("alpha beta gamma", ["alpha", "beta", "gamma"], split="train")
    half = _row("alpha beta elsewhere", ["alpha", "beta"])
    below = _row("alpha only here", ["alpha"])
    wide = _row("alpha beta gamma delta", ["alpha", "beta", "gamma", "delta"], split="train")
    touch = _row("touch token", ["touch"])
    report = _census([half, below, touch], trained=[train_j, wide])
    assert report["rejected"]["first_failing"]["3"] == 1
    assert report["n_admitted"] == 2

    twin_train = _row("hello world", ["hello", "world"], split="train")
    twin = _row("Hello World", ["hello", "world"])
    url = _row("ate that https://t.co/abc up", ["ate", "that", "up"])
    url_train = _row("ate that up", ["ate", "that", "up"], split="train")
    blocked = _census([twin, url], trained=[twin_train, url_train])
    assert blocked["n_admitted"] == 0
    assert blocked["rejected"]["first_failing"]["3"] == 2

    # Lemma overlap is not a census sibling. "quits" does not match "quitting".
    lemma_train = _row("quiet quitting", ["quiet", "quitting"], split="train")
    lemma = _row("quiet quits zebra", ["zebra"])
    assert _census([lemma], trained=[lemma_train])["n_admitted"] == 1

    # Pool twins are both counted. The union checked is the trained side only.
    one = _row("solo phrase", ["solo", "phrase"])
    two = _row("solo phrase", ["solo", "phrase"])
    assert _census([one, two])["n_admitted"] == 2


def test_text_only_trained_file_blocks_normalized_text_and_shares_fillers():
    pool = [
        _row("no cap", ["no", "cap"]),
        _row("no cap extra", ["no", "cap", "extra"]),
        _row("extra words", ["extra", "words"]),
    ]
    trained = [{"text": "No, cap!"}]
    report = _census(pool, trained=trained)
    assert report["n_admitted"] == 1
    assert report["rejected"]["first_failing"]["3"] == 2


def test_train_split_row_is_not_admitted():
    row = _row("seen already", ["seen", "already"], split="train")
    report = _census([row])
    assert report["n_admitted"] == 0
    assert report["rejected"]["first_failing"]["3"] == 1


def test_holdout_key_and_row_id_both_exclude():
    row = _census_row = _row("held out phrase", ["held", "out", "phrase"])
    text, scheme = row_key(row)
    key = "|".join((row["task"], text, scheme))
    by_key = _census([row], holdout={key})
    assert by_key["rejected"]["first_failing"]["5"] == 1
    by_id = _census([_census_row], holdout={row_id(_census_row)})
    assert by_id["n_admitted"] == 0


def test_verdict_thresholds_and_source_cap():
    assert TOPUP_MIN == 150 and DRAW_READY_MIN == 470
    assert pinned_verdict(0, 0) == "POOL_EXHAUSTED"
    assert pinned_verdict(149, 149) == "POOL_EXHAUSTED"
    assert pinned_verdict(150, 150) == "TOPUP_NEEDED"
    assert pinned_verdict(469, 200) == "TOPUP_NEEDED"
    assert pinned_verdict(470, 282) == "DRAW_READY"
    assert pinned_verdict(470, 283) == "SOURCE_CAP"
    assert pinned_verdict(470, 470) == "SOURCE_CAP"
    assert source_over_cap(282, 470) is False
    assert source_over_cap(283, 470) is True
    assert source_over_cap(0, 0) is False

    def band(n, first_source):
        rows = []
        for i in range(n):
            source = "src-a:x" if i < first_source else "src-b:x"
            rows.append(_row(f"unique{i} alpha", [f"unique{i}", "alpha"], provenance=source))
        return _census(rows)

    ready = band(470, 282)
    assert ready["verdict"]["candidate"] == "DRAW_READY"
    assert ready["admitted"]["max_source_share"] == pytest.approx(0.6)
    assert ready["admitted"]["max_source"] == "src-a"
    assert ready["verdict"]["published"] == "HOLD"
    assert ready["verdict"]["reproduce"] == "pending"
    skewed = band(470, 283)
    assert skewed["verdict"]["candidate"] == "SOURCE_CAP"
    assert skewed["verdict"]["checks"]["source_cap_ok"] is False
    assert band(150, 150)["verdict"]["candidate"] == "TOPUP_NEEDED"
    assert band(149, 149)["verdict"]["candidate"] == "POOL_EXHAUSTED"


def test_reproduce_matches_admitted_id_hash_only_for_the_same_sha():
    rows = [_row("alpha beta", ["alpha", "beta"]), _row("gamma delta", ["gamma", "delta"])]
    first = _census(rows)
    assert first["admitted_ids_sha256"] == admitted_ids_sha256(
        [row_id(rows[0]), row_id(rows[1])]
    )
    matched = _census(rows, prior=first)
    assert matched["verdict"]["candidate"] == "POOL_EXHAUSTED"
    assert matched["verdict"]["reproduce"] == "matched"
    assert matched["verdict"]["published"] == matched["verdict"]["candidate"]
    assert matched["verdict"]["hold"] is False

    drifted = dict(first)
    drifted["admitted_ids_sha256"] = "0" * 64
    mismatch = _census(rows, prior=drifted)
    assert mismatch["verdict"]["published"] == "HOLD"
    assert mismatch["verdict"]["reproduce"] == "mismatch"

    other_sha = dict(first)
    other_sha["code_commit"] = "different"
    assert _census(rows, prior=other_sha)["verdict"]["reproduce"] == "mismatch"

    missing = _census(rows, prior=first, id_list_present=False)
    assert missing["holdout"]["id_list_present"] is False
    assert missing["verdict"]["checks"]["holdout_id_list_present"] is False
    assert missing["verdict"]["reproduce"] == "matched"
    assert missing["verdict"]["published"] == missing["verdict"]["candidate"]
    direct = publish_census("DRAW_READY", first["admitted_ids_sha256"], "abc", first)
    assert direct["published"] == "DRAW_READY"


def test_empty_admission_hash_and_test_rows_are_unread():
    secret = _row("TEST SECRET GOLD", ["test", "secret"], split="test")
    report = _census([secret, _row("kept token", ["kept", "token"])])
    assert report["n_test_discarded"] == 1
    assert report["n_pool"] == 1
    assert report["n_admitted"] == 1
    assert "TEST SECRET GOLD" not in json.dumps(report)
    empty = _census([])
    assert empty["n_admitted"] == 0
    assert empty["verdict"]["candidate"] == "POOL_EXHAUSTED"
    assert empty["admitted_ids_sha256"] == hashlib.sha256(b"").hexdigest()
    assert empty["brier"] is None


def _write(directory: pathlib.Path, name: str, payload) -> pathlib.Path:
    path = directory / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_holdout_loader_id_list_and_hash_only_manifest(tmp_path):
    listed = _write(tmp_path, "ids.json", {"row_ids": ["a", "b"], "rules": ["do not treat me as an id"]})
    ids, present = load_holdout_ids(listed)
    assert present is True
    assert ids == {"a", "b"}
    nested = _write(
        tmp_path,
        "nested.json",
        {
            "slices": {"unbind_all": {"ids": ["u1"], "ids_sha256": "abc", "n": 1}},
            "metrics": {"unbind": ["unbind_exact"]},
            "trained_files": ["/tmp/force.jsonl"],
            "rules": ["Score each listed model once on these exact row-ID hashes."],
        },
    )
    ids, present = load_holdout_ids(nested)
    assert present is True
    assert ids == {"u1"}
    assert "unbind_exact" not in ids
    bare = _write(tmp_path, "bare.json", ["only-id"])
    assert load_holdout_ids(bare) == ({"only-id"}, True)
    hashed = _write(
        tmp_path,
        "holdout-manifest-rc1.json",
        {"schema": "hyperlex.holdout_manifest.v0.1", "slices": {"unbind_all": {"ids_sha256": "abc", "n": 1}}},
    )
    ids, present = load_holdout_ids(hashed)
    assert ids == set() and present is False
    embedded = _write(tmp_path, "rows.json", {"rows": [{"text": "secret gold", "fillers": ["secret"], "task": "unbind"}]})
    with pytest.raises(SystemExit, match="row content"):
        load_holdout_ids(embedded)
    scores = _write(tmp_path, "holdout-scores-rc1.json", {"row_ids": ["z"]})
    with pytest.raises(SystemExit, match="scores"):
        load_holdout_ids(scores)


def test_train_receipt_resolves_basename_and_skips_test_rows(tmp_path):
    data = tmp_path / "hlx"
    data.mkdir()
    force = data / "force.jsonl"
    force.write_text(
        json.dumps({"text": "no cap", "fillers": ["no", "cap"], "role_scheme": "positional"}) + "\n"
        + json.dumps({"text": "secret test", "fillers": ["secret"], "split": "test"}) + "\n",
        encoding="utf-8",
    )
    receipt = _write(
        tmp_path,
        "train-receipt.json",
        {
            "schema": "hyperlex.hyperlexical.train_receipt.v0.1",
            "unbind_force_train_path": "force.jsonl",
            "unbind_hard_atoms_path": "",
            "epoch_metrics": [{"note": "do not import this text"}],
        },
    )
    rows, loaded = load_trained_files([str(force), str(receipt)])
    assert [row["text"] for row in rows] == ["no cap", "no cap"]
    assert "secret test" not in json.dumps(rows)
    assert str(force) in loaded
    missing = _write(
        tmp_path,
        "other-receipt.json",
        {"schema": "hyperlex.hyperlexical.train_receipt.v0.1", "unbind_hard_atoms_path": "missing.jsonl"},
    )
    with pytest.raises(SystemExit, match="not found"):
        load_trained_files([str(missing)])


def test_run_command_is_cpu_only_and_refuses_allow_train(monkeypatch, tmp_path):
    command = census_cli.RUN_COMMAND
    assert "--gpus" not in command
    assert "HYPERLEX_ALLOW_TRAIN" not in command
    assert "guard.py" not in command
    assert "HYPERLEX_OFFLINE=1" in command
    assert "heldout_census.py" in command
    assert "/home/morpheus/Hyperlex" in command
    assert "/home/morpheus/hlx/force_train_morph78_expanded.jsonl" in command
    assert "/home/morpheus/hlx/hard_atoms_train_morph50.jsonl" in command
    assert "train-receipt.json" in command
    assert "holdout-manifest-rc1.json" in command
    assert "specs/007-hyperlexical-model/receipts/heldout-census-20260924" in command
    assert census_cli.main(["--print-command"]) == 0

    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    monkeypatch.setenv("HYPERLEX_RELEASE_SET", "1")
    monkeypatch.setenv("HYPERLEX_INCLUDE_LIVE", "1")
    with pytest.raises(SystemExit, match="HYPERLEX_ALLOW_TRAIN"):
        census_cli.main(["--out-dir", str(tmp_path / "out"), "--holdout-manifest", str(tmp_path / "m.json")])
    assert not (tmp_path / "out").exists()

    monkeypatch.delenv("HYPERLEX_ALLOW_TRAIN", raising=False)
    monkeypatch.delenv("HYPERLEX_OFFLINE", raising=False)
    with pytest.raises(SystemExit, match="HYPERLEX_OFFLINE"):
        census_cli.main(["--out-dir", str(tmp_path / "out2"), "--holdout-manifest", str(tmp_path / "m.json")])


def test_cli_writes_only_census_json(monkeypatch, tmp_path):
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    monkeypatch.setenv("HYPERLEX_RELEASE_SET", "1")
    monkeypatch.setenv("HYPERLEX_INCLUDE_LIVE", "1")
    monkeypatch.delenv("HYPERLEX_ALLOW_TRAIN", raising=False)
    manifest = _write(tmp_path, "ids.json", {"row_ids": []})
    trained = tmp_path / "trained.jsonl"
    trained.write_text(json.dumps({"text": "other phrase", "fillers": ["other", "phrase"]}) + "\n", encoding="utf-8")
    pool = [
        _row("kept token", ["kept", "token"]),
        _row("TEST SECRET GOLD", ["test", "secret"], split="test"),
    ]
    monkeypatch.setattr(census_cli, "load_release_pool", lambda: (pool, {"release_set": True, "release_content_sha256": "abc"}))
    out = tmp_path / "out"
    assert census_cli.main([
        "--out-dir", str(out),
        "--holdout-manifest", str(manifest),
        "--trained", str(trained),
    ]) == 0
    assert sorted(path.name for path in out.iterdir()) == ["census.json"]
    body = json.loads((out / "census.json").read_text(encoding="utf-8"))
    assert body["schema"] == "hyperlex.heldout_census.v0.1"
    assert body["n_admitted"] == 1
    assert body["n_test_discarded"] == 1
    assert body["code_commit"]
    assert len(body["code_tree_sha256"]) == 64
    assert "TEST SECRET GOLD" not in json.dumps(body)
    assert "rows" not in body
    again = tmp_path / "again"
    assert census_cli.main([
        "--out-dir", str(again),
        "--holdout-manifest", str(manifest),
        "--trained", str(trained),
        "--reproduce", str(out / "census.json"),
    ]) == 0
    reproduced = json.loads((again / "census.json").read_text(encoding="utf-8"))
    assert reproduced["verdict"]["reproduce"] == "matched"
    assert reproduced["verdict"]["published"] == reproduced["verdict"]["candidate"]
    assert reproduced["admitted_ids_sha256"] == body["admitted_ids_sha256"]


def test_sources_do_not_import_scorer_or_torch():
    package = (ROOT / "scripts/shadow/hyperlexical/heldout_census.py").read_text(encoding="utf-8")
    cli = (SPARK / "heldout_census.py").read_text(encoding="utf-8")
    for text in (package, cli):
        assert "score_holdout" not in text
        assert "import holdout_manifest" not in text
        assert "from holdout_manifest" not in text
        assert "import torch" not in text


def test_write_census_rejects_escaped_name(tmp_path):
    report = _census([])
    path = write_census(report, tmp_path)
    assert path.name == "census.json"
    assert path.parent == tmp_path
