"""Spec 007 residual dump themes beside unbind_exact.

Tiny fixtures only. Does not invent gold. name_gate stays false.
"""

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.unbind_residual import (
    THEME_EXACT,
    THEME_FULL,
    THEME_MORPH,
    THEME_ORDER,
    THEME_POS_HEAD,
    classify_residual_themes,
    residual_row_record,
    resolve_unbind_residual_dump_path,
    summarize_residual_records,
    write_residual_dump,
)


def test_resolve_dump_path_default_empty(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_RESIDUAL_DUMP", raising=False)
    assert resolve_unbind_residual_dump_path() == ""
    assert resolve_unbind_residual_dump_path("  ") == ""


def test_resolve_dump_path_armed(monkeypatch, tmp_path):
    target = tmp_path / "residual.jsonl"
    monkeypatch.setenv("HYPERLEX_UNBIND_RESIDUAL_DUMP", str(target))
    assert resolve_unbind_residual_dump_path() == str(target)


def test_exact_hit_themes():
    assert classify_residual_themes(["rizz", "aura"], ["rizz", "aura"]) == [THEME_EXACT]
    assert residual_row_record(text="x", gold=["rizz"], pred=["rizz"]) is None


def test_positional_head_miss():
    themes = classify_residual_themes(
        ["rizz", "aura"],
        ["mid", "aura"],
        role_scheme="positional",
    )
    assert THEME_POS_HEAD in themes
    assert THEME_EXACT not in themes


def test_order_miss_permutation():
    themes = classify_residual_themes(["rizz", "aura"], ["aura", "rizz"])
    assert THEME_ORDER in themes


def test_morph_bleed_uses_existing_siblings():
    themes = classify_residual_themes(
        ["looksmaxxing"],
        ["looksmaxxed"],
        role_scheme="positional",
    )
    assert THEME_MORPH in themes
    assert THEME_POS_HEAD in themes


def test_full_miss():
    themes = classify_residual_themes(["rizz"], ["mid"], role_scheme="positional")
    assert THEME_FULL in themes or THEME_POS_HEAD in themes


def test_write_dump_and_summary(tmp_path):
    rec = residual_row_record(
        text="quiet quitting",
        gold=["quiet", "quitting"],
        pred=["quiet", "quit"],
        row={
            "role_scheme": "positional",
            "roles": ["0", "1"],
            "lineage": "ai-native",
            "class": "OBSERVED",
        },
    )
    assert rec is not None
    assert THEME_POS_HEAD not in rec["themes"] or rec["gold"][0] != rec["pred"][0]
    path = tmp_path / "val_residual.jsonl"
    receipt = write_residual_dump(path, [rec])
    assert receipt["n_unbind_residual"] == 1
    assert receipt["unbind_residual_dump"] == "val_residual.jsonl"
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    loaded = json.loads(lines[0])
    assert loaded["text"] == "quiet quitting"
    summary = summarize_residual_records([rec])
    assert summary["n_residual"] == 1
    assert summary["by_scheme"].get("positional") == 1
