import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.release_set import enabled, is_share_alike, maybe_release, release_rows

ROWS = [
    {"task": "classify", "split": "train", "text": "skibidi", "license": "CC BY-SA 4.0 (Wiktionary); operator-local labels"},
    {"task": "unbind", "split": "train", "text": "TOKEN:skibidi", "license": "operator-local; labels OBSERVED"},
    {"task": "unbind", "split": "val", "text": "gyatt", "license": "CC-BY-SA-4.0+GFDL (Wiktionary text); INFERRED"},
    {"task": "classify", "split": "train", "text": "rizz", "license": "operator-attested"},
    {"task": "classify", "split": "test", "text": "no cap", "license": "operator-local", "source_license": "CC-BY-SA-4.0"},
]


def test_share_alike_detection():
    assert [is_share_alike(r) for r in ROWS] == [True, False, True, False, True]


def test_release_rows_drops_license_and_same_text():
    kept, stats = release_rows(ROWS)
    assert [r["text"] for r in kept] == ["rizz"]
    assert stats["n_excluded_share_alike"] == 3 and stats["n_excluded_same_text"] == 1
    assert len(stats["release_content_sha256"]) == 64


def test_env_switch(monkeypatch):
    monkeypatch.delenv("HYPERLEX_RELEASE_SET", raising=False)
    assert not enabled()
    rows, stats = maybe_release(ROWS)
    assert rows == ROWS and stats == {"release_set": False}
    monkeypatch.setenv("HYPERLEX_RELEASE_SET", "1")
    rows, stats = maybe_release(ROWS)
    assert len(rows) == 1 and stats["release_set"]
    with pytest.raises(ValueError):
        enabled("yes")
