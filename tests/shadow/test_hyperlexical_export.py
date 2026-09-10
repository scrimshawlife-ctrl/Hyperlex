import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.export import FAMILIES, export_dataset, lexical_split, write_export


def test_export_minimums():
    bundle = export_dataset(ROOT)
    c = bundle["counts"]
    # Honest classify = family-labeled only (excludes negatives bucket)
    assert c["classify"] >= 80
    assert c["classify"] == c.get("classify") # family
    assert c["classify_all"] == c["classify"] + c["classify_none"]
    # Negatives = ordinary-prose seed only (not all lineage=none classify)
    assert c["negatives"] >= 200
    assert c["negatives"] == sum(
        1
        for r in bundle["rows"]
        if r["task"] == "classify"
        and r["lineage"] == "none"
        and str(r.get("provenance") or "").startswith("seed:negative-prose")
    )
    assert c["classify_none"] >= c["negatives"]
    # Fixtures honest n=24 + civilian dual-scheme — not n=128 padding toward gate
    assert c["unbind_fixture"] >= 40
    assert c["unbind_civilian"] >= 40
    assert c["unbind"] == c["unbind_fixture"] + c["unbind_civilian"]
    assert c["dialect"] >= 8
    assert c["backfill"] >= 1
    assert c["inferred"] >= 1
    assert c["observed"] >= 20
    assert c["name_gate"] is False
    assert c["name_gate_classify_gap"] == max(0, 2000 - c["classify"])
    families = {r["lineage"] for r in bundle["rows"] if r["task"] == "classify"}
    for fam in FAMILIES:
        assert fam in families
    assert "none" in families
    schemes = {r["role_scheme"] for r in bundle["rows"] if r["task"] == "unbind"}
    assert schemes == {"positional", "type_slot"}
    civ_schemes = {
        r["role_scheme"]
        for r in bundle["rows"]
        if r["task"] == "unbind"
        and str(r["provenance"]).startswith(("civilian-pos:", "civilian-type:"))
    }
    assert civ_schemes == {"positional", "type_slot"}
    assert all(r["class"] in {"OBSERVED", "INFERRED"} for r in bundle["rows"])
    assert all("/home/" not in json.dumps(r) for r in bundle["rows"])
    assert ".hyperlex" not in bundle["payload"]
    skill = [r for r in bundle["rows"] if r["text"].lower() == "skill issue" and r["task"] == "classify"]
    families_hit = {r["lineage"] for r in skill}
    assert not ({"ai-native", "gaming-meta"} <= families_hit)
    # collision-hold must not appear as civilian unbind gold
    skill_unbind = [
        r
        for r in bundle["rows"]
        if r["task"] == "unbind" and "skill issue" in r["text"].lower()
    ]
    assert skill_unbind == []


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
    assert "unbind_fixture" in man["counts"]
    assert "classify_all" in man["counts"]


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
    # allowlisted short slang / codes (clear FPs on prior reject list)
    for tok in ("ez", "gg", "W", "L", "gm", "420", "4/20", "BS", "A+"):
        assert reject_candidate_text(tok) is None, tok
    # still reject bare junk / ambiguous non-allowlisted shorts
    assert reject_candidate_text("a") == "len_le_2"
    assert reject_candidate_text("11") == "numeric"


def test_include_live_preserves_store_class(tmp_path):
    """--include-live copies class from store; unset defaults to INFERRED."""
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
        '"split": "train"}\n'
        '{"text": "gm", "lineage": "gaming-meta", "typology": ["status", "hook"], '
        '"stage": "circulating", "roles": [], "fillers": [], "role_scheme": null, '
        '"task": "classify", "provenance": "ingest:pipeline", "class": "INFERRED", '
        '"license": "operator-local", "split": "train"}\n'
        # Settled OBSERVED must stay OBSERVED (do not hardcode INFERRED).
        '{"text": "zzzx_settled_observed_atom", "lineage": "brainrot-aura", "typology": ["compression"], '
        '"stage": "circulating", "roles": [], "fillers": [], "role_scheme": null, '
        '"task": "classify", '
        '"provenance": "ingest:pipeline;operator-settle:KEEP-93:2026-09-10", '
        '"class": "OBSERVED", "license": "operator-local", "split": "val"}\n'
        # Unset class → INFERRED (never invent OBSERVED).
        '{"text": "zzzx_unset_class_atom", "lineage": "gaming-meta", "typology": ["status"], '
        '"stage": "circulating", "roles": [], "fillers": [], "role_scheme": null, '
        '"task": "classify", "provenance": "ingest:pipeline", '
        '"license": "operator-local", "split": "train"}\n',
        encoding="utf-8",
    )
    bundle = export_dataset(ROOT, include_live=True, live_store=store)
    live = [r for r in bundle["rows"] if str(r["provenance"]).endswith(":live")]
    assert live
    by_text = {r["text"]: r for r in live}
    assert by_text["zzzx_live_unique_atom_test"]["class"] == "INFERRED"
    assert by_text["zzzx_settled_observed_atom"]["class"] == "OBSERVED"
    assert by_text["zzzx_unset_class_atom"]["class"] == "INFERRED"
    assert all(r["text"] != "ab" for r in live)
    assert any(r["text"] == "gm" for r in live)  # allowlisted short slang kept
    assert bundle["counts"]["live_rejected"] >= 1
    write_export(tmp_path / "out", bundle)

