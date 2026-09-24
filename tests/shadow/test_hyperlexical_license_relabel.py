import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.license_relabel import SPDX, main, relabel, relabelled


def _store():
    return [
        {"text": "skibidi", "license": "operator-local", "harvest_page": "https://en.wiktionary.org/wiki/skibidi", "class": "INFERRED", "split": "train"},
        {"text": "gyatt", "license": "operator-local; labels OBSERVED", "wiktionary_categories": ["en:Slang"], "class": "OBSERVED", "split": "val"},
        {"text": "smurf", "license": "CC BY-SA (Wiktionary); operator-local labels", "provenance": "crawl4ai:wiktionary"},
        {"text": "rizz", "license": "operator-attested", "class": "OBSERVED"},
    ]


def test_relabelled_strings():
    assert relabelled("operator-local") == "CC BY-SA 4.0 (Wiktionary); operator-local labels"
    assert relabelled("operator-local; labels OBSERVED") == "CC BY-SA 4.0 (Wiktionary); operator-local labels OBSERVED"
    assert relabelled("CC BY-SA (Wiktionary); operator-local labels") == "CC BY-SA (Wiktionary); operator-local labels"


def test_relabel_store_and_harvest_only_touches_wiktionary():
    store = _store()
    harvest = [
        {"text": "TOKEN:skibidi", "role_scheme": "type_slot", "license": "operator-local; labels OBSERVED; unbind structural whitespace"},
        {"text": "rizz", "role_scheme": "positional", "license": "operator-local; labels OBSERVED"},
    ]
    s = relabel(store, harvest)
    assert s["n_store_changed"] == 3 and s["n_harvest_changed"] == 1
    assert store[0]["source_license"] == SPDX and store[0]["source_url"].endswith("/skibidi")
    assert store[1]["class"] == "OBSERVED" and store[1]["split"] == "val"
    assert "source_license" not in store[3] and store[3]["license"] == "operator-attested"
    assert harvest[0]["license"].startswith("CC BY-SA 4.0") and harvest[1]["license"] == "operator-local; labels OBSERVED"
    again = relabel(store, harvest)
    assert again["n_store_changed"] == 0 and again["n_harvest_changed"] == 0


def test_cli_dry_run_and_write(tmp_path):
    store_p, harvest_p, summary = tmp_path / "s.jsonl", tmp_path / "h.jsonl", tmp_path / "sum.json"
    store_p.write_text("".join(json.dumps(r) + "\n" for r in _store()))
    harvest_p.write_text("")
    before = store_p.read_text()
    assert main(["--store", str(store_p), "--harvest", str(harvest_p), "--summary", str(summary), "--dry-run"]) == 0
    assert store_p.read_text() == before
    assert main(["--store", str(store_p), "--harvest", str(harvest_p), "--summary", str(summary)]) == 0
    assert store_p.read_text() != before
    assert list(tmp_path.glob("s.jsonl.bak-pre-license-relabel-*"))
