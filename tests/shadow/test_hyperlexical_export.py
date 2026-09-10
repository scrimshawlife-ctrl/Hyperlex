import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.export import FAMILIES, export_dataset, lexical_split, main, write_export
from hyperlexical.ingest_tap import append_rows, row_from_atom


def test_export_minimums():
    bundle = export_dataset(ROOT)
    c = bundle["counts"]
    assert c["classify"] >= 80
    assert c["unbind"] >= 40
    assert c["negatives"] >= 20
    assert c["dialect"] >= 8
    assert c["backfill"] >= 1
    assert c["inferred"] >= 1
    assert c["observed"] >= 20
    assert c["name_gate"] is False
    families = {r["lineage"] for r in bundle["rows"] if r["task"] == "classify"}
    for fam in FAMILIES:
        assert fam in families
    assert "none" in families
    schemes = {r["role_scheme"] for r in bundle["rows"] if r["task"] == "unbind"}
    assert schemes == {"positional", "type_slot"}
    assert all(r["class"] in {"OBSERVED", "INFERRED"} for r in bundle["rows"])
    assert all("/home/" not in json.dumps(r) for r in bundle["rows"])
    assert ".hyperlex" not in bundle["payload"]
    skill = [r for r in bundle["rows"] if r["text"].lower() == "skill issue" and r["task"] == "classify"]
    families_hit = {r["lineage"] for r in skill}
    assert not ({"ai-native", "gaming-meta"} <= families_hit)


def test_split_stable():
    assert lexical_split("rizz") == lexical_split("rizz")
    assert lexical_split("rizz") in {"train", "val", "test"}


def test_write_and_hash(tmp_path):
    bundle = export_dataset(ROOT)
    path = write_export(tmp_path, bundle)
    raw = path.read_text(encoding="utf-8")
    assert raw == bundle["payload"]
    man = json.loads((tmp_path / "MANIFEST.json").read_text())
    assert man["sha256"] == bundle["sha256"]
    assert man["brier"] is None
    assert man["trunk"] == "answerdotai/ModernBERT-base"
    assert man["counts"]["name_gate"] is False


def test_no_third_scheme():
    bundle = export_dataset(ROOT)
    for row in bundle["rows"]:
        if row["role_scheme"] is not None:
            assert row["role_scheme"] in {"positional", "type_slot"}


def test_export_include_live_merges_store(monkeypatch, tmp_path):
    store = tmp_path / "ingest_candidates.jsonl"
    append_rows([row_from_atom("sigma grindset", family="ai-native", source="pipeline")], store)
    monkeypatch.setenv("HYPERLEX_HYPERLEXICAL_STORE", str(store))

    base = export_dataset(ROOT)
    live = export_dataset(ROOT, include_live=True)

    assert "sigma grindset" not in {row["text"] for row in base["rows"]}
    rows = [row for row in live["rows"] if row["text"] == "sigma grindset"]
    assert len(rows) == 1
    assert rows[0]["provenance"] == "ingest:store"


def test_export_cli_include_live_flag(monkeypatch, tmp_path):
    store = tmp_path / "ingest_candidates.jsonl"
    append_rows([row_from_atom("receipt-maxxing", family="brainrot-aura", source="scan")], store)
    monkeypatch.setenv("HYPERLEX_HYPERLEXICAL_STORE", str(store))

    assert main(["--out", str(tmp_path), "--include-live"]) == 0
    payload = (tmp_path / "civilian.v0.1.jsonl").read_text(encoding="utf-8")
    assert "receipt-maxxing" in payload