def test_include_live_observed_upgrades_inferred_duplicate(tmp_path):
    """Settled OBSERVED live row replaces earlier base INFERRED on same key."""
    from hyperlexical.export import dedupe, load_live_candidates, _row

    # Simulate base INFERRED + live OBSERVED same (task, text, scheme, lineage).
    base = [
        _row(
            text="zzzx_upgrade_atom",
            lineage="brainrot-aura",
            typology=["compression"],
            stage="circulating",
            roles=[],
            fillers=[],
            role_scheme=None,
            task="classify",
            provenance="backfill:test.json",
            **{"class": "INFERRED"},
            license="MIT-examples",
            split="train",
        )
    ]
    store = tmp_path / "ingest_candidates.jsonl"
    store.write_text(
        '{"text": "zzzx_upgrade_atom", "lineage": "brainrot-aura", "typology": ["compression"], '
        '"stage": "circulating", "roles": [], "fillers": [], "role_scheme": null, '
        '"task": "classify", "provenance": "operator-settle:KEEP-93:2026-09-10", '
        '"class": "OBSERVED", "license": "operator-local", "split": "val"}\n',
        encoding="utf-8",
    )
    live = load_live_candidates(store)
    assert live and live[0]["class"] == "OBSERVED"
    merged = dedupe(base + live)
    hit = [r for r in merged if r["text"] == "zzzx_upgrade_atom"]
    assert len(hit) == 1
    assert hit[0]["class"] == "OBSERVED"
    assert "KEEP-93" in hit[0]["provenance"]



def test_include_live_negatives_ordinary_prose_only(tmp_path):
    """Live lineage=none must not inflate name-gate negatives bucket."""
    from hyperlexical.export import export_dataset

    store = tmp_path / "ingest_candidates.jsonl"
    # Many live none rows (inbox unclassified) + one family row
    lines = []
    for i in range(50):
        lines.append(
            '{"text": "zzzx_live_none_%d", "lineage": "none", "typology": [], '
            '"stage": "noise", "roles": [], "fillers": [], "role_scheme": null, '
            '"task": "classify", "provenance": "ingest:inbox", "class": "INFERRED", '
            '"license": "operator-local", "split": "train"}' % i
        )
    lines.append(
        '{"text": "zzzx_live_family_atom", "lineage": "brainrot-aura", "typology": ["compression"], '
        '"stage": "circulating", "roles": [], "fillers": [], "role_scheme": null, '
        '"task": "classify", "provenance": "ingest:pipeline", "class": "INFERRED", '
        '"license": "operator-local", "split": "train"}'
    )
    store.write_text("\n".join(lines) + "\n", encoding="utf-8")
    base = export_dataset(ROOT, include_live=False)
    live = export_dataset(ROOT, include_live=True, live_store=store)
    # Ordinary-prose negatives unchanged by live none flood
    assert live["counts"]["negatives"] == base["counts"]["negatives"]
    assert live["counts"]["negatives"] >= 200
    # Live none visible under classify_none, not negatives
    assert live["counts"]["classify_none"] >= base["counts"]["classify_none"] + 50
    assert live["counts"]["classify_none"] > live["counts"]["negatives"]
    assert live["counts"]["classify_all"] == live["counts"]["classify"] + live["counts"]["classify_none"]
    # Family gate still moves with live family row
    assert live["counts"]["classify"] >= base["counts"]["classify"] + 1

def test_live_split_live_coerced_to_lexical(tmp_path):
    """Store split=live must not survive export — Spec 007 lexical split only."""
    from hyperlexical.export import export_dataset, lexical_split

    store = tmp_path / "ingest_candidates.jsonl"
    store.write_text(
        '{"text": "zzzx_split_live_atom", "lineage": "brainrot-aura", "typology": ["compression"], '
        '"stage": "circulating", "roles": [], "fillers": [], "role_scheme": null, '
        '"task": "classify", "provenance": "operator-blanket-yes:test", "class": "INFERRED", '
        '"license": "operator-local", "split": "live"}\n',
        encoding="utf-8",
    )
    bundle = export_dataset(ROOT, include_live=True, live_store=store)
    hit = [r for r in bundle["rows"] if r["text"] == "zzzx_split_live_atom"]
    assert len(hit) == 1
    assert hit[0]["split"] == lexical_split("zzzx_split_live_atom")
    assert hit[0]["split"] in {"train", "val", "test"}
    assert all(r["split"] in {"train", "val", "test"} for r in bundle["rows"])

