"""Synthetic checks for the brainrot-aura fold fix and classify admission.

No data-store rows, holdout ids, or private manifests.
"""

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classify_admission import apply_classify_admission
from hyperlexical.export import (
    AI_NATIVE_TYPOLOGY,
    export_dataset,
    harvest_4333_dump,
    undo_dump_brainrot_fold,
)


def _classify(text, lineage, *, source="registry", split="train", task="classify", typology=None, raw=None, fillers=None, demote=None):
    prov = {"source": source}
    if raw is not None:
        prov["raw_typology"] = list(raw)
    row = {
        "text": text,
        "lineage": lineage,
        "split": split,
        "task": task,
        "provenance": prov,
        "typology": list(typology or ["compression"]),
        "fillers": list(fillers or []),
        "role_scheme": None,
        "class": "INFERRED",
    }
    if demote:
        row["gold_demote_reason"] = demote
    return row


def test_harvest_fold_no_longer_fires(tmp_path):
    dump = tmp_path / "data"
    dump.mkdir()
    (dump / "hyperlex_4333_dump.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "text": "zzzx fold target",
                        "lineage": "brainrot-aura",
                        "typology": ["compression", "status"],
                        "provenance": "notion-string",
                        "class": "INFERRED",
                    }
                ),
                json.dumps(
                    {
                        "text": "zzzx restore original lineage",
                        "lineage": "ai-native",
                        "typology": ["compression", "status"],
                        "provenance": {
                            "source": "notion",
                            "original_lineage": "brainrot-aura",
                        },
                        "class": "INFERRED",
                    }
                ),
                json.dumps(
                    {
                        "text": "zzzx stays ai native",
                        "lineage": "ai-native",
                        "typology": ["compression"],
                        "provenance": {"source": "notion"},
                        "class": "INFERRED",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    got = {row["text"]: row for row in harvest_4333_dump(tmp_path)}

    folded = got["zzzx fold target"]
    assert folded["lineage"] == "brainrot-aura"
    assert folded["typology"] == ["compression", "status"]
    assert folded["provenance"]["raw_typology"] == ["compression", "status"]
    assert "memory" not in folded["typology"]

    restored = got["zzzx restore original lineage"]
    assert restored["lineage"] == "brainrot-aura"
    assert restored["typology"] == ["compression", "status"]
    assert restored["provenance"]["raw_typology"] == ["compression", "status"]
    assert restored["provenance"]["original_provenance"]["original_lineage"] == "brainrot-aura"

    native = got["zzzx stays ai native"]
    assert native["lineage"] == "ai-native"
    assert native["typology"] == ["compression", *AI_NATIVE_TYPOLOGY[1:]]
    assert native["provenance"]["raw_typology"] == ["compression"]


def test_undo_relabels_only_unanimous_outside_evidence():
    text = "ZZZX Brainrot-Aura!!"
    notion = _classify(
        text,
        "ai-native",
        source="notion",
        split="test",
        typology=["compression", "memory", "provenance", "context", "vernacular"],
        raw=["status", "compression", "status"],
        demote=None,
    )
    notion["class"] = "OBSERVED"
    outside = _classify("zzzx brainrot aura", "brainrot-aura", source="registry", split="train")
    other_outside = _classify("zzzx   brainrot aura", "brainrot-aura", source="backfill", split="val")
    blocked = _classify(text, "ai-native", source="registry", split="test")
    rows = [notion, outside, other_outside, blocked]
    splits = [row["split"] for row in rows]

    out, n = undo_dump_brainrot_fold(rows)

    assert out is rows
    assert n == 1
    assert [row["split"] for row in out] == splits
    assert notion["lineage"] == "brainrot-aura"
    assert notion["split"] == "test"
    assert notion["typology"] == ["status", "compression"]
    assert notion["provenance"]["fold_undone"] == "dump_brainrot_fold"
    assert outside["lineage"] == "brainrot-aura"
    assert blocked["lineage"] == "ai-native"
    assert "fold_undone" not in blocked["provenance"]


def test_undo_leaves_mixed_or_missing_evidence_and_counts():
    unanimous = _classify(
        "zzzx unanimous",
        "ai-native",
        source="notion",
        raw=["compression", "status"],
        typology=["compression", "memory"],
    )
    twin = _classify("zzzx unanimous", "ai-native", source="notion", raw=["compression"])
    mixed = _classify("zzzx mixed", "ai-native", source="notion", raw=["status"])
    alone = _classify("zzzx alone", "ai-native", source="notion")
    test_only = _classify("zzzx test only", "ai-native", source="notion")
    notion_only = _classify("zzzx notion only", "ai-native", source="notion")
    blank = _classify("??", "ai-native", source="notion")
    rows = [
        unanimous,
        twin,
        mixed,
        alone,
        test_only,
        notion_only,
        blank,
        _classify("zzzx unanimous", "brainrot-aura", source="registry"),
        _classify("zzzx mixed", "brainrot-aura", source="registry"),
        _classify("zzzx mixed", "gaming-meta", source="registry", split="val"),
        _classify("zzzx test only", "brainrot-aura", source="registry", split="test"),
        _classify("zzzx notion only", "brainrot-aura", source="notion"),
        _classify("zzzx unanimous", "political-status", source="live", task="unbind"),
        _classify("??", "brainrot-aura", source="registry"),
    ]
    splits = [row["split"] for row in rows]

    out, n = undo_dump_brainrot_fold(rows)

    assert out is rows
    assert [row["split"] for row in out] == splits
    assert n == 2
    assert unanimous["lineage"] == "brainrot-aura"
    assert unanimous["typology"] == ["compression", "status"]
    assert twin["lineage"] == "brainrot-aura"
    assert twin["typology"] == ["compression"]
    for left in (mixed, alone, test_only, notion_only, blank):
        assert left["lineage"] == "ai-native"
        assert "fold_undone" not in left["provenance"]


def test_export_records_dump_brainrot_fold_undone(monkeypatch, tmp_path):
    import hyperlexical.export as exp

    text = "zzzx unanimous outside evidence"
    outside = exp._row(
        text=text,
        lineage="brainrot-aura",
        typology=["compression", "status"],
        task="classify",
        provenance="seed:synthetic",
        split="train",
        **{"class": "INFERRED"},
    )
    notion = exp._row(
        text=text,
        lineage="ai-native",
        typology=["compression", "memory", "provenance", "context", "vernacular"],
        task="classify",
        provenance={"source": "notion", "raw_typology": ["compression", "status"]},
        split="train",
        **{"class": "OBSERVED"},
    )
    mixed_text = "zzzx mixed outside evidence"
    mixed_notion = exp._row(
        text=mixed_text,
        lineage="ai-native",
        typology=["compression"],
        task="classify",
        provenance={"source": "notion", "raw_typology": ["compression"]},
        split="val",
        **{"class": "INFERRED"},
    )

    monkeypatch.setattr(
        exp,
        "harvest_dialect",
        lambda: [
            outside,
            _outside(exp, mixed_text, "brainrot-aura"),
            _outside(exp, mixed_text, "gaming-meta"),
        ],
    )
    monkeypatch.setattr(exp, "harvest_backfill", lambda root: [])
    monkeypatch.setattr(exp, "harvest_registry", lambda root: [])
    monkeypatch.setattr(exp, "harvest_receipts", lambda root: [])
    monkeypatch.setattr(exp, "harvest_archive", lambda root: [])
    monkeypatch.setattr(exp, "harvest_unbind", lambda n=24: [])
    monkeypatch.setattr(exp, "harvest_civilian_unbind", lambda root: [])
    monkeypatch.setattr(exp, "harvest_negatives", lambda: [])
    monkeypatch.setattr(exp, "harvest_inferred_classify_pass", lambda root: [])
    monkeypatch.setattr(exp, "harvest_moltbook", lambda root, stats=None: [])
    monkeypatch.setattr(exp, "harvest_4333_dump", lambda root: [notion, mixed_notion])

    bundle = export_dataset(tmp_path)
    assert bundle["counts"]["dump_brainrot_fold_undone"] == 1
    assert bundle["counts"]["name_gate"] is False
    kept = [row for row in bundle["rows"] if row["text"] == text]
    assert len(kept) == 1
    assert kept[0]["lineage"] == "brainrot-aura"
    assert kept[0]["split"] == "train"
    assert kept[0]["typology"] == ["compression", "status"]
    assert kept[0]["provenance"]["fold_undone"] == "dump_brainrot_fold"
    mixed = [
        row
        for row in bundle["rows"]
        if row["text"] == mixed_text and row["task"] == "classify"
    ]
    assert {row["lineage"] for row in mixed} == {"ai-native", "brainrot-aura", "gaming-meta"}
    assert all(
        "fold_undone" not in row["provenance"]
        for row in mixed
        if isinstance(row.get("provenance"), dict) and row["lineage"] == "ai-native"
    )


def _outside(exp, text, lineage):
    return exp._row(
        text=text,
        lineage=lineage,
        typology=["status"],
        task="classify",
        provenance=f"seed:synthetic:{lineage}",
        split="train",
        **{"class": "INFERRED"},
    )


def _admission_pool():
    conflict_a = _classify("zzzx conflict phrase", "ai-native", split="train")
    conflict_b = _classify("zzzx conflict phrase", "brainrot-aura", split="val")
    test_only = _classify("zzzx test disagreement", "ai-native", split="train")
    test_other = _classify("zzzx test disagreement", "gaming-meta", split="test")
    molt = _classify("zzzx molt row", "ai-native", source="moltbook", split="train")
    molt_seed = _classify("zzzx molt seed", "ai-native", source="moltbook-curated-seed", split="val")
    molt_demoted = _classify(
        "zzzx molt demoted",
        "ai-native",
        source="moltbook",
        split="train",
        demote="fallback_label",
    )
    demoted = _classify("zzzx demoted reason", "workplace-corp", split="train", demote="no_gold")
    filler = _classify("zzzx filler general", "kinship-address", split="val", fillers=["General"])
    kdr = _classify("zzzx filler kdr", "crypto-degen", split="train", fillers=["kdr"])
    kept_word = _classify("zzzx generally fine", "betting-sharp", split="train", fillers=["generally"])
    clean_tr = _classify("zzzx clean train", "political-status", split="train")
    clean_va = _classify("zzzx clean val", "workplace-corp", split="val")
    all_rows = [
        conflict_a,
        conflict_b,
        test_only,
        test_other,
        molt,
        molt_seed,
        molt_demoted,
        demoted,
        filler,
        kdr,
        kept_word,
        clean_tr,
        clean_va,
    ]
    train = [conflict_a, test_only, molt, molt_demoted, demoted, kdr, kept_word, clean_tr]
    val = [conflict_b, molt_seed, filler, clean_va]
    return all_rows, train, val


def test_admission_drops_only_when_flag_on(monkeypatch):
    all_rows, train, val = _admission_pool()
    monkeypatch.setenv("HLX_CLASSIFY_ADMISSION", "1")
    got_tr, got_va, receipt = apply_classify_admission(all_rows, train, val)

    assert [row["text"] for row in got_tr] == [
        "zzzx test disagreement",
        "zzzx generally fine",
        "zzzx clean train",
    ]
    assert [row["text"] for row in got_va] == ["zzzx clean val"]
    assert receipt["enabled"] is True
    assert receipt["conflict_texts"] == 1
    assert receipt["train"] == {
        "in": 8,
        "kept": 3,
        "dropped": {
            "conflict": 1,
            "demoted": 2,
            "moltbook_source_constant": 2,
        },
    }
    assert receipt["val"] == {
        "in": 4,
        "kept": 1,
        "dropped": {
            "conflict": 1,
            "demoted": 1,
            "moltbook_source_constant": 1,
        },
    }
    assert train[0]["lineage"] == "ai-native"
    assert "gold_demote_reason" in train[4]


@pytest.mark.parametrize("flag", [None, "0", "true", ""])
def test_admission_is_noop_when_flag_off(monkeypatch, flag):
    monkeypatch.delenv("HLX_CLASSIFY_ADMISSION", raising=False)
    if flag is not None:
        monkeypatch.setenv("HLX_CLASSIFY_ADMISSION", flag)
    all_rows, train, val = _admission_pool()
    before = json.dumps([train, val], sort_keys=True)
    got_tr, got_va, receipt = apply_classify_admission(all_rows, train, val)
    assert got_tr is train
    assert got_va is val
    assert receipt is None
    assert json.dumps([got_tr, got_va], sort_keys=True) == before
