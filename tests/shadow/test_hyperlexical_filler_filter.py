import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.filler_filter import assert_publishable_vocab, filter_mode, filter_unbind_rows, reject_reason


@pytest.mark.parametrize("tok", ["rizz", "no", "cap", "fr", "4k", "brain-rot", "let's", "let\\u2019s", "'em", "honkin'", "skibidi", "W"])
def test_publishable(tok):
    assert reject_reason(tok) is None


@pytest.mark.parametrize(
    "tok,reason",
    [
        ("@someone", "handle_or_email"),
        ("https://t.co/x", "link"),
        ("example.com", "link"),
        ("![](https://en.wikipedia.org/wiki/x", "link"),
        ("(slang)", "markup_or_quote"),
        ('"w:gyatt")', "markup_or_quote"),
        ("[In:]", "markup_or_quote"),
        ("Polish:", "not_word"),
        ("brainrot.", "not_word"),
        ("1.", "not_word"),
        ("Języka", "non_ascii"),
        ("cap\\U0001F923", "non_ascii"),
        ("", "empty"),
        ("a" * 30, "too_long"),
    ],
)
def test_rejected(tok, reason):
    assert reject_reason(tok) == reason


def test_filter_rows_modes(monkeypatch):
    rows = [{"fillers": ["no", "cap"]}, {"fillers": ["@x", "cap"]}, {"fillers": ["(slang)"]}]
    kept, stats = filter_unbind_rows(rows, "strict")
    assert kept == [rows[0]] and stats["n_filler_rows_dropped"] == 2
    assert stats["filler_reject_reasons"] == {"handle_or_email": 1, "markup_or_quote": 1}
    kept, stats = filter_unbind_rows(rows, "off")
    assert kept == rows and stats["n_filler_rows_dropped"] == 0
    monkeypatch.delenv("HYPERLEX_FILLER_FILTER", raising=False)
    assert filter_mode() == "strict"
    with pytest.raises(ValueError):
        filter_mode("lenient")


def test_vocab_guard():
    assert_publishable_vocab(["<unk>", "rizz", "cap"])
    with pytest.raises(ValueError):
        assert_publishable_vocab(["<unk>", "rizz", "@handle"])


def test_loop_prepare_applies_filter(monkeypatch):
    from hyperlexical.loop import prepare_unbind_splits

    monkeypatch.delenv("HYPERLEX_UNBIND_FORCE_TRAIN_PATH", raising=False)
    monkeypatch.setenv("HYPERLEX_TASK_ROUTING", "legacy_split")
    rows = [
        {"task": "unbind", "split": "train", "text": "no cap", "fillers": ["no", "cap"], "roles": ["pos_0", "pos_1"], "role_scheme": "positional", "class": "OBSERVED"},
        {"task": "unbind", "split": "train", "text": "(slang) rizz", "fillers": ["(slang)", "rizz"], "roles": ["pos_0", "pos_1"], "role_scheme": "positional", "class": "OBSERVED"},
        {"task": "unbind", "split": "val", "text": "Polish: x", "fillers": ["Polish:", "x"], "roles": ["pos_0", "pos_1"], "role_scheme": "positional", "class": "OBSERVED"},
    ]
    monkeypatch.setenv("HYPERLEX_FILLER_FILTER", "strict")
    train, val, stats = prepare_unbind_splits(rows)
    assert all("(slang)" not in r["fillers"] for r in train) and val == []
    assert stats["n_filler_rows_dropped_train"] == 1 and stats["n_filler_rows_dropped_val"] == 1
    monkeypatch.setenv("HYPERLEX_FILLER_FILTER", "off")
    train, val, stats = prepare_unbind_splits(rows)
    assert len(val) == 1 and stats["n_filler_rows_dropped_train"] == 0
