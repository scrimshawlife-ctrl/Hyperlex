import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.export import FAMILIES, export_dataset, lexical_split, write_export


def test_export_minimums():
    bundle = export_dataset(ROOT)
    c = bundle["counts"]
    assert c["classify"] >= 80
    assert c["unbind"] >= 200
    assert c["negatives"] >= 200
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


def test_reject_candidate_text():
    from hyperlexical.export import reject_candidate_text

    assert reject_candidate_text("") == "empty"
    assert reject_candidate_text("ab") == "len_le_2"
    assert reject_candidate_text("...") == "punct_only"
    assert reject_candidate_text("42") == "numeric"
    assert reject_candidate_text("Unsupported title") == "unsupported_title"
    assert reject_candidate_text("ordinary phrase here") is None


def test_include_live_stays_inferred(tmp_path):
    from hyperlexical.export import export_dataset, write_export

    store = tmp_path / "ingest_candidates.jsonl"
    store.write_text(
        '{"text": "zzzx_live_unique_atom_test", "lineage": "brainrot-aura", "typology": ["compression"], '
        '"stage": "circulating", "roles": [], "fillers": [], "role_scheme": null, '
        '"task": "classify", "provenance": "ingest:pipeline", "class": "INFERRED", '
        '"license": "operator-local", "split": "train"}\n'
        '{"text": "ab", "lineage": "none", "typology": [], "stage": "noise", '
        '"roles": [], "fillers": [], "role_scheme": null, "task": "classify", '
        '"provenance": "ingest:inbox", "class": "INFERRED", "license": "operator-local", '
        '"split": "train"}\n',
        encoding="utf-8",
    )
    bundle = export_dataset(ROOT, include_live=True, live_store=store)
    live = [r for r in bundle["rows"] if str(r["provenance"]).endswith(":live")]
    assert live
    assert all(r["class"] == "INFERRED" for r in live)
    assert all(r["text"] != "ab" for r in live)
    assert bundle["counts"]["live_rejected"] >= 1
    write_export(tmp_path / "out", bundle)
